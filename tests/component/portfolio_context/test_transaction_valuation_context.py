"""
Bounded-context tests: transactions -> holdings -> portfolio tree valuations -> factor values.

Semantics established from the implementation (see docs/TESTING.md, "Portfolio context"):

- Entry points: UnifiedPortfolioManager.set_holdings (targets) -> TradeManager.execute_trade, which
  books order + fill + position + cash leg as ONE database transaction. Fill price = trade price;
  no fees / commissions, no cost basis, no realised / unrealised P&L are modelled. Cash moves by
  exactly round(|qty| x fill price) (positions.quantity is an integer).
- Tree: main Portfolio holds only sub-portfolio links (CurrencyPortfolio, CompanySharePortfolio,
  CompanyShareOptionPortfolio); share holdings live in the CompanySharePortfolio, which may itself
  hold further CompanySharePortfolios. There are no direct share holdings under the main portfolio.
- Valuation is explicit, not event driven: get_portfolio_value -> PortfolioService.calculate_value
  walks the tree, recomputes every leaf holding factor (force_recalculate) from the last CLOSED bar
  and stores one total per portfolio and date. A parent = sum of its direct children; a child
  sub-portfolio's holdings are counted only inside the child (no double counting).
- Positions carry no history: quantities are the current state.

Prices: raw daily closes, bar stamped at its start, usable once closed (Friday's bar values Monday).
"""

import contextlib
import io
import logging
import math
import time
from unittest.mock import PropertyMock, patch

import pytest
from sqlalchemy.orm import Session

from src.application.services.data.entities.factor.factor_value_batch_resolution_service import (
    FactorValueBatchResolutionService,
)
from src.application.services.data.entities.factor.factor_value_resolution_service import FactorValueResolutionService
from src.domain.entities.factor.dependency_spec import DependencySpec
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_mid_price_factor import (
    CompanyShareMidPriceFactor,
)
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_value_factor import (
    CompanyShareValueFactor,
)
from src.domain.entities.factor.finance.holding.company_share_portfolio.company_share_portfolio_holding_value_factor import (
    CompanySharePortfolioHoldingValueFactor,
)
from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.infrastructure.models.factor.factor import FactorModel
from src.infrastructure.models.factor.factor_value import FactorValueModel
from src.infrastructure.models.finance.holding.company_share_portfolio_holding import CompanySharePortfolioHoldingModel
from src.infrastructure.models.finance.holding.company_share_portfolio_portfolio_holding import (
    CompanySharePortfolioPortfolioHoldingModel,
)
from src.infrastructure.models.finance.holding.currency_portfolio_holding import CurrencyPortfolioHoldingModel
from src.infrastructure.models.finance.holding.holding import HoldingModel
from src.infrastructure.models.finance.position import PositionModel
from src.infrastructure.models.finance.transaction.transaction import TransactionModel
from src.infrastructure.repositories.repository_factory import RepositoryFactory
from tests.component.factor_context.test_factor_resolution import Context
from tests.component.portfolio_context.test_portfolio_value_layers import (
    CASH, FRI, MON, MON_16, TUE, TUE_16, WED_16, Tree,
)
from tests.misbuffet.sqlite_portfolio import slice_at

logging.getLogger("context").setLevel(logging.CRITICAL)


@pytest.fixture
def tree():
    t = Tree()
    t.close("AAPL", FRI, 150.0)
    t.close("MSFT", FRI, 400.0)
    yield t
    t.p.close()


def books(t):
    """The bookkeeping state a transaction may change."""
    return dict(aapl=t.p.qty("AAPL"), msft=t.p.qty("MSFT"), cash=t.p.cash(),
                orders=len(t.p.orders()), txns=len(t.p.transactions()))


def set_holdings(t, when, **targets_and_prices):
    """set_holdings({CompanyShare: [...]}) at `when`; kwargs: TICKER=(quantity, slice price)."""
    t.p.upm._algorithm.time = when
    targets = [{"name": k, "quantity": q} for k, (q, _) in targets_and_prices.items()]
    return t.p.upm.set_holdings({CompanyShare: targets},
                                slice_at(when, **{k: px for k, (_, px) in targets_and_prices.items()}))


def rows_at(t, factor_name, when):
    return [(r[1], r[3]) for r in t.p.factor_values(factor_name) if r[2] == when]


def reload(t, when):
    """Re-read the persisted state through a fresh session and the repositories."""
    session = Session(t.p.engine)
    try:
        factory = RepositoryFactory(session)
        portfolio = factory.portfolio_local_repo.get_by_id(t.p.portfolio.id)

        def position_of(holding_model):
            return factory.position_local_repo.get_by_id(holding_model.position_id).quantity

        def holding(ticker):
            share = factory.company_share_local_repo.get_by_symbol(ticker)
            return session.query(CompanySharePortfolioHoldingModel).filter_by(asset_id=share.id).one_or_none()

        def value(name, entity_id):
            factor = session.query(FactorModel).filter_by(name=name).one_or_none()
            if factor is None or entity_id is None:
                return None
            fv = factory.factor_value_local_repo.get_by_factor_entity_date(
                factor.id, entity_id, when.strftime("%Y-%m-%d %H:%M:%S"))
            return float(fv.value) if fv is not None else None

        cash_holding = session.query(CurrencyPortfolioHoldingModel).one()
        link = session.query(CompanySharePortfolioPortfolioHoldingModel).filter_by(container_id=portfolio.id).one()
        state = {
            "portfolio": (portfolio.id, portfolio.name),
            "cash": float(position_of(cash_holding)),
            "transactions": len(factory.transaction_local_repo.get_all()),
            "main": value("Portfolio Value", portfolio.id),
            "share_portfolio": value("Company Share Portfolio Value", link.asset_id),
            "cash_portfolio": value("Currency Portfolio Value", cash_holding.currency_portfolio_id),
        }
        for ticker in ("AAPL", "MSFT"):
            h = holding(ticker)
            state[ticker] = (position_of(h), value("Portfolio Company Share Holding Value", h.id)) if h else None
        return state
    finally:
        session.close()


# ---------------------------------------------------------------------------------------------------
# 3. Transactions
# ---------------------------------------------------------------------------------------------------

class TestBuy:

    def test_buy_below_the_market_price_books_every_effect_and_reloads_identically(self, tree):
        before = books(tree)
        assert tree.revalue(MON_16) == CASH
        assert before == dict(aapl=0, msft=0, cash=CASH, orders=0, txns=0)

        tree.trade("AAPL", 10, 145.0, MON_16)                           # Tree.trade asserts it was booked
        assert books(tree) == dict(aapl=10, msft=0, cash=98_550.0, orders=2, txns=2)   # no fees: 10 x 145

        # side / quantity / price live on the order; the transaction records the execution of that order
        asset_order, cash_order = tree.p.orders()
        assert (asset_order.side.value, asset_order.quantity, asset_order.average_fill_price,
                asset_order.holding_id, asset_order.created_at) == ("BUY", 10, 145.0, tree.holding_id("AAPL"), MON_16)
        assert (cash_order.side.value, cash_order.quantity) == ("SELL", 1_450)
        asset_txn, cash_txn = tree.p.transactions()
        assert [(x.order_id, x.date, x.status.value) for x in (asset_txn, cash_txn)] == \
            [(asset_order.id, MON_16, "EXECUTED"), (cash_order.id, MON_16, "EXECUTED")]

        # valued at the market price (Friday close 150), not the execution price (145)
        assert tree.revalue(MON_16) == CASH + 50.0
        layers = tree.layers(MON_16)
        assert (layers["AAPL"], layers["share_portfolio"], layers["cash_portfolio"]) == (1_500.0, 1_500.0, 98_550.0)

        assert reload(tree, MON_16) == {
            "portfolio": (tree.p.portfolio.id, "TEST"), "cash": 98_550.0, "transactions": 2,
            "main": 100_050.0, "share_portfolio": 1_500.0, "cash_portfolio": 98_550.0,
            "AAPL": (10, 1_500.0), "MSFT": None,
        }

    def test_repeating_the_same_target_is_applied_once(self, tree):
        assert set_holdings(tree, MON_16, AAPL=(5, 150.0)) == {"AAPL": True}
        assert set_holdings(tree, MON_16, AAPL=(5, 150.0)) == {}      # already at target: nothing sent
        assert books(tree) == dict(aapl=5, msft=0, cash=99_250.0, orders=2, txns=2)
        assert tree.p.market_order.call_count == 1

    def test_each_booked_fill_counts_even_when_identical(self, tree):
        """TradeManager books every fill it is given (no idempotency key): de-duplication is the
        target logic of set_holdings, verified above."""
        tree.trade("AAPL", 10, 150.0, MON_16)
        tree.trade("AAPL", 10, 150.0, MON_16)
        assert books(tree) == dict(aapl=20, msft=0, cash=97_000.0, orders=4, txns=4)


class TestSellAndLiquidation:

    def test_partial_sell_changes_only_the_sold_holding(self, tree):
        tree.trade("AAPL", 10, 150.0, MON_16)
        tree.trade("MSFT", 2, 400.0, MON_16)
        tree.revalue(MON_16)
        tree.close("AAPL", MON, 160.0)                                  # no new MSFT bar: still 400

        tree.trade("AAPL", -4, 160.0, TUE_16)
        assert books(tree) == dict(aapl=6, msft=2, cash=98_340.0, orders=6, txns=6)
        assert tree.p.orders()[-2].side.value == "SELL"
        assert tree.revalue(TUE_16) == 100_100.0                       # +100 on AAPL, realised or not
        mon, tue = tree.layers(MON_16), tree.layers(TUE_16)
        assert (tue["AAPL"], tue["MSFT"], tue["share_portfolio"]) == (960.0, 800.0, 1_760.0)
        assert tue["MSFT"] == mon["MSFT"]                               # untouched holding
        tree.assert_consistent(tue)
        assert reload(tree, TUE_16)["AAPL"] == (6, 960.0)

    def test_full_liquidation_keeps_a_zero_holding_worth_nothing(self, tree):
        tree.trade("AAPL", 10, 150.0, MON_16)
        tree.close("AAPL", MON, 160.0)
        assert set_holdings(tree, TUE_16, AAPL=(0, 160.0)) == {"AAPL": True}
        assert books(tree) == dict(aapl=0, msft=0, cash=100_100.0, orders=4, txns=4)

        assert tree.revalue(TUE_16) == 100_100.0
        layers = tree.layers(TUE_16)
        assert (layers["AAPL"], layers["share_portfolio"], layers["cash_portfolio"]) == (0.0, 0.0, 100_100.0)
        # policy: the holding and its position stay (quantity 0) and are reused by the next buy
        hid = tree.holding_id("AAPL")
        assert hid is not None and tree.p.session.get(HoldingModel, hid).position_id is not None
        tree.trade("AAPL", 3, 160.0, TUE_16)
        assert tree.holding_id("AAPL") == hid and tree.p.qty("AAPL") == 3


class TestRejected:

    @pytest.mark.parametrize("ticker, qty, price", [
        ("NOPE", 5, 10.0),          # not a known instrument
        ("AAPL", 5, 0.0),           # no valid price
        ("AAPL", 5, -1.0),
        ("AAPL", 10_000, 150.0),    # 1.5M > cash
    ])
    def test_rejected_target_changes_nothing_in_any_layer(self, tree, ticker, qty, price):
        tree.trade("AAPL", 10, 150.0, MON_16)
        tree.revalue(MON_16)
        books_before, layers_before = books(tree), tree.layers(MON_16)

        targets = {ticker: (qty, price)}
        if ticker != "AAPL":
            targets["AAPL"] = (10, 150.0)                               # keep the held share at its quantity
        assert set_holdings(tree, MON_16, **targets).get(ticker) is False
        assert books(tree) == books_before
        assert tree.revalue(MON_16) == layers_before["main"]
        assert tree.layers(MON_16) == layers_before

    @pytest.mark.parametrize("qty, price", [(0, 150.0), (5, 0.0), (5, -5.0), (5, math.nan), (5, math.inf)])
    def test_trade_manager_refuses_nothing_to_trade_or_no_valid_price(self, tree, qty, price):
        """Regression: a zero-quantity trade was submitted and booked (an order + a 0 cash leg)."""
        tree.p.upm._algorithm.time = MON_16
        assert tree.p.trade("AAPL", qty, price, when=MON_16) is False
        tree.p.market_order.assert_not_called()
        assert books(tree) == dict(aapl=0, msft=0, cash=CASH, orders=0, txns=0)


# ---------------------------------------------------------------------------------------------------
# 4. Hierarchy
# ---------------------------------------------------------------------------------------------------

@pytest.fixture
def invested(tree):
    """Monday: AAPL 10 @ 150, MSFT 5 @ 400 (Friday closes) -> cash 96 500, shares 3 500."""
    tree.trade("AAPL", 10, 150.0, MON_16)
    tree.trade("MSFT", 5, 400.0, MON_16)
    assert tree.revalue(MON_16) == CASH
    return tree


class TestHierarchy:

    def test_trade_in_one_holding_moves_its_branch_and_the_cash_leg_only(self, invested):
        t = invested
        t.close("AAPL", MON, 150.0)
        t.close("MSFT", MON, 400.0)                                     # unchanged prices
        t.trade("AAPL", 5, 148.0, TUE_16)                               # 2 below the close
        assert t.revalue(TUE_16) == 100_010.0
        mon, tue = t.layers(MON_16), t.layers(TUE_16)
        changed = {k for k in tue if tue[k] != mon[k]}
        assert changed == {"AAPL", "share_portfolio", "cash_portfolio", "cash_holding", "main"}
        assert (tue["AAPL"], tue["MSFT"], tue["share_portfolio"], tue["cash_portfolio"]) == \
            (2_250.0, 2_000.0, 4_250.0, 95_760.0)
        t.assert_consistent(tue)

    def test_each_position_is_counted_once(self, invested):
        t = invested
        layers = t.layers(MON_16)
        direct_children = t.p.session.query(HoldingModel).filter_by(container_id=t.p.portfolio.id).all()
        assert sorted(h.holding_type for h in direct_children) == \
            ["CompanySharePortfolioPortfolioHoldings", "CurrencyPortfolioPortfolioHoldings"]
        assert layers["main"] == layers["cash_portfolio"] + layers["share_portfolio"]
        assert layers["main"] != layers["cash_portfolio"] + layers["share_portfolio"] + layers["AAPL"] + layers["MSFT"]
        # one stored total per portfolio and date, one value per holding and date
        assert len(rows_at(t, "Portfolio Value", MON_16)) == 1
        assert len(rows_at(t, "Company Share Portfolio Value", MON_16)) == 1
        assert sorted(v for _, v in rows_at(t, "Portfolio Company Share Holding Value", MON_16)) == [1_500.0, 2_000.0]

    def test_nested_sub_portfolio_propagates_through_every_ancestor(self, tree):
        """main -> TEST_CS -> TEST_CS_NESTED -> MSFT: the nested value is counted once, in its parent."""
        t = tree
        t.trade("AAPL", 10, 150.0, MON_16)
        cs_id = t.share_portfolio_id()
        repo = t.p.factory.get_local_repository("CompanySharePortfolio")
        nested = repo._create_or_get(name="TEST_CS_NESTED")
        s = t.p.session
        link_position = PositionModel(portfolio_id=cs_id, quantity=1, position_type="LONG")
        s.add(link_position)
        s.flush()
        s.add(CompanySharePortfolioPortfolioHoldingModel(asset_id=nested.id, portfolio_id=cs_id, container_id=cs_id,
                                                         start_date=MON_16, position_id=link_position.id))
        s.commit()
        repo.ensure_ticker_holding("MSFT", nested.id, MON_16)
        assert t.p.tm.execute_trade(ticker="MSFT", order_qty=5, price=400.0, portfolio_id=nested.id,
                                    current_time=MON_16, submit_order_fn=t.p.market_order,
                                    main_portfolio_id=t.p.portfolio.id)

        def portfolios(when):
            return dict(rows_at(t, "Company Share Portfolio Value", when))

        assert t.revalue(MON_16) == CASH
        assert portfolios(MON_16) == {nested.id: 2_000.0, cs_id: 3_500.0}
        assert t.p.qty("MSFT") == 5                                     # the manager sees the nested position

        t.close("MSFT", MON, 410.0)                                     # price move inside the nested branch
        assert t.revalue(TUE_16) == CASH + 50.0
        assert portfolios(TUE_16) == {nested.id: 2_050.0, cs_id: 3_550.0}
        assert t.layers(TUE_16)["AAPL"] == 1_500.0                      # sibling branch unchanged


class TestPriceMoveWithoutTransaction:

    def test_values_move_books_do_not(self, invested):
        t = invested
        books_before = books(t)
        t.close("AAPL", MON, 160.0)
        t.close("MSFT", MON, 390.0)
        assert t.revalue(TUE_16) == 100_050.0                           # +100 AAPL, -50 MSFT
        tue = t.layers(TUE_16)
        assert (tue["AAPL"], tue["MSFT"], tue["share_portfolio"], tue["cash_portfolio"]) == \
            (1_600.0, 1_950.0, 3_550.0, 96_500.0)
        assert books(t) == books_before                                 # no order, fill, position or cash change
        assert t.layers(MON_16)["main"] == CASH                         # Monday's snapshot is kept


# ---------------------------------------------------------------------------------------------------
# 5-7. Holding factor resolution, dependencies, transaction -> factor propagation
# ---------------------------------------------------------------------------------------------------

class Resolver:

    def __init__(self, t):
        self.t = t
        self.service = FactorValueResolutionService(factory=t.p.factory, logger=logging.getLogger("context"))
        d = CompanySharePortfolioHoldingValueFactor()
        self.holding_value = t.p.factory.get_local_repository("CompanySharePortfolioHoldingValueFactor")._create_or_get(
            "CompanySharePortfolioHoldingValueFactor", d.name, group=d.group, subgroup=d.subgroup,
            data_type=d.data_type, source=d.source, frequency="1d")
        v = CompanyShareValueFactor()
        self.share_value = t.p.factory.get_local_repository("CompanyShareValueFactor")._create_or_get(
            CompanyShareValueFactor, v.name, group=v.group, subgroup=v.subgroup, data_type=v.data_type,
            source=v.source, frequency="1d")

    def holding(self, ticker):
        return self.t.p.factory.get_local_repository("CompanySharePortfolioHolding").get_by_id(self.t.holding_id(ticker))

    def resolve(self, factor, entity, when, **kw):
        with contextlib.redirect_stdout(io.StringIO()):
            fv = self.service.resolve_factor_value(factor, entity, when, **kw)
        return None if fv is None else float(fv.value)

    def stored(self, factor, entity_id, when):
        return [float(r.value) for r in self.t.p.session.query(FactorValueModel).filter_by(
            factor_id=factor.id, entity_id=entity_id, date=when).order_by(FactorValueModel.id)]


class TestHoldingFactorResolution:

    def test_holding_value_resolves_its_whole_chain_from_raw_closes(self, tree):
        """holding value <- (company_share_value <- mid_price <- close) x Position."""
        tree.trade("AAPL", 10, 150.0, MON_16)
        tree.close("AAPL", MON, 170.0)
        r = Resolver(tree)
        assert r.resolve(r.holding_value, r.holding("AAPL"), TUE_16) == 1_700.0
        aapl = tree.p.factory.company_share_local_repo.get_by_symbol("AAPL").id
        assert rows_at(tree, "mid_price", TUE_16) == [(aapl, 170.0)]
        assert rows_at(tree, "company_share_value", TUE_16) == [(aapl, 170.0)]
        assert r.stored(r.holding_value, r.holding("AAPL").id, TUE_16) == [1_700.0]

    def test_a_stored_holding_value_is_reused_until_recalculated_after_a_trade(self, tree):
        """Policy: an existing value is reused; after a transaction the caller must force a recalculation
        (PortfolioService always does, so portfolio valuations never use a stale holding value)."""
        tree.trade("AAPL", 10, 150.0, MON_16)
        r = Resolver(tree)
        assert r.resolve(r.holding_value, r.holding("AAPL"), MON_16) == 1_500.0
        tree.trade("AAPL", 5, 150.0, MON_16)
        assert r.resolve(r.holding_value, r.holding("AAPL"), MON_16) == 1_500.0      # reused (stale)
        assert r.resolve(r.holding_value, r.holding("AAPL"), MON_16, force_recalculate=True) == 2_250.0
        assert tree.revalue(MON_16) == CASH and tree.layers(MON_16)["AAPL"] == 2_250.0

    def test_shared_prerequisite_is_stored_once_per_entity_and_date(self, tree):
        tree.trade("AAPL", 10, 150.0, MON_16)
        r = Resolver(tree)
        share = tree.p.factory.company_share_local_repo.get_by_symbol("AAPL")
        assert r.resolve(r.holding_value, r.holding("AAPL"), MON_16) == 1_500.0
        assert r.resolve(r.share_value, share, MON_16) == 150.0
        assert rows_at(tree, "mid_price", MON_16) == [(share.id, 150.0)]
        assert rows_at(tree, "company_share_value", MON_16) == [(share.id, 150.0)]

    def test_unpriced_holding_gives_no_value_and_no_parent_totals(self):
        t = Tree()
        try:
            t.close("AAPL", FRI, 150.0)                                 # MSFT has no price at all
            t.trade("AAPL", 10, 150.0, MON_16)
            t.trade("MSFT", 2, 400.0, MON_16)
            r = Resolver(t)
            assert r.resolve(r.holding_value, r.holding("MSFT"), MON_16) is None
            with pytest.raises(ValueError, match="no price available"):
                t.revalue(MON_16)
            # no total is stored for any portfolio at that date, and no MSFT value appears as zero
            assert rows_at(t, "Portfolio Value", MON_16) == []
            assert rows_at(t, "Company Share Portfolio Value", MON_16) == []
            assert r.stored(r.holding_value, r.holding("MSFT").id, MON_16) == []
            # and nothing is traded on a portfolio value that cannot be computed
            orders = len(t.p.orders())
            assert not any(set_holdings(t, MON_16, AAPL=(20, 150.0)).values())
            assert len(t.p.orders()) == orders
        finally:
            t.p.close()


@pytest.fixture
def ctx():
    c = Context()                                                       # AAPL, MSFT, NODATA shares
    c.p.seed_close("AAPL", FRI, 150.0)
    c.p.seed_close("MSFT", FRI, 400.0)
    c.p.seed_close("AAPL", MON, 155.0)
    yield c
    c.p.close()


class TestDependencyGraph:

    def test_batch_maps_every_value_to_its_entity_and_date(self, ctx):
        batch = FactorValueBatchResolutionService(ctx.p.factory, logger=logging.getLogger("context"))
        ids = {t: ctx.share(t).id for t in ("AAPL", "MSFT", "NODATA")}
        with contextlib.redirect_stdout(io.StringIO()):
            result = batch.resolve_batch(ctx.value_factor, [ctx.share(t) for t in ids], [MON_16, TUE_16])
        got = sorted((v.entity_id, v.date, float(v.value)) for v in result.values_for_factor(ctx.value_factor.id))
        assert got == sorted([(ids["AAPL"], MON_16, 150.0), (ids["AAPL"], TUE_16, 155.0),
                              (ids["MSFT"], MON_16, 400.0), (ids["MSFT"], TUE_16, 400.0)])
        assert sorted(result.failed[ctx.value_factor.id]) == [(ids["NODATA"], MON_16), (ids["NODATA"], TUE_16)]
        assert [r for r in ctx.stored() if r[1] == ids["NODATA"]] == []

    def test_batch_plans_and_resolves_the_real_prerequisites_first(self, ctx):
        """Regression: DependencySpec prerequisites never entered the batch graph (matches_factor was
        called with one argument and the TypeError swallowed)."""
        ctx.resolve("AAPL", MON_16)                                     # close / mid_price definitions stored
        batch = FactorValueBatchResolutionService(ctx.p.factory, logger=logging.getLogger("context"))
        ids = {t: ctx.share(t).id for t in ("AAPL", "MSFT", "NODATA")}
        with contextlib.redirect_stdout(io.StringIO()):
            result = batch.resolve_batch(ctx.value_factor, [ctx.share(t) for t in ids], [MON_16, TUE_16])
        assert [f.name for f in result.execution_order] == ["close", "mid_price", "company_share_value"]
        by_name = {f.name: f.id for f in result.execution_order}

        def values(name):
            return sorted((v.entity_id, v.date, float(v.value)) for v in result.values_for_factor(by_name[name]))

        # each (entity, date) gets the last CLOSED bar: Monday 16:00 <- Friday's bar, Tuesday <- Monday's
        expected = [(ids["AAPL"], MON_16, 150.0), (ids["AAPL"], TUE_16, 155.0),
                    (ids["MSFT"], MON_16, 400.0), (ids["MSFT"], TUE_16, 400.0)]
        assert values("mid_price") == values("company_share_value") == expected
        for name in by_name:
            assert sorted(result.failed[by_name[name]]) == [(ids["NODATA"], MON_16), (ids["NODATA"], TUE_16)]

    def test_batch_prerequisites_are_restricted_to_the_declared_factor_type(self, ctx):
        """A stored factor of another type with the same group / subgroup / source is not a prerequisite."""
        from src.domain.entities.factor.finance.financial_assets.currency.currency_value_factor import CurrencyValueFactor
        d = CurrencyValueFactor()
        other = ctx.p.factory.get_local_repository("CurrencyValueFactor")._create_or_get(
            CurrencyValueFactor, d.name, group="value", subgroup="asset", source="calculated",
            data_type=d.data_type, frequency="1d")
        assert other is not None
        ctx.resolve("AAPL", MON_16)
        batch = FactorValueBatchResolutionService(ctx.p.factory, logger=logging.getLogger("context"))
        holding_value = CompanySharePortfolioHoldingValueFactor()
        holding_value.id = -1                                           # not stored: only its specs matter
        deps = batch._collect_dynamic_dep_factors(holding_value)
        assert [(f.id, f.name) for f in deps] == [(ctx.value_factor.id, "company_share_value")]

    def test_batch_detects_a_cycle_in_the_real_chain_before_resolving(self, ctx):
        from src.application.services.data.entities.factor.exceptions import FactorDependencyCycleError
        cyclic = [DependencySpec(factor_type=CompanyShareValueFactor, group="value", subgroup="asset",
                                 source="calculated")]
        ctx.resolve("AAPL", MON_16)
        rows = len(ctx.p.factor_values("company_share_value")) + len(ctx.p.factor_values("mid_price"))
        batch = FactorValueBatchResolutionService(ctx.p.factory, logger=logging.getLogger("context"))
        with patch.object(CompanyShareMidPriceFactor, "calculate_dependencies", new_callable=PropertyMock,
                          return_value=cyclic):
            with pytest.raises(FactorDependencyCycleError) as cycle:
                batch.resolve_batch(ctx.value_factor, [ctx.share("MSFT")], [WED_16])
        assert {"mid_price", "company_share_value"} <= set(cycle.value.cycle_names)
        assert len(ctx.p.factor_values("company_share_value")) + len(ctx.p.factor_values("mid_price")) == rows

    def test_cycle_terminates_without_storing_partial_results(self, ctx):
        cyclic = [DependencySpec(factor_type=CompanyShareValueFactor, group="value", subgroup="asset",
                                 source="calculated")]
        ctx.resolve("AAPL", MON_16)                                     # both definitions exist
        with patch.object(CompanyShareMidPriceFactor, "calculate_dependencies", new_callable=PropertyMock,
                          return_value=cyclic):
            started = time.perf_counter()
            assert ctx.resolve("MSFT", WED_16, force_recalculate=True) is None
            assert time.perf_counter() - started < 30
        assert [r for r in ctx.stored() if r[2] == WED_16] == []
        assert [r for r in ctx.p.factor_values("mid_price") if r[2] == WED_16] == []


# ---------------------------------------------------------------------------------------------------
# 8. Temporal correctness
# ---------------------------------------------------------------------------------------------------

class TestTemporal:

    def test_a_revaluation_writes_only_at_its_valuation_timestamp(self, invested):
        t = invested
        t.close("AAPL", MON, 160.0)
        last_id = t.p.session.query(FactorValueModel.id).order_by(FactorValueModel.id.desc()).first()[0]
        mon_rows = {(r.factor_id, r.entity_id, r.value) for r in
                    t.p.session.query(FactorValueModel).filter(FactorValueModel.date == MON_16)}
        t.revalue(TUE_16)
        new_dates = {r.date for r in t.p.session.query(FactorValueModel).filter(FactorValueModel.id > last_id)}
        assert new_dates == {TUE_16}
        assert {(r.factor_id, r.entity_id, r.value) for r in
                t.p.session.query(FactorValueModel).filter(FactorValueModel.date == MON_16)} == mon_rows

    @pytest.mark.xfail(strict=True, reason="ACCEPTED (2026-10-14): positions carry no history — revaluing a past date after a later "
                                           "trade uses today's quantities and overwrites that date's stored snapshot")
    def test_revaluing_a_past_date_uses_the_quantities_held_then(self, tree):
        tree.trade("AAPL", 10, 150.0, MON_16)
        assert tree.revalue(MON_16) == CASH
        tree.close("AAPL", MON, 160.0)
        tree.trade("AAPL", 10, 160.0, TUE_16)
        assert tree.revalue(TUE_16) == 100_100.0
        assert tree.revalue(MON_16) == CASH
        assert tree.layers(MON_16)["AAPL"] == 1_500.0


# ---------------------------------------------------------------------------------------------------
# 9. Failures during valuation (booking atomicity: test_resilience.py)
# ---------------------------------------------------------------------------------------------------

class TestValuationFailures:

    def test_failure_storing_a_valuation_leaves_the_books_and_earlier_snapshots_intact(self, invested):
        t = invested
        books_before, mon = books(t), t.layers(MON_16)
        repo = t.p.factory.factor_value_local_repo
        with patch.object(type(repo), "add", side_effect=RuntimeError("database unavailable")), \
                patch.object(type(repo), "update", side_effect=RuntimeError("database unavailable")):
            with pytest.raises(Exception):
                t.revalue(TUE_16)
        t.p.session.rollback()
        assert books(t) == books_before
        assert rows_at(t, "Portfolio Value", TUE_16) == []
        assert t.layers(MON_16) == mon
        assert t.revalue(TUE_16) == CASH                                # recovers once the store works


# ---------------------------------------------------------------------------------------------------
# Level 2: the same workflow persisted on SQLite (foreign keys on) and on the SQL Server test database
# ---------------------------------------------------------------------------------------------------

def test_transaction_and_valuations_persist_and_reload(backend):
    t = Tree(engine=backend.engine)
    try:
        t.close("AAPL", FRI, 150.0)
        t.close("MSFT", FRI, 400.0)
        t.trade("AAPL", 10, 145.0, MON_16)
        t.trade("MSFT", 2, 400.0, MON_16)
        t.close("AAPL", MON, 160.0)
        t.trade("AAPL", -4, 160.0, TUE_16)
        assert t.revalue(TUE_16) == pytest.approx(98_390.0 + 960.0 + 800.0)
        state = reload(t, TUE_16)
        assert state["cash"] == 98_390.0 and state["transactions"] == 6
        assert state["AAPL"] == (6, 960.0) and state["MSFT"] == (2, 800.0)
        assert (state["share_portfolio"], state["cash_portfolio"], state["main"]) == (1_760.0, 98_390.0, 100_150.0)
    finally:
        t.p.close()
