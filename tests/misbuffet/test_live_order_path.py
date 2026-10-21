"""
Checklist section 1 — the real-money order path, end to end, with fakes only.

Nothing here connects to IBKR or sends an order: brokers and TWS clients are fakes or Mocks,
and IBTWSClient.placeOrder is patched where a real client object is used.

Tests marked ``expectedFailure`` describe the behaviour the live path needs and fail today
because of a known bug (named in the docstring). When the bug is fixed the test reports
"unexpected success": remove the decorator then.
"""

import logging
import unittest
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock, Mock, patch

from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient
from src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker
from src.application.services.misbuffet.common import Symbol
from src.application.services.misbuffet.common.enums import OrderDirection, OrderStatus
from src.application.services.misbuffet.common.orders import LimitOrder, MarketOrder
from src.application.services.misbuffet.engine.enums import ComponentState, EngineMode
from src.application.services.misbuffet.engine.transaction_handlers import (
    BacktestingTransactionHandler, BrokerageTransactionHandler,
)

logging.getLogger("BrokerageTransactionHandler").setLevel(logging.CRITICAL)
logging.getLogger("InteractiveBrokersBroker").setLevel(logging.CRITICAL)


def market(ticker, qty):
    return MarketOrder(symbol=Symbol.create_equity(ticker), quantity=qty,
                       direction=OrderDirection.BUY if qty > 0 else OrderDirection.SELL)


class FakeBrokerage:
    """IBrokerage stand-in: records every call, never talks to anything."""

    def __init__(self, accept=True, connected=True, connect_ok=True):
        self.accept, self.connected, self.connect_ok = accept, connected, connect_ok
        self.placed, self.cancelled, self.disconnected = [], [], False

    def is_connected(self):
        return self.connected

    def connect(self):
        self.connected = self.connect_ok
        return self.connect_ok

    def disconnect(self):
        self.disconnected = True

    def place_order(self, order):
        self.placed.append(order)
        return self.accept

    def cancel_order(self, order):
        self.cancelled.append(order)
        return True

    def update_order(self, order):
        return True


class BrokerageTransactionHandlerTest(unittest.TestCase):

    def make(self, brokerage):
        handler = BrokerageTransactionHandler()
        self.algorithm = Mock()
        with patch.object(BrokerageTransactionHandler, "_start_monitoring"):   # no background thread
            handler.initialize(self.algorithm, brokerage)
        return handler

    def test_order_is_sent_once_and_marked_submitted(self):
        broker = FakeBrokerage()
        handler = self.make(broker)
        order = market("SPY", 10)
        self.assertTrue(handler.process_order(order))
        self.assertEqual(broker.placed, [order])
        self.assertEqual(order.status, OrderStatus.SUBMITTED)

    def test_broker_rejection_is_recorded_and_reported(self):
        broker = FakeBrokerage(accept=False)
        handler = self.make(broker)
        order = market("SPY", 10)
        self.assertFalse(handler.process_order(order))
        self.assertEqual(order.status, OrderStatus.INVALID)
        self.assertEqual(handler.get_metrics()["rejected_orders"], 1)
        event = self.algorithm.on_order_event.call_args.args[0]
        self.assertEqual(event.status, OrderStatus.INVALID)

    def test_zero_quantity_never_reaches_the_broker(self):
        broker = FakeBrokerage()
        handler = self.make(broker)
        self.assertFalse(handler.process_order(market("SPY", 0)))
        self.assertEqual(broker.placed, [])

    def test_uninitialized_handler_sends_nothing(self):
        broker = FakeBrokerage()
        handler = BrokerageTransactionHandler()
        handler._brokerage = broker
        self.assertFalse(handler.process_order(market("SPY", 1)))
        self.assertEqual(broker.placed, [])

    def test_initialize_connects_and_fails_hard_when_it_cannot(self):
        broker = FakeBrokerage(connected=False)
        self.make(broker)
        self.assertTrue(broker.connected)
        handler = BrokerageTransactionHandler()
        with patch.object(BrokerageTransactionHandler, "_start_monitoring"), self.assertRaises(RuntimeError):
            handler.initialize(Mock(), FakeBrokerage(connected=False, connect_ok=False))
        self.assertEqual(handler._state, ComponentState.ERROR)

    def test_fill_event_updates_order_and_notifies_algorithm(self):
        handler = self.make(FakeBrokerage())
        order = market("SPY", 10)
        handler.process_order(order)
        fill = SimpleNamespace(order_id=order.id, status=OrderStatus.FILLED, fill_quantity=10, fill_price=500.0)
        handler.handle_fills([fill])
        self.assertEqual(order.status, OrderStatus.FILLED)
        self.assertEqual(handler.get_metrics()["filled_orders"], 1)
        self.algorithm.on_order_event.assert_called_with(fill)

    def test_dispose_disconnects(self):
        broker = FakeBrokerage()
        handler = self.make(broker)
        handler.dispose()
        self.assertTrue(broker.disconnected)

    def test_submitted_order_is_open(self):
        handler = self.make(FakeBrokerage())
        order = market("SPY", 10)
        handler.process_order(order)
        self.assertEqual(handler.get_open_orders(), [order])

    def test_cancel_reaches_the_broker(self):
        broker = FakeBrokerage()
        handler = self.make(broker)
        order = market("SPY", 10)
        handler.process_order(order)
        self.assertTrue(handler.cancel_order(order.id))
        self.assertEqual(broker.cancelled, [order])

    def test_partial_fill_event_can_be_created(self):
        handler = self.make(FakeBrokerage())
        order = market("SPY", 10)
        event = handler._create_fill_event(order, Decimal("500"), 4)
        self.assertEqual(event.status, OrderStatus.PARTIAL_FILLED)

    def test_status_updates_flow_back_from_the_broker(self):
        """A broker order event (fill) reaches the order and the algorithm."""
        broker = FakeBrokerage()
        broker.order_event_handlers = []
        handler = self.make(broker)
        order = market("SPY", 10)
        handler.process_order(order)
        self.assertEqual(len(broker.order_event_handlers), 1)
        fill = SimpleNamespace(order_id=order.id, status=OrderStatus.FILLED, fill_quantity=10, fill_price=500.0)
        broker.order_event_handlers[0](fill)
        self.assertEqual(order.status, OrderStatus.FILLED)
        self.algorithm.on_order_event.assert_called_with(fill)


class FakeTWS:
    """IBTWSClient stand-in for InteractiveBrokersBroker: builds real ibapi objects, sends nothing."""

    def __init__(self):
        self.real = IBTWSClient("127.0.0.1", 1, 1)
        self.contracts, self.orders = [], []
        self.order_status = {}
        self._next = 100

    def is_connected(self):
        return True

    def create_contract(self, *args, **kwargs):
        contract = self.real.create_contract(*args, **kwargs)
        self.contracts.append(contract)
        return contract

    def create_market_order(self, action, qty):
        return self.real.create_market_order(action, qty)

    def create_limit_order(self, action, qty, price):
        return self.real.create_limit_order(action, qty, price)

    def place_order(self, contract, order):
        self.orders.append((contract, order))
        self._next += 1
        return self._next


class InteractiveBrokersBrokerOrderTest(unittest.TestCase):

    def setUp(self):
        self.broker = InteractiveBrokersBroker({"host": "127.0.0.1", "port": 1, "client_id": 1})
        self.tws = FakeTWS()
        self.broker.ib_connection = self.tws

    def test_buy_and_sell_map_to_action_and_absolute_quantity(self):
        order = market("SPY", -5)
        self.assertTrue(self.broker._place_order_impl(order))
        _, ib_order = self.tws.orders[0]
        self.assertEqual((ib_order.action, ib_order.totalQuantity, ib_order.orderType), ("SELL", 5, "MKT"))

    def test_limit_order_carries_the_limit_price(self):
        order = LimitOrder(symbol=Symbol.create_equity("SPY"), quantity=3, limit_price=501.25)
        self.assertTrue(self.broker._place_order_impl(order))
        _, ib_order = self.tws.orders[0]
        self.assertEqual((ib_order.action, ib_order.orderType, ib_order.lmtPrice), ("BUY", "LMT", 501.25))

    def test_pending_order_is_tracked_by_tws_id(self):
        order = market("SPY", 1)
        self.broker._place_order_impl(order)
        self.assertIs(self.broker.pending_orders[101], order)

    def test_contradicting_sign_and_direction_is_refused(self):
        order = market("SPY", -5)
        order.direction = OrderDirection.BUY
        self.assertFalse(self.broker._place_order_impl(order))
        self.assertEqual(self.tws.orders, [])

    def test_repeated_status_is_reported_once(self):
        order = market("SPY", 10)
        self.broker.pending_orders[9] = order
        self.tws.order_status[9] = {"status": "Submitted", "filled": 0, "remaining": 10, "avgFillPrice": 0}
        events = []
        self.broker.order_event_handlers.append(events.append)
        self.broker._process_order_updates()
        self.broker._process_order_updates()
        self.assertEqual([e.status for e in events], [OrderStatus.SUBMITTED])

    def test_zero_quantity_is_refused_before_tws(self):
        self.broker.status = self.broker.status.__class__.CONNECTED
        self.assertFalse(self.broker.place_order(market("SPY", 0)))
        self.assertEqual(self.tws.orders, [])

    def test_place_order_works_with_framework_orders(self):
        self.broker.status = self.broker.status.__class__.CONNECTED
        self.assertTrue(self.broker.place_order(market("SPY", 10)))
        self.assertEqual(len(self.tws.orders), 1)

    def test_stock_order_uses_a_stock_contract(self):
        order = market("SPY", 10)
        self.broker._place_order_impl(order)
        contract, _ = self.tws.orders[0]
        self.assertEqual((contract.secType, contract.symbol, contract.exchange, contract.currency),
                         ("STK", "SPY", "SMART", "USD"))

    def test_option_order_uses_the_option_contract(self):
        order = market("SPY   281215C00775000", -1)
        self.broker._place_order_impl(order)
        contract, ib_order = self.tws.orders[0]
        self.assertEqual((contract.secType, contract.symbol, contract.localSymbol, contract.right, contract.strike,
                          contract.lastTradeDateOrContractMonth, contract.multiplier, ib_order.action),
                         ("OPT", "SPY", "SPY   281215C00775000", "C", 775.0, "20281215", "100", "SELL"))

    def test_filled_status_becomes_an_order_event(self):
        order = market("SPY", 10)
        self.broker.pending_orders[7] = order
        self.tws.order_status[7] = {"status": "Filled", "filled": 10, "remaining": 0, "avgFillPrice": 500.5}
        events = []
        self.broker.order_event_handlers.append(events.append)
        self.broker._process_order_updates()
        self.assertEqual([(e.status, e.fill_quantity, e.fill_price) for e in events],
                         [(OrderStatus.FILLED, 10, Decimal("500.5"))])
        self.assertNotIn(7, self.broker.pending_orders)

    def test_partial_fill_is_reported(self):
        order = market("SPY", 10)
        self.broker.pending_orders[8] = order
        self.tws.order_status[8] = {"status": "Submitted", "filled": 4, "remaining": 6, "avgFillPrice": 500.0}
        events = []
        self.broker.order_event_handlers.append(events.append)
        self.broker._process_order_updates()
        self.assertEqual([(e.status, e.fill_quantity) for e in events], [(OrderStatus.PARTIAL_FILLED, 4)])


class TWSOrderIdTest(unittest.TestCase):

    def setUp(self):
        self.client = IBTWSClient("127.0.0.1", 1, 1)
        self.client.is_connected = lambda: True
        self.client.managedAccounts("DU1234567")                    # paper login, matches the default mode
        env = patch.dict("os.environ", {"IBKR_ACCOUNT_MODE": "paper"})
        env.start()
        self.addCleanup(env.stop)

    def test_ids_increase_and_follow_next_valid_id_after_reconnect(self):
        with patch.object(self.client, "placeOrder") as place:
            self.client.nextValidId(10)
            ids = [self.client.place_order(Mock(symbol="SPY"), Mock(action="BUY", totalQuantity=1)) for _ in range(2)]
            self.client.nextValidId(25)                     # reconnect: TWS hands out its next free id
            ids.append(self.client.place_order(Mock(symbol="SPY"), Mock(action="BUY", totalQuantity=1)))
        self.assertEqual(ids, [10, 11, 25])
        self.assertEqual([c.args[0] for c in place.call_args_list], ids)

    def test_disconnected_client_refuses_to_place(self):
        self.client.is_connected = lambda: False
        with patch.object(self.client, "placeOrder") as place, self.assertRaises(ConnectionError):
            self.client.place_order(Mock(), Mock())
        place.assert_not_called()

    def test_ids_never_go_backwards(self):
        with patch.object(self.client, "placeOrder"):
            self.client.nextValidId(10)
            self.client.place_order(Mock(symbol="SPY"), Mock(action="BUY", totalQuantity=1))
            self.client.nextValidId(5)
            self.assertEqual(self.client.place_order(Mock(symbol="SPY"), Mock(action="BUY", totalQuantity=1)), 11)


class ConnectedAccountGuardTest(unittest.TestCase):
    """BI-005: TWS sends nothing unless the logged-in account matches IBKR_ACCOUNT_MODE (paper DU… vs live U…)."""

    def client(self, accounts, mode="paper"):
        client = IBTWSClient("127.0.0.1", 1, 1)
        client.is_connected = lambda: True
        if accounts is not None:
            client.managedAccounts(accounts)
        env = {"IBKR_ACCOUNT_MODE": mode, "IBKR_ALLOW_LIVE": "yes" if mode == "live" else ""}
        patcher = patch.dict("os.environ", env)
        patcher.start()
        self.addCleanup(patcher.stop)
        return client

    def place(self, client, account=""):
        with patch.object(client, "placeOrder") as place:
            try:
                client.place_order(Mock(symbol="SPY"), Mock(action="BUY", totalQuantity=1, account=account))
            finally:
                self.sent = place.call_count
        return self.sent

    def refused(self, client, account=""):
        from src.application.services.misbuffet.brokers.ibkr.ibkr_settings import AccountModeMismatch
        with self.assertRaises(AccountModeMismatch):
            self.place(client, account)
        self.assertEqual(self.sent, 0)

    def test_paper_mode_sends_to_a_paper_account(self):
        self.assertEqual(self.place(self.client("DU1234567")), 1)

    def test_paper_mode_refuses_a_live_login(self):
        self.refused(self.client("U1234567"))

    def test_live_mode_refuses_a_paper_login(self):
        self.refused(self.client("DU1234567", mode="live"))

    def test_live_mode_sends_to_a_live_account(self):
        self.assertEqual(self.place(self.client("U1234567", mode="live")), 1)

    def test_unknown_account_is_refused(self):
        self.refused(self.client(None))

    def test_order_account_must_be_managed_and_of_the_mode(self):
        client = self.client("DU1234567,U7654321")
        self.assertEqual(self.place(client, account="DU1234567"), 1)
        self.refused(client, account="U7654321")
        self.refused(client, account="DU0000000")
        self.refused(client)                                        # default account is ambiguous: refused

    def test_refusal_does_not_consume_an_order_id(self):
        client = self.client("U1234567")
        client.nextValidId(10)
        self.refused(client)
        self.assertEqual(client.next_order_id, 10)

    def test_broker_reports_a_refused_order_as_not_placed(self):
        broker = InteractiveBrokersBroker.__new__(InteractiveBrokersBroker)
        broker.logger = logging.getLogger("InteractiveBrokersBroker")
        broker.pending_orders = {}
        broker.ib_connection = self.client("U1234567")
        with patch.object(broker.ib_connection, "placeOrder") as place:
            self.assertFalse(broker._place_order_impl(market("SPY", 10)))
        place.assert_not_called()


class LiveModeWiringTest(unittest.TestCase):

    def test_launcher_picks_the_brokerage_handler_in_live_mode(self):
        from src.application.services.misbuffet.launcher.handlers import HandlerFactory
        factory = HandlerFactory.__new__(HandlerFactory)       # __init__ is broken, see below
        self.assertIsInstance(factory._create_transaction_handler(SimpleNamespace(live_mode=True)),
                              BrokerageTransactionHandler)
        self.assertIsInstance(factory._create_transaction_handler(SimpleNamespace(live_mode=False)),
                              BacktestingTransactionHandler)

    def test_launcher_handler_factory_can_be_built(self):
        from src.application.services.misbuffet.launcher.handlers import HandlerFactory
        HandlerFactory()

    def test_lean_engine_creates_the_handler_named_by_the_job(self):
        from src.application.services.misbuffet.engine.lean_engine import LeanEngine
        engine = LeanEngine.__new__(LeanEngine)
        engine._logger = logging.getLogger("test")
        engine._job = SimpleNamespace(transaction_handler="BrokerageTransactionHandler")
        self.assertIsInstance(engine._create_transaction_handler(), BrokerageTransactionHandler)

    def test_live_job_defaults_to_the_brokerage_handler(self):
        from src.application.services.misbuffet.engine.engine_node_packet import LiveNodePacket
        packet = LiveNodePacket()
        self.assertEqual(packet.engine_mode, EngineMode.LIVE_TRADING)
        self.assertEqual(packet.transaction_handler, "BrokerageTransactionHandler")

    def test_misbuffet_engine_wires_live_trading(self):
        from src.application.services.misbuffet.engine.misbuffet_engine import MisbuffetEngine
        engine = MisbuffetEngine.__new__(MisbuffetEngine)
        engine.logger = logging.getLogger("test")
        engine._transaction_handler = BacktestingTransactionHandler()
        engine.algorithm = algorithm = self.algorithm()
        broker = FakeBrokerage()
        with patch.object(BrokerageTransactionHandler, "_start_monitoring"):
            engine._wire_live_trading(SimpleNamespace(live_mode=True, brokerage=broker))
        self.assertIsInstance(engine.transaction_handler, BrokerageTransactionHandler)
        self.assertIs(engine.transaction_handler._brokerage, broker)
        self.assertTrue(algorithm.live_mode)
        self.assertIs(algorithm.transaction_handler, engine.transaction_handler)

    def test_misbuffet_engine_live_without_brokerage_fails_hard(self):
        from src.application.services.misbuffet.engine.misbuffet_engine import MisbuffetEngine
        engine = MisbuffetEngine.__new__(MisbuffetEngine)
        engine.logger = logging.getLogger("test")
        engine._transaction_handler = None
        engine.algorithm = self.algorithm()
        with self.assertRaises(RuntimeError):
            engine._wire_live_trading(SimpleNamespace(live_mode=True))
        engine._wire_live_trading(SimpleNamespace(live_mode=False))       # backtest: untouched
        self.assertFalse(engine.algorithm.live_mode)

    @staticmethod
    def algorithm():
        from src.application.services.misbuffet.algorithm.base import QCAlgorithm
        return QCAlgorithm()

    def test_algorithm_can_be_switched_to_live_mode(self):
        algorithm = self.algorithm()
        self.assertFalse(algorithm.live_mode)
        algorithm.set_live_mode(True)
        self.assertTrue(algorithm.live_mode)

    def test_live_market_order_is_handed_to_the_transaction_handler(self):
        algorithm = self.algorithm()
        handler = Mock()
        handler.process_order.return_value = True
        algorithm.set_live_mode(True)
        algorithm.set_transaction_handler(handler)
        ticket = algorithm.market_order("SPY", 10)
        self.assertIsNotNone(ticket)
        sent, = [c.args[0] for c in handler.process_order.call_args_list]
        self.assertEqual((sent.symbol.value, sent.quantity), ("SPY", 10))

    def test_rejected_live_order_returns_no_ticket(self):
        algorithm = self.algorithm()
        algorithm.set_live_mode(True)
        algorithm.set_transaction_handler(Mock(process_order=Mock(return_value=False)))
        self.assertIsNone(algorithm.market_order("SPY", 10))

    def test_live_order_without_handler_is_refused(self):
        algorithm = self.algorithm()
        algorithm.set_live_mode(True)
        with self.assertRaises(RuntimeError):
            algorithm.market_order("SPY", 10)

    def test_backtest_market_order_reaches_no_handler(self):
        algorithm = self.algorithm()
        handler = Mock()
        algorithm.set_transaction_handler(handler)
        self.assertIsNotNone(algorithm.market_order("SPY", 10))
        handler.process_order.assert_not_called()

if __name__ == "__main__":
    unittest.main()
