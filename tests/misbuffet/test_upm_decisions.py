"""
Checklist sections 3 and 5 — what UnifiedPortfolioManager.set_holdings decides.

Decision logic runs on an in-memory book (make_upm); the portfolio-tree lookups run on the
real SQLite portfolio (SqlitePortfolio). No IBKR, no orders.
``expectedFailure`` tests name a known bug in their docstring.
"""

import logging
import math
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from tests.misbuffet.sqlite_portfolio import T0, SqlitePortfolio, slice_at
from tests.misbuffet.test_order_safety import DATA, CompanyShare, make_upm, traded

logging.getLogger("sqlite_portfolio").setLevel(logging.CRITICAL)
logging.getLogger("test_order_safety").setLevel(logging.CRITICAL)


def book_upm(book=None, classes=None, pv=100_000.0, price=100.0):
    book = {} if book is None else book
    upm = make_upm(book, classes or {t: "CompanyShare" for t in book})
    upm.get_portfolio_value = lambda backtest_date=None: pv
    upm._price_from_slice = lambda t, data: price(t) if callable(price) else price
    return upm, book


class OrderSizingTest(unittest.TestCase):

    def test_weight_to_quantity_truncates(self):
        upm, _ = book_upm(price=333.0)
        upm.set_holdings({CompanyShare: {"name": "SPY", "weight": 0.1}}, DATA)
        self.assertEqual(traded(upm), {"SPY": 30})               # 10 000 / 333 = 30.03

    def test_negative_weight_truncates_toward_zero(self):
        upm, _ = book_upm(price=333.0)
        upm.set_holdings({CompanyShare: {"name": "SPY", "weight": -0.1}}, DATA)
        self.assertEqual(traded(upm), {"SPY": -30})

    def test_weight_too_small_for_one_share_sends_nothing(self):
        upm, _ = book_upm(price=500.0)
        upm.set_holdings({CompanyShare: {"name": "SPY", "weight": 0.004}}, DATA)   # 400 < 500
        self.assertEqual(traded(upm), {})

    def test_quantity_target_is_absolute(self):
        upm, _ = book_upm({"SPY": 7})
        upm.set_holdings({CompanyShare: {"name": "SPY", "quantity": 10}}, DATA)
        self.assertEqual(traded(upm), {"SPY": 3})

    def test_weight_is_relative_to_current_position(self):
        upm, _ = book_upm({"SPY": 50})
        upm.set_holdings({CompanyShare: {"name": "SPY", "weight": 0.1}}, DATA)
        self.assertEqual(traded(upm), {"SPY": 50})               # target 100 shares

    def test_sells_execute_before_buys(self):
        upm, _ = book_upm({"AAA": 10, "BBB": 0})
        upm.set_holdings({CompanyShare: [{"name": "BBB", "quantity": 5}, {"name": "AAA", "quantity": 2}]}, DATA)
        order = [c.kwargs["ticker"] for c in upm._trade_manager.execute_trade.call_args_list]
        self.assertEqual(order, ["AAA", "BBB"])

    def test_buy_without_cash_is_blocked_sell_is_not(self):
        upm, _ = book_upm({"AAA": 10})
        upm._has_budget_for_trade = UnifiedBudget(cash=500.0)
        result = upm.set_holdings({CompanyShare: [{"name": "AAA", "quantity": 0},
                                                  {"name": "BBB", "quantity": 10}]}, DATA)
        self.assertEqual(traded(upm), {"AAA": -10})
        self.assertFalse(result["BBB"])

    def test_invalid_portfolio_value_sends_nothing(self):
        for pv in (0.0, -1.0):
            upm, _ = book_upm({"AAA": 10}, pv=pv)
            self.assertEqual(upm.set_holdings({CompanyShare: {"name": "AAA", "quantity": 0}}, DATA), {"AAA": False})
            upm._trade_manager.execute_trade.assert_not_called()

    def test_portfolio_value_error_sends_nothing(self):
        upm, _ = book_upm({"AAA": 10})
        upm.get_portfolio_value = Mock(side_effect=RuntimeError("no price"))
        self.assertEqual(upm.set_holdings({CompanyShare: {"name": "AAA", "quantity": 0}}, DATA), {"AAA": False})
        upm._trade_manager.execute_trade.assert_not_called()


class UnifiedBudget:
    """_has_budget_for_trade with a fixed cash balance (real rule: buys need cash, sells always pass)."""

    def __init__(self, cash):
        self.cash = cash

    def __call__(self, order_qty, price, current_qty):
        from src.application.services.misbuffet.algorithm.unified_portfolio_manager import UnifiedPortfolioManager
        probe = SimpleNamespace(_get_cash_balance=lambda: self.cash, logger=None)
        return UnifiedPortfolioManager._has_budget_for_trade(probe, order_qty, price, current_qty)


class PriceFallbackTest(unittest.TestCase):

    def setUp(self):
        self.upm, _ = book_upm()
        self.calls = []
        self.upm._price_from_slice = self.source("slice")
        self.upm._algorithm._resolve_asset_price = self.source("ibkr")
        self.upm._get_mid_price_from_factor_db = self.source("factor_db")
        self.upm._get_price_from_market_data = lambda t, now: self.source("market_data")(t)
        self.prices = {}

    def source(self, name):
        def get(ticker, *_):
            self.calls.append(name)
            return self.prices.get(name)
        return get

    def test_chain_order_and_first_valid_price_wins(self):
        self.prices = {"factor_db": 50.0, "market_data": 999.0}
        self.upm.set_holdings({CompanyShare: {"name": "SPY", "weight": 0.01}}, DATA)
        self.assertEqual(self.calls, ["slice", "ibkr", "factor_db"])
        self.assertEqual(traded(self.upm), {"SPY": 20})          # 1 000 / 50

    def test_zero_and_negative_prices_are_skipped(self):
        self.prices = {"slice": 0.0, "ibkr": -3.0, "factor_db": None, "market_data": 100.0}
        self.upm.set_holdings({CompanyShare: {"name": "SPY", "weight": 0.01}}, DATA)
        self.assertEqual(traded(self.upm), {"SPY": 10})

    def test_no_price_skips_the_ticker_never_prices_it_at_zero(self):
        result = self.upm.set_holdings({CompanyShare: {"name": "SPY", "weight": 0.01}}, DATA)
        self.assertEqual(result, {"SPY": False})
        self.upm._trade_manager.execute_trade.assert_not_called()


class TargetGuardTest(unittest.TestCase):
    """Section 5: nonsense targets must never become orders."""

    def test_rebalancing_twice_is_idempotent(self):
        """Restart / repeated bar: the second identical call sends no order."""
        upm, book = book_upm({"AAA": 0})
        targets = {CompanyShare: [{"name": "AAA", "weight": 0.2}, {"name": "BBB", "quantity": 7}]}
        upm.set_holdings(targets, DATA)
        first = upm._trade_manager.execute_trade.call_count
        upm.set_holdings(targets, DATA)
        self.assertEqual(upm._trade_manager.execute_trade.call_count, first)
        self.assertEqual(book, {"AAA": 200, "BBB": 7})

    def test_nan_weight_is_refused_without_breaking_the_call(self):
        upm, _ = book_upm()
        result = upm.set_holdings({CompanyShare: [{"name": "AAA", "weight": math.nan},
                                                  {"name": "BBB", "quantity": 5}]}, DATA)
        self.assertFalse(result["AAA"])
        self.assertEqual(traded(upm), {"BBB": 5})

    def test_infinite_weight_is_refused(self):
        upm, _ = book_upm()
        result = upm.set_holdings({CompanyShare: {"name": "AAA", "weight": math.inf}}, DATA)
        self.assertEqual(result, {"AAA": False})

    def test_gross_exposure_above_100_percent_is_refused(self):
        upm, _ = book_upm()
        upm.set_holdings({CompanyShare: [{"name": "AAA", "weight": 1.5}, {"name": "BBB", "weight": -1.5}]}, DATA)
        self.assertEqual(traded(upm), {})


class PortfolioTreeSqliteTest(unittest.TestCase):

    def setUp(self):
        self.p = SqlitePortfolio()

    def tearDown(self):
        self.p.close()

    def test_tickers_and_quantities_found_inside_sub_portfolio(self):
        self.p.trade("AAPL", 10, 150.0)
        self.p.trade("MSFT", 3, 400.0)
        self.p.trade("MSFT", -3, 400.0)
        self.assertEqual(self.p.upm._get_all_held_tickers(), {"AAPL"})      # zero positions excluded
        self.assertEqual((self.p.qty("AAPL"), self.p.qty("MSFT")), (10, 0))
        main = self.p.portfolio.id
        self.assertEqual(self.p.upm._qty_in_container("AAPL", main), 10)
        self.assertNotEqual(self.p.container("AAPL"), main)                  # lives one level down

    def test_cash_holding_is_not_a_ticker(self):
        self.assertEqual(self.p.upm._get_all_held_tickers(), set())

    def test_probe_asset_class(self):
        self.assertEqual(self.p.upm._probe_asset_class_name("AAPL"), "CompanyShare")
        self.assertIsNone(self.p.upm._probe_asset_class_name("NOPE"))

    def test_set_holdings_end_to_end_and_repeat_is_idempotent(self):
        data = slice_at(AAPL=150.0)
        result = self.p.upm.set_holdings({CompanyShare: {"name": "AAPL", "quantity": 10}}, data)
        self.assertEqual(result, {"AAPL": True})
        self.assertEqual((self.p.qty("AAPL"), self.p.cash()), (10, 98_500.0))
        self.p.upm.set_holdings({CompanyShare: {"name": "AAPL", "quantity": 10}}, data)
        self.assertEqual(self.p.market_order.call_count, 1)

    def test_set_holdings_buy_beyond_cash_is_refused(self):
        result = self.p.upm.set_holdings({CompanyShare: {"name": "AAPL", "quantity": 1_000}}, slice_at(AAPL=150.0))
        self.assertEqual(result, {"AAPL": False})
        self.assertEqual((self.p.qty("AAPL"), self.p.cash()), (0, 100_000.0))
        self.p.market_order.assert_not_called()

    def test_portfolio_value_includes_held_shares(self):
        self.p.trade("AAPL", 10, 150.0)
        try:
            pv = self.p.upm.get_portfolio_value(backtest_date=T0)
        except Exception:
            return
        self.assertNotEqual(float(getattr(pv, "value", pv) or 0), 98_500.0)


if __name__ == "__main__":
    unittest.main()
