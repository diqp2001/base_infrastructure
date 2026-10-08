"""IBKR monitoring: no order methods, only read requests, honest account / position views."""

import datetime as dt
import threading
import time
import unittest

from src.application.services.monitoring.ibkr_monitor import (
    FORBIDDEN_METHODS, IBKRMonitor, IBKRReadOnlyViolation, ReadOnlyIBKRClient,
)
from src.application.services.monitoring.status import DISCONNECTED, HEALTHY, STALE, UNKNOWN
from tests.monitoring.helpers import build_service, contract, fed_ibkr_monitor

ALLOWED_REQUESTS = {"connect", "isConnected", "run", "disconnect", "reqCurrentTime", "reqAccountSummary",
                    "cancelAccountSummary", "reqAccountUpdates", "reqPositions", "reqAllOpenOrders"}


class SpyClient:
    """Fake ibapi client: records every call; anything outside the read allow-list fails the test."""
    calls = []
    active_summaries = set()
    max_active_summaries = 0

    def __init__(self, sink):
        self.sink = sink
        self.connected = False

    def __getattr__(self, name):
        def call(*args, **kwargs):
            SpyClient.calls.append(name)
            if name not in ALLOWED_REQUESTS:
                raise AssertionError(f"monitor called a non read-only method: {name}")
            if name == "connect":
                self.connected = True
                threading.Timer(0.05, self.sink._on_ready).start()
                threading.Timer(0.05, lambda: self.sink._on_accounts(["U1234567"])).start()
            if name == "isConnected":
                return self.connected
            if name == "reqCurrentTime":
                self.sink._on_current_time(int(time.time()))
            if name == "reqAccountSummary":                 # subscription stays active after End
                SpyClient.active_summaries.add(args[0])
                SpyClient.max_active_summaries = max(SpyClient.max_active_summaries, len(SpyClient.active_summaries))
                self.sink._on_summary(args[0], "U1234567", "NetLiquidation", "1", "USD")
                self.sink._on_summary_end(args[0])
            if name == "cancelAccountSummary":
                SpyClient.active_summaries.discard(args[0])
            if name == "run":
                while self.connected:
                    time.sleep(0.05)
            if name == "disconnect":
                self.connected = False
            return None
        return call


class ReadOnlyClientTest(unittest.TestCase):

    def test_order_and_configuration_methods_raise(self):
        client = ReadOnlyIBKRClient(sink=IBKRMonitor("h", 1, 1, "paper"))
        for name in FORBIDDEN_METHODS:
            with self.assertRaises(IBKRReadOnlyViolation, msg=name):
                getattr(client, name)(1, None, None)
        for name in ("placeOrder", "cancelOrder", "reqGlobalCancel", "exerciseOptions"):
            self.assertIn(name, FORBIDDEN_METHODS)

    def test_monitor_loop_only_sends_read_requests(self):
        SpyClient.calls = []
        m = IBKRMonitor("ibkr", 4004, 90, "paper", account_interval=1, positions_interval=1, heartbeat_interval=1,
                        client_factory=SpyClient)
        m.start()
        time.sleep(3.0)
        m.stop()
        called = set(SpyClient.calls)
        self.assertTrue({"connect", "reqCurrentTime", "reqAccountSummary", "reqPositions", "reqAllOpenOrders",
                         "reqAccountUpdates"} <= called, called)
        self.assertTrue(called <= ALLOWED_REQUESTS, called - ALLOWED_REQUESTS)
        for forbidden in FORBIDDEN_METHODS:
            self.assertNotIn(forbidden, called)

    def test_account_summary_subscriptions_never_exceed_ibkr_limit(self):
        """IBKR allows 2 active reqAccountSummary subscriptions (error 322 beyond)."""
        SpyClient.calls, SpyClient.active_summaries, SpyClient.max_active_summaries = [], set(), 0
        m = IBKRMonitor("ibkr", 4004, 90, "paper", account_interval=1, positions_interval=5, heartbeat_interval=1,
                        client_factory=SpyClient)
        m.start()
        time.sleep(4.5)
        m.stop()
        self.assertGreaterEqual(SpyClient.calls.count("reqAccountSummary"), 6)       # several refresh cycles
        self.assertLessEqual(SpyClient.max_active_summaries, 2)
        self.assertIsNotNone(m.summary_updated)

    def test_dashboard_requests_never_reach_ibkr(self):
        """API calls read the snapshot only: no client method is called while serving requests."""
        from src.interfaces.flask.monitoring_app import create_monitoring_app
        ibkr = fed_ibkr_monitor()
        ibkr._client = SpyClient(ibkr)
        SpyClient.calls = []
        service = build_service(ibkr=ibkr)
        app = create_monitoring_app(service_provider=lambda: service)
        c = app.test_client()
        for path in ("/monitor/api/status/ibkr", "/monitor/api/account/summary", "/monitor/api/account/positions",
                     "/monitor/api/account/orders", "/monitor/api/status"):
            self.assertEqual(c.get(path).status_code, 200)
        service.stop()
        self.assertEqual([x for x in SpyClient.calls if x != "disconnect"], [])


class AccountViewsTest(unittest.TestCase):

    def setUp(self):
        self.m = fed_ibkr_monitor()

    def test_zero_is_kept_and_missing_is_unavailable(self):
        v = self.m.account_view()["values"]
        self.assertEqual(v["net_liquidation"], {"value": 100250.5, "currency": "USD", "available": True})
        self.assertEqual(v["total_cash_value"], {"value": 0.0, "currency": "USD", "available": True})
        self.assertEqual(v["buying_power"], {"value": None, "currency": None, "available": False})
        self.assertEqual(v["unrealized_pnl"]["value"], 12.5)

    def test_currencies_are_never_combined(self):
        a = self.m.account_view()
        self.assertEqual({c["currency"] for c in a["cash_by_currency"]}, {"USD", "EUR"})
        cash = {c["currency"]: c["cash_balance"] for c in a["cash_by_currency"]}
        self.assertEqual(cash, {"USD": 1000.0, "EUR": -200.0})          # "$LEDGER-" prefix handled
        exposure = {e["currency"]: e for e in a["exposure_by_currency"]}
        self.assertEqual(exposure["USD"]["net"], 4500.0)
        self.assertEqual(exposure["EUR"]["net"], -650.0)
        self.assertEqual(exposure["EUR"]["gross"], 650.0)

    def test_positions_merge_market_values(self):
        rows = {r["symbol"]: r for r in self.m.positions_view()["positions"]}
        self.assertEqual(rows["SPY"]["quantity"], 10)
        self.assertEqual(rows["SPY"]["market_value"], 4500.0)
        self.assertEqual(rows["SAP"]["currency"], "EUR")
        self.assertEqual(rows["SAP"]["unrealized_pnl"], -50.0)

    def test_open_orders_are_reported_with_status(self):
        orders = self.m.orders_view()["orders"]
        self.assertEqual(len(orders), 1)
        o = orders[0]
        self.assertEqual((o["side"], o["order_type"], o["quantity"], o["filled"], o["remaining"], o["status"]),
                         ("BUY", "LMT", 5, 2, 3, "Submitted"))
        self.assertIsNone(o["submitted_at"])

    def test_unset_double_is_unavailable_not_zero(self):
        unset = 1.7976931348623157e308          # ibapi UNSET_DOUBLE
        self.m._on_portfolio(contract(), 10, unset, 4500.0, 400.0, unset, 0.0, "DU1234567")
        self.assertIsNone(self.m.portfolio[756733]["market_price"])
        self.assertIsNone(self.m.portfolio[756733]["unrealized_pnl"])


class ConnectionStateTest(unittest.TestCase):

    def test_states(self):
        m = IBKRMonitor("ibkr", 4004, 90, "paper")
        self.assertEqual(m.connection_view()["status"], UNKNOWN)
        m.last_connect_attempt = dt.datetime.now(dt.timezone.utc)
        m._failure("no API socket at ibkr:4004")
        view = m.connection_view()
        self.assertEqual(view["status"], DISCONNECTED)
        self.assertEqual(view["connection_failures"][0]["message"], "no API socket at ibkr:4004")
        healthy = fed_ibkr_monitor().connection_view()
        self.assertEqual(healthy["status"], HEALTHY)

    def test_paper_live_detection_and_mismatch(self):
        m = fed_ibkr_monitor()
        self.assertEqual(m.detected_mode(), "paper")
        m._on_accounts(["U11111111"])
        view = m.connection_view()
        self.assertEqual(view["detected_mode"], "live")
        self.assertTrue(view["mode_mismatch"])

    def test_informational_errors_are_ignored_and_connectivity_errors_disconnect(self):
        m = fed_ibkr_monitor()
        m._on_error(-1, 2104, "Market data farm connection is OK")
        self.assertEqual(len(m.errors), 0)
        m._on_error(-1, 1100, "Connectivity between IB and TWS has been lost")
        self.assertFalse(m.connected)
        self.assertEqual(m.errors[0]["kind"], "connectivity")

    def test_old_account_data_is_reported_stale(self):
        m = fed_ibkr_monitor()
        m.summary_updated = dt.datetime.now(dt.timezone.utc) - dt.timedelta(hours=1)
        service = build_service(ibkr=m)
        self.assertEqual(service.account_summary()["status"], STALE)
        self.assertTrue(service.account_summary()["stale"])

    def test_disconnected_gateway_keeps_last_values_labelled(self):
        m = fed_ibkr_monitor()
        m.connected = False
        view = build_service(ibkr=m).account_summary()
        self.assertEqual(view["status"], DISCONNECTED)
        self.assertIn("last known", view["error"])
        self.assertEqual(view["data"]["values"]["net_liquidation"]["value"], 100250.5)


if __name__ == "__main__":
    unittest.main()
