"""
End-to-end chain tests: one set_holdings call, then every link the algorithm CLAUDE.md describes
is checked in the database, together with how the links point at each other.

  Portfolio → CompanySharePortfolioPortfolioHolding → CompanySharePortfolio
            → CompanySharePortfolioHolding (asset = the share) → Position
  Account → Order (holding_id, account_id) → Transaction (order_id)
  cash leg: CurrencyPortfolio holding → cash Order → CASH_ Transaction → cash Position

and the portfolio-value chain persisted by get_portfolio_value:

  raw close (previous session) → CompanyShareMidPrice → CompanyShareValue
  → Portfolio Company Share Holding Value (qty × price) → Company Share Portfolio Value
  cash Position → Currency Portfolio Holding Value → Currency Portfolio Value
  → Portfolio Value = Σ sub-portfolio values

In-memory SQLite built through the real repositories; orders go to a Mock. No IBKR.
"""

import logging
import unittest
from datetime import datetime, timedelta

from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare
from src.infrastructure.models.finance.holding.company_share_portfolio_holding import CompanySharePortfolioHoldingModel
from src.infrastructure.models.finance.holding.company_share_portfolio_portfolio_holding import (
    CompanySharePortfolioPortfolioHoldingModel,
)
from src.infrastructure.models.finance.holding.currency_portfolio_holding import CurrencyPortfolioHoldingModel
from src.infrastructure.models.finance.position import PositionModel
from tests.misbuffet.sqlite_portfolio import T0, SqlitePortfolio, slice_at

logging.getLogger("sqlite_portfolio").setLevel(logging.CRITICAL)
logging.getLogger("src.application.services.data.entities.factor.factor_value_resolution_service").setLevel(logging.CRITICAL)

PREV_SESSION = datetime(2026, 1, 2)          # Friday daily bar: closed before the Monday T0 decision
T1 = T0 + timedelta(days=1)


def name_of(value):
    return getattr(value, "name", str(value).split(".")[-1])


class ChainBase(unittest.TestCase):

    SHARES = ("AAPL", "MSFT")

    def setUp(self):
        self.p = SqlitePortfolio(cash=100_000.0, shares=self.SHARES)
        self.p.upm._algorithm.bar_size_setting = "1 day"
        self.s = self.p.session

    def tearDown(self):
        self.p.close()

    def at(self, when):
        """Advance the algorithm clock (get_portfolio_value prefers algorithm.time over backtest_date)."""
        self.p.upm._algorithm.time = when

    def hold(self, qty, ticker="AAPL", price=150.0, when=T0):
        self.at(when)
        return self.p.upm.set_holdings({CompanyShare: {"name": ticker, "quantity": qty}},
                                       slice_at(when, **{ticker: price}))

    def share_id(self, ticker):
        return self.p.factory.company_share_local_repo.get_by_symbol(ticker).id

    def share_holding(self, ticker):
        return self.s.query(CompanySharePortfolioHoldingModel).filter_by(asset_id=self.share_id(ticker)).one()

    def position(self, holding):
        return self.s.query(PositionModel).filter_by(id=holding.position_id).one()

    def cash_holding(self):
        return self.s.query(CurrencyPortfolioHoldingModel).one()

    def asset_orders(self):
        return [o for o in self.p.orders() if not str(o.external_order_id).startswith("CASH_")]

    def cash_orders(self):
        return [o for o in self.p.orders() if str(o.external_order_id).startswith("CASH_")]


class SetHoldingsBuyChainTest(ChainBase):
    """10 AAPL @ 150 from a flat book."""

    def setUp(self):
        super().setUp()
        self.result = self.hold(10)

    def test_result(self):
        self.assertEqual(self.result, {"AAPL": True})
        self.p.market_order.assert_called_once()
        self.assertEqual(self.p.market_order.call_args.args[:2], ("AAPL", 10))

    def test_portfolio_tree_main_to_sub_portfolio_to_share(self):
        link = self.s.query(CompanySharePortfolioPortfolioHoldingModel).filter_by(
            container_id=self.p.portfolio.id).one()
        holding = self.share_holding("AAPL")
        self.assertEqual(holding.container_id, link.asset_id)          # share held inside the sub-portfolio
        self.assertNotEqual(link.asset_id, self.p.portfolio.id)
        self.assertEqual(holding.asset_id, self.share_id("AAPL"))

    def test_position_belongs_to_the_holding(self):
        holding = self.share_holding("AAPL")
        self.assertIsNotNone(holding.position_id)
        pos = self.position(holding)
        self.assertEqual((pos.quantity, name_of(pos.position_type), pos.portfolio_id),
                         (10, "LONG", holding.container_id))

    def test_account_exists_and_both_orders_use_it(self):
        from src.infrastructure.models.finance.account import AccountModel
        account = self.s.query(AccountModel).one()
        self.assertEqual({o.account_id for o in self.p.orders()}, {account.id})

    def test_asset_order_points_to_the_share_holding(self):
        order, = self.asset_orders()
        self.assertEqual((order.holding_id, name_of(order.side), order.quantity, name_of(order.status),
                          order.created_at, order.external_order_id),
                         (self.share_holding("AAPL").id, "BUY", 10, "FILLED", T0, "QC1"))

    def test_asset_transaction_points_to_the_asset_order(self):
        order, = self.asset_orders()
        txn, = [t for t in self.p.transactions() if t.order_id == order.id]
        self.assertTrue(txn.transaction_id.startswith("TXN_QC1_"))
        self.assertEqual((txn.date, txn.trade_date, txn.value_date, txn.settlement_date, name_of(txn.status)),
                         (T0, T0.date(), T0.date(), T0.date(), "EXECUTED"))

    def test_cash_leg_order_transaction_and_position(self):
        order, = self.cash_orders()
        cash = self.cash_holding()
        self.assertEqual((order.holding_id, name_of(order.side), order.quantity, name_of(order.status), order.created_at),
                         (cash.id, "SELL", 1_500, "FILLED", T0))
        txn, = [t for t in self.p.transactions() if t.order_id == order.id]
        self.assertTrue(txn.transaction_id.startswith("CASH_TXN_"))
        self.assertEqual((txn.date, name_of(txn.status)), (T0, "EXECUTED"))
        self.assertEqual(self.position(cash).quantity, 98_500)

    def test_nothing_else_is_written(self):
        self.assertEqual((len(self.p.orders()), len(self.p.transactions())), (2, 2))
        self.assertEqual(self.s.query(CompanySharePortfolioHoldingModel).count(), 1)
        self.assertEqual(self.s.query(CompanySharePortfolioPortfolioHoldingModel).count(), 1)

    def test_read_back_through_the_manager(self):
        self.assertEqual(self.p.qty("AAPL"), 10)
        self.assertEqual(self.p.upm._get_all_held_tickers(), {"AAPL"})
        self.assertEqual(self.p.cash(), 98_500.0)


class SetHoldingsFollowUpChainTest(ChainBase):
    """What the chain looks like after the second call: sell, liquidation, short, refusal."""

    def test_partial_sell_reuses_holding_and_returns_cash(self):
        self.hold(10)
        self.hold(4, when=T1)
        sells = [o for o in self.asset_orders() if name_of(o.side) == "SELL"]
        self.assertEqual([(o.quantity, o.created_at, o.holding_id) for o in sells],
                         [(6, T1, self.share_holding("AAPL").id)])
        self.assertEqual(self.position(self.share_holding("AAPL")).quantity, 4)
        cash_buy, = [o for o in self.cash_orders() if name_of(o.side) == "BUY"]
        self.assertEqual(cash_buy.quantity, 900)
        self.assertEqual(self.p.cash(), 99_400.0)
        self.assertEqual(len(self.p.transactions()), 4)

    def test_unlisted_same_class_ticker_is_liquidated_through_the_chain(self):
        self.hold(10)
        self.at(T1)
        self.p.upm.set_holdings({CompanyShare: {"name": "MSFT", "quantity": 2}}, slice_at(T1, AAPL=150.0, MSFT=400.0))
        self.assertEqual(self.position(self.share_holding("AAPL")).quantity, 0)
        self.assertEqual(self.position(self.share_holding("MSFT")).quantity, 2)
        self.assertEqual(self.p.upm._get_all_held_tickers(), {"MSFT"})
        self.assertEqual(self.p.cash(), 100_000.0 - 1_500 + 1_500 - 800)
        liquidation, = [o for o in self.asset_orders() if name_of(o.side) == "SELL"]
        self.assertEqual((liquidation.quantity, liquidation.holding_id), (10, self.share_holding("AAPL").id))

    def test_short_from_flat(self):
        self.hold(-3)
        pos = self.position(self.share_holding("AAPL"))
        self.assertEqual((pos.quantity, name_of(pos.position_type)), (-3, "SHORT"))
        self.assertEqual(self.p.cash(), 100_450.0)

    def test_refused_buy_writes_no_order_transaction_or_cash(self):
        self.assertEqual(self.hold(10_000), {"AAPL": False})
        self.assertEqual((self.p.orders(), self.p.transactions(), self.p.cash()), ([], [], 100_000.0))
        self.p.market_order.assert_not_called()


class PortfolioValueChainTest(ChainBase):
    """
    ZZZ is created first and priced at 999, so share ids (ZZZ, AAPL, MSFT) never coincide with
    the holding ids — a value can only be right if each holding is priced through its own share.
    """

    SHARES = ("ZZZ", "AAPL", "MSFT")

    def setUp(self):
        super().setUp()
        self.p.seed_close("ZZZ", PREV_SESSION, 999.0)
        self.p.seed_close("AAPL", PREV_SESSION, 150.0)
        self.p.seed_close("MSFT", PREV_SESSION, 400.0)

    def value(self, when=T0):
        self.at(when)
        pv = self.p.upm.get_portfolio_value(backtest_date=when)
        return float(getattr(pv, "value", pv))

    def latest(self, factor_name, entity_id=None, when=T0):
        rows = [r for r in self.p.factor_values(factor_name)
                if r[2] == when and (entity_id is None or r[1] == entity_id)]
        self.assertTrue(rows, f"no '{factor_name}' value stored at {when}")
        return rows[-1][3]

    def test_flat_book_is_worth_its_cash_through_every_level(self):
        self.assertEqual(self.value(), 100_000.0)
        self.assertEqual(self.latest("Currency Portfolio Holding Value"), 100_000.0)
        self.assertEqual(self.latest("Currency Portfolio Value"), 100_000.0)
        self.assertEqual(self.latest("Portfolio Value", self.p.portfolio.id), 100_000.0)
        self.assertEqual(self.latest("currency_value"), 1.0)

    def test_holding_value_is_quantity_times_previous_close(self):
        self.hold(10)
        self.assertEqual(self.value(), 100_000.0)
        holding = self.share_holding("AAPL")
        self.assertEqual(self.latest("Portfolio Company Share Holding Value", holding.id), 1_500.0)
        self.assertEqual(self.latest("Company Share Portfolio Value", holding.container_id), 1_500.0)
        self.assertEqual(self.latest("Currency Portfolio Value"), 98_500.0)

    def test_portfolio_value_is_the_sum_of_its_sub_portfolios(self):
        self.p.upm.set_holdings({CompanyShare: [{"name": "AAPL", "quantity": 10}, {"name": "MSFT", "quantity": 5}]},
                                slice_at(T0, AAPL=150.0, MSFT=400.0))
        total = self.value()
        shares = self.latest("Company Share Portfolio Value", self.share_holding("AAPL").container_id)
        cash = self.latest("Currency Portfolio Value")
        self.assertEqual((shares, cash), (1_500.0 + 2_000.0, 100_000.0 - 3_500.0))
        self.assertEqual(total, shares + cash)
        self.assertEqual(self.latest("Portfolio Value", self.p.portfolio.id), total)

    @unittest.expectedFailure
    def test_new_close_revalues_the_holding(self):
        """BUG (stale price): on the next bar the holding value is recomputed from the
        company_share_value stored on the previous date — no new mid_price / company_share_value is
        derived from the newer close, so the portfolio value never follows the market."""
        self.hold(10)
        self.p.seed_close("AAPL", T0.replace(hour=0), 160.0)          # Monday bar, closed by Tuesday
        self.assertEqual(self.value(T1), 98_500.0 + 1_600.0)
        self.assertEqual(self.latest("Portfolio Company Share Holding Value", self.share_holding("AAPL").id, T1), 1_600.0)

    def test_todays_unclosed_bar_is_not_used(self):
        self.hold(10)
        self.p.seed_close("AAPL", T0.replace(hour=0), 999.0)          # same-day bar: not closed at T0
        value = self.value()
        self.assertNotEqual(value, 98_500.0 + 9_990.0)
        self.assertEqual(value, 100_000.0)                            # Friday's 150 is used

    def test_snapshot_is_stored_once_per_date(self):
        self.hold(10)
        self.value()
        self.value()
        rows = [r for r in self.p.factor_values("Portfolio Value") if r[1] == self.p.portfolio.id and r[2] == T0]
        self.assertEqual(len(rows), 1)

    def test_value_snapshot_is_dated_and_daily(self):
        from src.infrastructure.models.factor.factor import FactorModel
        self.value()
        factor = self.s.query(FactorModel).filter_by(name="Portfolio Value").one()
        self.assertEqual(factor.frequency, "1d")
        self.assertEqual({r[2] for r in self.p.factor_values("Portfolio Value")}, {T0})

    def test_weight_targets_are_sized_on_the_full_portfolio_value(self):
        self.hold(10)                                                  # 1 500 in AAPL, 98 500 cash
        self.p.upm.set_holdings({CompanyShare: [{"name": "AAPL", "quantity": 10}, {"name": "MSFT", "weight": 0.1}]},
                                slice_at(T0, AAPL=150.0, MSFT=400.0))
        self.assertEqual(self.p.qty("MSFT"), 25)                      # 100 000 * 0.1 / 400



class PortfolioValueIdCollisionTest(ChainBase):
    """Default share ids (AAPL=4, MSFT=5): buying MSFT first gives the MSFT holding id 4 = AAPL's id."""

    def setUp(self):
        super().setUp()
        self.p.seed_close("AAPL", PREV_SESSION, 150.0)
        self.p.seed_close("MSFT", PREV_SESSION, 400.0)

    def buy(self, ticker, qty):
        self.at(T0)
        self.p.upm.set_holdings({CompanyShare: {"name": ticker, "quantity": qty}},
                                slice_at(T0, AAPL=150.0, MSFT=400.0), liquidate_unlisted=False)

    def test_ids_that_line_up_value_correctly(self):
        self.buy("AAPL", 10)
        self.buy("MSFT", 5)
        self.assertEqual(float(self.p.upm.get_portfolio_value(backtest_date=T0)), 100_000.0)

    @unittest.expectedFailure
    def test_holding_id_equal_to_another_held_share_id_does_not_cross_prices(self):
        """BUG: when a holding's id equals the id of another held share, the value chain prices the
        holding entity itself and reads raw closes by entity_id without the entity type — the AAPL
        and MSFT holdings get each other's / averaged prices (101 875 instead of 100 000)."""
        self.buy("MSFT", 5)                     # MSFT holding id 4 == AAPL share id 4
        self.buy("AAPL", 10)
        self.assertEqual(float(self.p.upm.get_portfolio_value(backtest_date=T0)), 100_000.0)


if __name__ == "__main__":
    unittest.main()
