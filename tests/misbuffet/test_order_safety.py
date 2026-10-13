"""
Order safety of UnifiedPortfolioManager.set_holdings + PositionReconciler.

No database, no IBKR connection, no orders: the portfolio manager's DB/price helpers and the
broker snapshot are replaced by in-memory fakes; TradeManager.execute_trade is a Mock.
"""

import logging
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.application.services.misbuffet.algorithm.position_reconciler import (
    BrokerOrder, BrokerSnapshot, IBKRSnapshotProvider, PositionReconciler, instrument_key, normalize_ticker,
)
from src.application.services.misbuffet.algorithm.unified_portfolio_manager import UnifiedPortfolioManager
from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient

OPTION = "SPY   281215C00775000"


class CompanyShare:          # only the class name matters to set_holdings
    pass


class CompanyShareOption:
    pass


def _now():
    return datetime.now(timezone.utc)


def make_upm(holdings, classes, live=False):
    """UPM over an in-memory book {ticker: qty}; execute_trade applies the order to the book."""
    upm = UnifiedPortfolioManager.__new__(UnifiedPortfolioManager)
    upm.logger = logging.getLogger("test_order_safety")
    upm._current_portfolio_entity = SimpleNamespace(id=1)
    upm._algorithm = SimpleNamespace(live_mode=live, market_order=Mock(), time=datetime(2026, 1, 5))
    upm._reconciler = None
    upm.get_portfolio_value = lambda backtest_date=None: 100_000.0
    upm._ensure_asset_container = lambda ticker, now, asset_class=None: 1
    upm._find_existing_container = lambda ticker: 1
    upm._get_all_held_tickers = lambda: {t for t, q in holdings.items() if q}
    upm._get_current_position_qty = lambda t: holdings.get(t, 0)
    upm._probe_asset_class_name = lambda t: classes.get(t)
    upm._price_from_slice = lambda t, data: 100.0
    upm._has_budget_for_trade = lambda *a: True

    def execute_trade(ticker, order_qty, **kw):
        holdings[ticker] = holdings.get(ticker, 0) + order_qty
        return True
    upm._trade_manager = Mock()
    upm._trade_manager.execute_trade.side_effect = execute_trade
    return upm


def traded(upm):
    return {c.kwargs["ticker"]: c.kwargs["order_qty"] for c in upm._trade_manager.execute_trade.call_args_list}


DATA = SimpleNamespace(time=datetime(2026, 1, 5, 16, 0))


class LiquidationScopeTest(unittest.TestCase):

    def setUp(self):
        self.book = {"SPY": 10, OPTION: -2, "QQQ": 5}
        self.classes = {"SPY": "CompanyShare", OPTION: "CompanyShareOption", "QQQ": "CompanyShare"}

    def test_share_call_does_not_sell_options(self):
        """The old bug: a CompanyShare-only call sold every held option of the portfolio."""
        upm = make_upm(self.book, self.classes)
        upm.set_holdings({CompanyShare: {"name": "SPY", "quantity": 10}}, DATA)
        self.assertNotIn(OPTION, traded(upm))
        self.assertEqual(self.book[OPTION], -2)
        self.assertEqual(traded(upm), {"QQQ": -5})        # same class, unlisted -> liquidated

    def test_option_call_does_not_sell_shares(self):
        upm = make_upm(self.book, self.classes)
        upm.set_holdings({CompanyShareOption: {"name": OPTION, "quantity": -3}}, DATA)
        self.assertEqual(traded(upm), {OPTION: -1})

    def test_unscoped_selection_would_have_included_the_option(self):
        """What the old code did for every call (kept only for string-keyed calls)."""
        upm = make_upm(self.book, self.classes)
        held = upm._get_all_held_tickers() - {"SPY"}
        self.assertIn(OPTION, upm._select_liquidations(held, {}, scoped=False, enabled=True))
        self.assertNotIn(OPTION, upm._select_liquidations(held, {"SPY": CompanyShare}, scoped=True, enabled=True))

    def test_string_keys_keep_original_behaviour(self):
        upm = make_upm(self.book, self.classes)
        upm.set_holdings({"SPY": 0.01}, DATA)               # 1000 / 100 = 10 shares -> no SPY order
        self.assertEqual(traded(upm), {OPTION: 2, "QQQ": -5})

    def test_liquidate_unlisted_false(self):
        upm = make_upm(self.book, self.classes)
        upm.set_holdings({CompanyShare: {"name": "SPY", "quantity": 12}}, DATA, liquidate_unlisted=False)
        self.assertEqual(traded(upm), {"SPY": 2})

    def test_unknown_class_is_never_liquidated(self):
        self.classes["QQQ"] = None
        upm = make_upm(self.book, self.classes)
        with self.assertLogs("test_order_safety", "WARNING") as logs:
            upm.set_holdings({CompanyShare: {"name": "SPY", "quantity": 10}}, DATA)
        self.assertEqual(traded(upm), {})
        self.assertTrue(any("QQQ unknown" in m for m in logs.output))

    def test_liquidations_are_logged(self):
        upm = make_upm(self.book, self.classes)
        with self.assertLogs("test_order_safety", "WARNING") as logs:
            upm.set_holdings({CompanyShare: {"name": "SPY", "quantity": 10}}, DATA)
        self.assertTrue(any("liquidating QQQ" in m for m in logs.output))


def snapshot(positions, orders=(), age=0.0, complete=True):
    return BrokerSnapshot(positions=dict(positions), open_orders=list(orders),
                          taken_at=_now() - timedelta(seconds=age), complete=complete)


def working(key, status="Submitted"):
    return BrokerOrder(key=key, order_id=7, perm_id=70, side="BUY", quantity=1, remaining=1, status=status)


class ReconciliationGateTest(unittest.TestCase):

    def setUp(self):
        self.book = {"SPY": 10, OPTION: -2}
        self.classes = {"SPY": "CompanyShare", OPTION: "CompanyShareOption"}

    def test_live_mode_without_reconciler_refuses(self):
        upm = make_upm(self.book, self.classes, live=True)
        result = upm.set_holdings({CompanyShare: {"name": "SPY", "quantity": 20}}, DATA)
        self.assertEqual(result, {"SPY": False})
        upm._trade_manager.execute_trade.assert_not_called()

    def test_backtest_without_reconciler_trades(self):
        upm = make_upm(self.book, self.classes)
        upm.set_holdings({CompanyShare: {"name": "SPY", "quantity": 20}}, DATA)
        self.assertEqual(traded(upm), {"SPY": 10})

    def test_mismatch_blocks_all_trading(self):
        upm = make_upm(self.book, self.classes, live=True)
        upm.attach_reconciler(lambda: snapshot({"SPY": 10, instrument_key("SPY", OPTION, "OPT"): -1}))
        result = upm.set_holdings({CompanyShare: {"name": "SPY", "quantity": 20}}, DATA)
        self.assertEqual(result, {"SPY": False})
        upm._trade_manager.execute_trade.assert_not_called()
        self.assertEqual(upm._reconciler.last_result.mismatches,
                         [{"ticker": OPTION, "strategy_qty": -2.0, "broker_qty": -1.0}])

    def test_matching_broker_allows_trading_and_ignores_unmanaged(self):
        upm = make_upm(self.book, self.classes, live=True)
        upm.attach_reconciler(lambda: snapshot({"SPY": 10, OPTION: -2, "VFV": 300}))
        upm.set_holdings({CompanyShare: {"name": "SPY", "quantity": 20}}, DATA)
        self.assertEqual(traded(upm), {"SPY": 10})
        self.assertEqual(upm._reconciler.last_result.unmanaged_positions, {"VFV": 300})

    def test_working_order_skips_only_that_ticker(self):
        """Restart while yesterday's order is still working: no duplicate order."""
        self.book["QQQ"] = 0
        upm = make_upm(self.book, self.classes, live=True)
        upm.attach_reconciler(lambda: snapshot({"SPY": 10, OPTION: -2}, [working("SPY")]))
        result = upm.set_holdings({CompanyShare: [{"name": "SPY", "quantity": 20},
                                                  {"name": "QQQ", "quantity": 5}]}, DATA)
        self.assertFalse(result["SPY"])
        self.assertEqual(traded(upm), {"QQQ": 5})

    def test_working_order_mismatch_does_not_block(self):
        # fill not yet reported: the strategy's book leads the broker for the pending ticker only
        upm = make_upm(self.book, self.classes, live=True)
        upm.attach_reconciler(lambda: snapshot({"SPY": 4, OPTION: -2}, [working("SPY")]))
        result = upm.set_holdings({CompanyShare: {"name": "SPY", "quantity": 20}}, DATA)
        self.assertTrue(upm._reconciler.last_result.ok)
        self.assertEqual(result, {"SPY": False})

    def test_submitted_ticker_pending_until_newer_snapshot(self):
        upm = make_upm(self.book, self.classes, live=True)
        snaps = {"age": 0.0}
        upm.attach_reconciler(lambda: snapshot({"SPY": self.book["SPY"], OPTION: -2}, age=snaps["age"]))
        upm.set_holdings({CompanyShare: {"name": "SPY", "quantity": 20}}, DATA)
        self.assertEqual(traded(upm), {"SPY": 10})
        snaps["age"] = 30.0                        # cached snapshot taken before the order was sent
        result = upm.set_holdings({CompanyShare: {"name": "SPY", "quantity": 25}}, DATA)
        self.assertEqual(result, {"SPY": False})
        self.assertEqual(upm._trade_manager.execute_trade.call_count, 1)
        snaps["age"] = 0.0                         # fresh snapshot, no working order: cleared
        upm.set_holdings({CompanyShare: {"name": "SPY", "quantity": 25}}, DATA)
        self.assertEqual(upm._trade_manager.execute_trade.call_count, 2)


class PositionReconcilerTest(unittest.TestCase):

    def make(self, provider, book=None):
        book = {"SPY": 10} if book is None else book
        return PositionReconciler(lambda t: book.get(t, 0), lambda: [t for t, q in book.items() if q], provider)

    def test_fail_closed_on_broker_problems(self):
        def boom():
            raise ConnectionError("down")
        for provider, text in ((boom, "unavailable"), (lambda: None, "unavailable"),
                               (lambda: snapshot({"SPY": 10}, complete=False), "incomplete"),
                               (lambda: snapshot({"SPY": 10}, age=600), "old")):
            result = self.make(provider).check()
            self.assertFalse(result.ok)
            self.assertIn(text, result.error)

    def test_position_missing_at_broker(self):
        result = self.make(lambda: snapshot({})).check()
        self.assertFalse(result.ok)
        self.assertEqual(result.mismatches[0]["broker_qty"], 0.0)

    def test_targeted_ticker_held_at_broker_but_not_by_strategy(self):
        result = self.make(lambda: snapshot({"SPY": 10, "QQQ": 3})).check(extra_tickers=["QQQ"])
        self.assertFalse(result.ok)
        self.assertEqual(result.mismatches, [{"ticker": "QQQ", "strategy_qty": 0.0, "broker_qty": 3.0}])

    def test_done_orders_are_not_pending(self):
        result = self.make(lambda: snapshot({"SPY": 10}, [working("SPY", "Filled"),
                                                          working("SPY", "Cancelled")])).check()
        self.assertTrue(result.ok)
        self.assertEqual(result.pending_tickers, set())


class FakeIB:
    def __init__(self, positions, orders, complete=True):
        self.positions_snapshot, self.open_orders_snapshot, self.complete = positions, orders, complete
        self.calls = []

    def is_connected(self):
        return True

    def request_positions_snapshot(self, timeout):
        self.calls.append("positions")
        return self.complete

    def request_open_orders_snapshot(self, timeout):
        self.calls.append("orders")
        return True


class IBKRSnapshotProviderTest(unittest.TestCase):

    def test_keys_and_account_filter(self):
        ib = FakeIB(
            positions=[
                {"account": "U1", "symbol": "SPY", "secType": "STK", "localSymbol": "SPY", "position": 10},
                {"account": "U1", "symbol": "SPY", "secType": "OPT", "localSymbol": OPTION, "position": -2},
                {"account": "U2", "symbol": "SPY", "secType": "STK", "localSymbol": "SPY", "position": 99},
                {"account": "U1", "symbol": "XYZ", "secType": "STK", "localSymbol": "XYZ", "position": 0},
            ],
            orders=[{"account": "U1", "symbol": "SPY", "secType": "OPT", "localSymbol": OPTION,
                     "orderId": 3, "permId": 30, "action": "BUY", "totalQuantity": 1.0,
                     "remaining": None, "status": "PreSubmitted"}])
        snap = IBKRSnapshotProvider(ib, account="U1")()
        self.assertEqual(snap.positions, {"SPY": 10.0, normalize_ticker(OPTION): -2.0})
        self.assertEqual([o.key for o in snap.open_orders if o.working], [normalize_ticker(OPTION)])
        self.assertTrue(snap.complete)
        self.assertEqual(ib.calls, ["positions", "orders"])

    def test_incomplete_and_disconnected(self):
        self.assertFalse(IBKRSnapshotProvider(FakeIB([], [], complete=False))().complete)
        ib = FakeIB([], [])
        ib.is_connected = lambda: False
        with self.assertRaises(ConnectionError):
            IBKRSnapshotProvider(ib)()

    def test_option_key_uses_local_symbol(self):
        self.assertEqual(instrument_key("SPY", OPTION, "OPT"), "SPY 281215C00775000")
        self.assertEqual(instrument_key("SPY", "SPY", "STK"), "SPY")


class IBTWSClientSnapshotTest(unittest.TestCase):
    """Callbacks driven by hand: reqPositions / reqAllOpenOrders are patched, nothing is sent."""

    def setUp(self):
        self.client = IBTWSClient("127.0.0.1", 1, 1)
        self.client.is_connected = lambda: True

    @staticmethod
    def contract(symbol, sec_type, local_symbol, con_id):
        return SimpleNamespace(symbol=symbol, secType=sec_type, exchange="SMART", localSymbol=local_symbol,
                               conId=con_id, currency="USD")

    def test_positions_snapshot(self):
        def req_positions():
            self.client.position("U1", self.contract("SPY", "STK", "SPY", 756733), 10, 500.0)
            self.client.position("U1", self.contract("SPY", "OPT", OPTION, 1234), -2, 3.1)
            self.client.positionEnd()
        with patch.object(self.client, "reqPositions", side_effect=req_positions), \
                patch.object(self.client, "cancelPositions") as cancel:
            self.assertTrue(self.client.request_positions_snapshot(timeout=1))
        cancel.assert_called_once()
        self.assertEqual([(p["localSymbol"], p["conId"], p["position"]) for p in self.client.positions_snapshot],
                         [("SPY", 756733, 10), (OPTION, 1234, -2)])
        # legacy symbol-keyed list still merges the option into the share row
        self.assertEqual(len(self.client.positions), 1)

    def test_positions_snapshot_timeout(self):
        with patch.object(self.client, "reqPositions"), patch.object(self.client, "cancelPositions"):
            self.assertFalse(self.client.request_positions_snapshot(timeout=0.05))

    def test_open_orders_snapshot(self):
        order = SimpleNamespace(permId=55, clientId=0, account="U1", action="SELL", totalQuantity=2,
                                orderType="LMT")
        def req_all():
            self.client.openOrder(9, self.contract("SPY", "OPT", OPTION, 1234), order,
                                  SimpleNamespace(status="Submitted"))
            self.client.openOrderEnd()
        with patch.object(self.client, "reqAllOpenOrders", side_effect=req_all):
            self.assertTrue(self.client.request_open_orders_snapshot(timeout=1))
        row, = self.client.open_orders_snapshot
        self.assertEqual((row["orderId"], row["localSymbol"], row["status"], row["totalQuantity"]),
                         (9, OPTION, "Submitted", 2.0))

    def test_callbacks_outside_a_snapshot_are_not_collected(self):
        self.client.openOrder(1, self.contract("SPY", "STK", "SPY", 1), SimpleNamespace(), SimpleNamespace())
        self.assertEqual(self.client.open_orders_snapshot, [])


if __name__ == "__main__":
    unittest.main()
