"""
Checklist section 4 — the broker reconciliation over time, the account filter, and an opt-in
read-only smoke test against a real IB Gateway.

The smoke test only runs with IBKR_LIVE_SMOKE=1. It reads positions and open orders and
patches every order-sending method of the client to raise, so it cannot place, modify or
cancel anything.
"""

import os
import unittest
from datetime import datetime, timedelta, timezone

from src.application.services.misbuffet.algorithm.position_reconciler import (
    BrokerOrder, BrokerSnapshot, IBKRSnapshotProvider,
)
from tests.misbuffet.test_order_safety import DATA, CompanyShare, FakeIB, make_upm, traded


class Broker:
    """Mutable broker state the reconciler snapshots on every set_holdings call."""

    def __init__(self, positions):
        self.positions, self.orders = dict(positions), []

    def snapshot(self):
        return BrokerSnapshot(positions=dict(self.positions), open_orders=list(self.orders),
                              taken_at=datetime.now(timezone.utc) + timedelta(milliseconds=1))


def working(key):
    return BrokerOrder(key=key, order_id=1, perm_id=1, side="BUY", quantity=10, remaining=10, status="Submitted")


class FillTimingTest(unittest.TestCase):

    def setUp(self):
        self.book = {"SPY": 10, "QQQ": 5}
        self.broker = Broker(self.book)
        self.upm = make_upm(self.book, {"SPY": "CompanyShare", "QQQ": "CompanyShare"}, live=True)
        self.upm.attach_reconciler(self.broker.snapshot)

    def call(self, spy, qqq):
        return self.upm.set_holdings({CompanyShare: [{"name": "SPY", "quantity": spy},
                                                     {"name": "QQQ", "quantity": qqq}]}, DATA)

    def test_order_working_then_filled_then_trading_resumes(self):
        self.call(20, 5)                                   # SPY +10 sent, book SPY=20
        self.assertEqual(traded(self.upm), {"SPY": 10})

        self.broker.orders = [working("SPY")]              # broker: order working, still 10
        result = self.call(25, 8)
        self.assertFalse(result["SPY"])                    # pending: not re-sent, not compared
        self.assertTrue(self.upm._reconciler.last_result.ok)
        self.assertEqual(self.upm._trade_manager.execute_trade.call_count, 2)   # QQQ +3 only

        self.broker.orders, self.broker.positions = [], {"SPY": 20, "QQQ": 8}   # filled
        self.call(25, 8)
        last = self.upm._trade_manager.execute_trade.call_args.kwargs
        self.assertEqual((last["ticker"], last["order_qty"]), ("SPY", 5))
        self.assertEqual(self.upm._trade_manager.execute_trade.call_count, 3)

    def test_partial_fill_then_cancel_blocks_everything(self):
        self.call(20, 5)
        self.broker.positions = {"SPY": 16, "QQQ": 5}       # 6 of 10 filled, rest cancelled
        result = self.call(20, 9)
        self.assertEqual(result, {"SPY": False, "QQQ": False})
        self.assertEqual(self.upm._reconciler.last_result.mismatches,
                         [{"ticker": "SPY", "strategy_qty": 20.0, "broker_qty": 16.0}])
        self.assertEqual(self.upm._trade_manager.execute_trade.call_count, 1)

    def test_broker_down_blocks_everything(self):
        def down():
            raise ConnectionError("gateway restarting")
        self.upm.attach_reconciler(down)
        self.assertEqual(self.call(30, 30), {"SPY": False, "QQQ": False})
        self.upm._trade_manager.execute_trade.assert_not_called()


class AccountFilterTest(unittest.TestCase):

    POSITIONS = [
        {"account": "U111", "symbol": "SPY", "secType": "STK", "localSymbol": "SPY", "position": 10},
        {"account": "U222", "symbol": "SPY", "secType": "STK", "localSymbol": "SPY", "position": 90},
    ]

    def test_named_account_only(self):
        snap = IBKRSnapshotProvider(FakeIB(self.POSITIONS, []), account="U111")()
        self.assertEqual(snap.positions, {"SPY": 10.0})

    def test_account_is_required_when_several_accounts_are_visible(self):
        try:
            snap = IBKRSnapshotProvider(FakeIB(self.POSITIONS, []))()
        except Exception:
            return
        self.assertFalse(snap.complete)


@unittest.skipUnless(os.getenv("IBKR_LIVE_SMOKE") == "1", "set IBKR_LIVE_SMOKE=1 to read the real Gateway")
class LiveGatewayReadOnlySmokeTest(unittest.TestCase):
    """Reads positions + open orders from the configured Gateway (IBKR_HOST / IBKR_PORT)."""

    BLOCKED = ("placeOrder", "cancelOrder", "reqGlobalCancel", "exerciseOptions", "reqIds")

    def test_snapshot_is_complete_and_nothing_is_sent(self):
        import threading
        from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient

        host = os.getenv("IBKR_HOST", "127.0.0.1")
        port = int(os.getenv("IBKR_PORT", "4001"))
        client = IBTWSClient(host, port, int(os.getenv("IBKR_SMOKE_CLIENT_ID", "93")))

        def refuse(name):
            def _blocked(*a, **k):
                raise AssertionError(f"{name} called during a read-only smoke test")
            return _blocked
        for name in self.BLOCKED:
            setattr(client, name, refuse(name))

        client.connect(host, port, client.client_id)
        threading.Thread(target=client.run, daemon=True).start()
        try:
            self.assertTrue(client.connection_event.wait(15), f"no handshake with {host}:{port}")
            snap = IBKRSnapshotProvider(client, account=os.getenv("IBKR_ACCOUNT") or None, timeout=15)()
            self.assertTrue(snap.complete)
            print(f"\nlive snapshot: {len(snap.positions)} position(s), {len(snap.open_orders)} open order(s)")
        finally:
            client.disconnect()


if __name__ == "__main__":
    unittest.main()
