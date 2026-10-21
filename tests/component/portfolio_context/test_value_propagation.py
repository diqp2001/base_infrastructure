"""
Value propagation up the portfolio tree:

    stock value (company_share_value)  x  position quantity
        -> holding value ("Portfolio Company Share Holding Value")
            -> share portfolio value ("Company Share Portfolio Value")
                -> main portfolio value ("Portfolio Value")  (+ cash, unchanged unless cash moves)

1. a change of the stock value (new closed bar) moves the holding, the share portfolio and the main
   portfolio by quantity x price change — quantities and cash stay;
2. a change of the position quantity moves the holding, the share portfolio and the main portfolio by
   quantity change x stock value — the stock value stays (a trade also moves cash).

Each step is checked at every layer against independently computed figures, through the valuation used
by the algorithm (get_portfolio_value) and through FactorValueResolutionService.
"""

import contextlib
import io
import logging

import pytest

from src.infrastructure.models.finance.position import PositionModel
from tests.component.portfolio_context.test_portfolio_value_layers import (
    CASH, FRI, MON, MON_16, TUE, TUE_16, WED_16, Tree,
)

AAPL_QTY, MSFT_QTY = 10, 5
AAPL_PX, MSFT_PX = 150.0, 400.0


@pytest.fixture
def tree():
    """Monday 16:00: AAPL 10 and MSFT 5 bought at Friday's closes (150 / 400); cash 96 500."""
    t = Tree()
    t.close("AAPL", FRI, AAPL_PX)
    t.close("MSFT", FRI, MSFT_PX)
    t.trade("AAPL", AAPL_QTY, AAPL_PX, MON_16)
    t.trade("MSFT", MSFT_QTY, MSFT_PX, MON_16)
    assert t.revalue(MON_16) == CASH
    yield t
    t.p.close()


def chain(t, when, ticker="AAPL"):
    """Stock value, holding value, share-portfolio value and main value stored at `when`."""
    share_id = t.p.factory.company_share_local_repo.get_by_symbol(ticker).id
    stock = [v for (_, entity_id, date, v) in t.p.factor_values("company_share_value")
             if entity_id == share_id and date == when]
    layers = t.layers(when)
    return {"stock": stock[-1] if stock else None, "holding": layers[ticker],
            "share_portfolio": layers["share_portfolio"], "main": layers["main"],
            "cash": layers["cash_portfolio"]}


def books(t):
    return {"AAPL": t.p.qty("AAPL"), "MSFT": t.p.qty("MSFT"), "cash": t.p.cash()}


def set_quantity(t, ticker, quantity):
    """Change the position quantity directly (e.g. a correction / stock split), without any cash."""
    holding = t.p.session.get(__import__(
        "src.infrastructure.models.finance.holding.holding", fromlist=["HoldingModel"]).HoldingModel, t.holding_id(ticker))
    position = t.p.session.get(PositionModel, holding.position_id)
    position.quantity = quantity
    t.p.session.commit()


# ---------------------------------------------------------------------------------------------------
# 1. stock value changes
# ---------------------------------------------------------------------------------------------------

class TestStockValueChangePropagates:

    @pytest.mark.parametrize("new_price", [160.0, 140.0, 150.0])
    def test_every_layer_moves_by_quantity_times_price_change(self, tree, new_price):
        before, books_before = chain(tree, MON_16), books(tree)
        tree.close("AAPL", MON, new_price)                              # Monday's bar, closed by Tuesday
        tree.revalue(TUE_16)
        after = chain(tree, TUE_16)
        delta = AAPL_QTY * (new_price - AAPL_PX)

        assert (before["stock"], after["stock"]) == (AAPL_PX, new_price)
        assert after["holding"] - before["holding"] == pytest.approx(delta)
        assert after["share_portfolio"] - before["share_portfolio"] == pytest.approx(delta)
        assert after["main"] - before["main"] == pytest.approx(delta)
        assert after["holding"] == pytest.approx(AAPL_QTY * new_price)  # holding = quantity x stock value
        assert after["cash"] == before["cash"]                           # no cash movement
        assert books(tree) == books_before                               # no transaction
        msft_before, msft_after = chain(tree, MON_16, "MSFT"), chain(tree, TUE_16, "MSFT")
        assert (msft_after["stock"], msft_after["holding"]) == (msft_before["stock"], msft_before["holding"])

    def test_both_stocks_moving_add_up_in_the_share_portfolio_and_main(self, tree):
        before = chain(tree, MON_16)
        tree.close("AAPL", MON, 155.0)
        tree.close("MSFT", MON, 390.0)
        tree.revalue(TUE_16)
        after = chain(tree, TUE_16)
        delta = AAPL_QTY * 5.0 + MSFT_QTY * -10.0                       # +50 - 50
        assert after["share_portfolio"] - before["share_portfolio"] == pytest.approx(delta)
        assert after["main"] - before["main"] == pytest.approx(delta)
        assert chain(tree, TUE_16, "MSFT")["holding"] == pytest.approx(MSFT_QTY * 390.0)

    def test_successive_price_moves_follow_day_by_day(self, tree):
        prices = {MON: 152.0, TUE: 149.0}                               # Monday's and Tuesday's bars
        expected_main = {TUE_16: CASH + AAPL_QTY * 2.0, WED_16: CASH + AAPL_QTY * -1.0}
        for bar_day, valuation in ((MON, TUE_16), (TUE, WED_16)):
            tree.close("AAPL", bar_day, prices[bar_day])
            tree.close("MSFT", bar_day, MSFT_PX)                        # a bar every session (bars > 4 days are stale)
            tree.revalue(valuation)
            step = chain(tree, valuation)
            assert step["stock"] == prices[bar_day]
            assert step["holding"] == pytest.approx(AAPL_QTY * prices[bar_day])
            assert step["main"] == pytest.approx(expected_main[valuation])


# ---------------------------------------------------------------------------------------------------
# 2. position quantity changes
# ---------------------------------------------------------------------------------------------------

class TestQuantityChangePropagates:

    @pytest.mark.parametrize("new_quantity", [15, 4, 0, -3])
    def test_position_change_without_cash_moves_every_layer(self, tree, new_quantity):
        before = chain(tree, MON_16)
        set_quantity(tree, "AAPL", new_quantity)
        tree.revalue(MON_16)                                             # same date, same price
        after = chain(tree, MON_16)
        delta = (new_quantity - AAPL_QTY) * AAPL_PX

        assert after["stock"] == before["stock"] == AAPL_PX              # the stock value does not move
        assert after["holding"] == pytest.approx(new_quantity * AAPL_PX)
        assert after["share_portfolio"] - before["share_portfolio"] == pytest.approx(delta)
        assert after["main"] - before["main"] == pytest.approx(delta)
        assert after["cash"] == before["cash"]
        assert chain(tree, MON_16, "MSFT")["holding"] == pytest.approx(MSFT_QTY * MSFT_PX)

    def test_buy_moves_holding_and_share_portfolio_cash_pays_for_it(self, tree):
        before = chain(tree, MON_16)
        tree.trade("AAPL", 5, AAPL_PX, MON_16)                          # at the valuation price
        tree.revalue(MON_16)
        after = chain(tree, MON_16)
        assert after["holding"] - before["holding"] == pytest.approx(5 * AAPL_PX)
        assert after["share_portfolio"] - before["share_portfolio"] == pytest.approx(5 * AAPL_PX)
        assert after["cash"] - before["cash"] == pytest.approx(-5 * AAPL_PX)
        assert after["main"] == before["main"]                           # value moved, not created

    def test_sell_above_the_stock_value_raises_the_main_portfolio(self, tree):
        before = chain(tree, MON_16)
        tree.trade("AAPL", -4, 155.0, MON_16)                           # 5 above the 150 valuation
        tree.revalue(MON_16)
        after = chain(tree, MON_16)
        assert after["holding"] == pytest.approx(6 * AAPL_PX)
        assert after["cash"] - before["cash"] == pytest.approx(4 * 155.0)
        assert after["main"] - before["main"] == pytest.approx(4 * 5.0)

    def test_quantity_and_price_change_together(self, tree):
        before = chain(tree, MON_16)
        set_quantity(tree, "AAPL", 12)
        tree.close("AAPL", MON, 160.0)
        tree.revalue(TUE_16)
        after = chain(tree, TUE_16)
        assert after["holding"] == pytest.approx(12 * 160.0)
        assert after["main"] - before["main"] == pytest.approx(12 * 160.0 - AAPL_QTY * AAPL_PX)


# ---------------------------------------------------------------------------------------------------
# 3. the same propagation through FactorValueResolutionService
# ---------------------------------------------------------------------------------------------------

class Service:
    """Resolves the holding / share-portfolio / main-portfolio value factors through the service."""

    def __init__(self, t):
        from src.application.services.data.entities.factor.factor_value_resolution_service import (
            FactorValueResolutionService,
        )
        self.t = t
        self.svc = FactorValueResolutionService(factory=t.p.factory, logger=logging.getLogger("propagation"))
        logging.getLogger("propagation").setLevel(logging.CRITICAL)

    def factor(self, name):
        from tests.component.factor_context.factor_catalog import factor_classes
        cls = dict(factor_classes())[name]
        d = cls()
        return self.t.p.factory.get_local_repository(name)._create_or_get(
            cls, d.name, group=d.group, subgroup=d.subgroup, data_type=d.data_type, source=d.source, frequency="1d")

    def value(self, factor_name, entity, when):
        with contextlib.redirect_stdout(io.StringIO()):
            fv = self.svc.resolve_factor_value(self.factor(factor_name), entity, when, force_recalculate=True)
        return None if fv is None else float(fv.value)

    def chain(self, when):
        from src.infrastructure.models.finance.holding.company_share_portfolio_holding import (
            CompanySharePortfolioHoldingModel,
        )
        f = self.t.p.factory
        holding = f.get_local_repository("CompanySharePortfolioHolding").get_by_id(self.t.holding_id("AAPL"))
        share_portfolio = f.get_local_repository("CompanySharePortfolio").get_by_id(self.t.share_portfolio_id())
        main = f.get_local_repository("Portfolio").get_by_id(self.t.p.portfolio.id)
        assert self.t.p.session.query(CompanySharePortfolioHoldingModel).count() == 2
        link = f.get_local_repository("CompanySharePortfolioPortfolioHolding").get_by_id(
            self.t.p.session.query(__import__(
                "src.infrastructure.models.finance.holding.company_share_portfolio_portfolio_holding",
                fromlist=["CompanySharePortfolioPortfolioHoldingModel"]).CompanySharePortfolioPortfolioHoldingModel).one().id)
        self.main = main
        # bottom-up: each layer recalculated (force_recalculate applies to the requested factor only)
        return {"holding": self.value("CompanySharePortfolioHoldingValueFactor", holding, when),
                "share_portfolio": self.value("CompanySharePortfolioValueFactor", share_portfolio, when),
                "link": self.value("CompanySharePortfolioPortfolioHoldingValueFactor", link, when),
                "main": self.value("PortfolioValueFactor", main, when)}


class TestPropagationThroughTheResolutionService:

    def test_stock_value_change(self, tree):
        svc = Service(tree)
        before = svc.chain(MON_16)
        assert before == pytest.approx({"holding": 1_500.0, "share_portfolio": 3_500.0, "link": 3_500.0,
                                        "main": CASH})
        tree.close("AAPL", MON, 160.0)
        tree.close("MSFT", MON, MSFT_PX)
        after = svc.chain(TUE_16)
        assert after == pytest.approx({"holding": 1_600.0, "share_portfolio": 3_600.0, "link": 3_600.0,
                                       "main": CASH + 100.0})

    def test_quantity_change(self, tree):
        svc = Service(tree)
        svc.chain(MON_16)
        set_quantity(tree, "AAPL", 15)
        after = svc.chain(MON_16)                                       # same date, every layer recalculated
        assert after == pytest.approx({"holding": 2_250.0, "share_portfolio": 4_250.0, "link": 4_250.0,
                                       "main": CASH + 750.0})

    def test_forcing_the_top_factor_alone_picks_up_a_quantity_change(self, tree):
        """BI-028: a forced resolution recomputes every derived value of its chain (it used to reuse the holding /
        share-portfolio values stored for that date)."""
        svc = Service(tree)
        svc.chain(MON_16)
        set_quantity(tree, "AAPL", 15)
        assert svc.value("PortfolioValueFactor", svc.main, MON_16) == pytest.approx(CASH + 750.0)

    def test_forcing_the_top_factor_picks_up_a_corrected_price(self, tree):
        """BI-028: a re-run after a raw price correction gives the value a run on an empty derived store gives."""
        from src.infrastructure.models.factor.factor import CompanyShareFactorModel
        from src.infrastructure.models.factor.factor_value import FactorValueModel
        svc = Service(tree)
        svc.chain(MON_16)
        close = tree.p.session.query(CompanyShareFactorModel).filter_by(name="close", frequency="1d").first()
        aapl = tree.p.factory.company_share_local_repo.get_by_symbol("AAPL").id
        tree.p.session.query(FactorValueModel).filter(FactorValueModel.factor_id == close.id,
                                                      FactorValueModel.entity_id == aapl,
                                                      FactorValueModel.date == FRI).update({FactorValueModel.value: "160.0"})
        tree.p.session.commit()                                          # Friday's AAPL close corrected 150 -> 160
        assert svc.value("PortfolioValueFactor", svc.main, MON_16) == pytest.approx(CASH + AAPL_QTY * 10.0)

    def test_a_share_price_is_never_overwritten_by_a_holding_with_the_same_id(self, tree):
        """Regression: with force_recalculate the write path matched an existing row by (factor, id, date)
        of ANY entity type — the MSFT price computed for holding id 5 replaced AAPL's (share id 5) price."""
        aapl = tree.p.factory.company_share_local_repo.get_by_symbol("AAPL").id
        assert aapl == tree.holding_id("MSFT")                           # the collision this guards
        Service(tree).chain(MON_16)
        prices = {(t, e): v for (t, e, d, v) in tree.p.factor_values("company_share_value") if d == MON_16}
        assert prices[("CompanyShare", aapl)] == AAPL_PX

    def test_share_prices_are_stored_for_shares_only(self, tree):
        """BI-010 (was a strict xfail): a share price factor is never resolved on a share portfolio / holding."""
        Service(tree).chain(MON_16)
        assert {t for (t, _, _, _) in tree.p.factor_values("company_share_value")} == {"CompanyShare"}
