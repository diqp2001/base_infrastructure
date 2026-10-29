"""P.06.01 — the paper / live stack wiring (fake connected client, in-memory SQLite; no IBKR, no orders)."""

from types import SimpleNamespace

import pytest

from src.application.services.misbuffet.live.live_stack import LiveStackConfig, build_live_stack
from src.domain.entities.finance.order.pre_trade_risk import RiskLimits
from src.domain.entities.finance.order.trading_control import ControlMode
from tests.misbuffet.sqlite_portfolio import SqlitePortfolio


class FakeClient:
    def __init__(self, accounts=("DUR314497",)):
        self.accounts = list(accounts)
        self.order_listeners, self.connection_listeners = [], []
        self.market_data, self.market_data_type, self.market_data_errors, self.tick_by_tick = {}, {}, {}, {}
        self.types, self.requests = [], []

    def is_connected(self):
        return True

    def get_managed_accounts(self):
        return self.accounts

    def request_market_data_type(self, t):
        self.types.append(t)

    def request_market_data(self, req_id, contract, snapshot=False):
        self.requests.append((req_id, contract.symbol))


class FakeBroker:
    def __init__(self, client):
        self.ib_connection, self.risk_gate = client, None

    def attach_risk_gate(self, gate):
        self.risk_gate = gate


@pytest.fixture
def book():
    b = SqlitePortfolio(shares=("F",), live=True)
    yield b
    b.close()


def config(**kw):
    return LiveStackConfig(account="DUR314497", strategy="P06", limits=RiskLimits(max_order_quantity=5), **kw)


def test_the_stack_wires_ledger_reconciler_recovery_and_gate(book, monkeypatch):
    monkeypatch.delenv("IBKR_ACCOUNT_MODE", raising=False)                # default: paper
    client, broker = FakeClient(), None
    broker = FakeBroker(client)
    stack = build_live_stack(broker, book.upm, book.factory, config(allow_delayed_prices=True))
    assert broker.risk_gate is stack.gate and stack.gate.account == "DUR314497"
    assert book.upm._order_ledger is stack.ledger and book.upm._recovery is stack.recovery
    assert book.upm._reconciler is stack.reconciler and book.tm.ledger is stack.ledger
    assert stack.ledger.enqueue in client.order_listeners and stack.recovery.invalidate in client.connection_listeners
    assert client.types == [4] and stack.prices.allow_delayed
    stack.subscribe(["F"])
    assert client.requests[0][1] == "F"
    stack.controls.kill("test", "pytest")
    status = stack.status()
    assert status["trading_control"] == ControlMode.DISABLED.value and status["mode"] == "paper"
    assert status["trading_allowed"] is False and status["quotes"][0]["instrument"] == "STK:F"


def test_the_stack_refuses_a_live_account_in_paper_mode_and_delayed_prices_on_live(book, monkeypatch):
    monkeypatch.delenv("IBKR_ACCOUNT_MODE", raising=False)
    with pytest.raises(PermissionError, match="live account"):
        build_live_stack(FakeBroker(FakeClient(["U11494855"])), book.upm, book.factory,
                         LiveStackConfig(account="U11494855", strategy="x", limits=RiskLimits()))
    with pytest.raises(PermissionError, match="not managed"):
        build_live_stack(FakeBroker(FakeClient(["DU1"])), book.upm, book.factory, config())
    monkeypatch.setenv("IBKR_ACCOUNT_MODE", "live")
    monkeypatch.setenv("IBKR_ALLOW_LIVE", "yes")
    for option in ("allow_delayed_prices", "paper_bar_prices"):
        with pytest.raises(PermissionError, match="PAPER account only"):
            build_live_stack(FakeBroker(FakeClient(["U11494855"])), book.upm, book.factory,
                             LiveStackConfig(account="U11494855", strategy="x", limits=RiskLimits(),
                                             **{option: True}))


def test_paper_bar_prices_use_the_last_trade_bar_provider(book, monkeypatch):
    from src.application.services.misbuffet.brokers.trading_controls import LastTradeBarPriceProvider
    monkeypatch.delenv("IBKR_ACCOUNT_MODE", raising=False)
    stack = build_live_stack(FakeBroker(FakeClient()), book.upm, book.factory, config(paper_bar_prices=True))
    assert isinstance(stack.prices, LastTradeBarPriceProvider) and stack.gate.price_provider is stack.prices


def test_the_stack_needs_a_connected_broker(book):
    broker = FakeBroker(SimpleNamespace(is_connected=lambda: False))
    with pytest.raises(ValueError, match="not connected"):
        build_live_stack(broker, book.upm, book.factory, config())


def test_shutdown_applies_events_unsubscribes_and_cancels_only_when_asked(book, monkeypatch):
    from unittest.mock import Mock
    monkeypatch.delenv("IBKR_ACCOUNT_MODE", raising=False)
    client = FakeClient()
    client.cancel_market_data, client.cancel_order = Mock(), Mock()
    order_id = _order_row(book)                                # before the ledger: the backtest path books it
    stack = build_live_stack(FakeBroker(client), book.upm, book.factory, config())
    stack.subscribe(["F"])
    bo = stack.ledger.record_intent(order_id, "F", "BUY", 1, 1, 1)
    stack.ledger.mark_submitted(bo, 77, 7)
    left = stack.shutdown("end of day")
    assert left["open_orders"][0]["broker_order_id"] == 77 and left["cancel_requested"] == []
    assert stack.streaming.subscriptions() == [] and client.cancel_order.call_count == 0
    left = stack.shutdown("kill", cancel_working=True)
    client.cancel_order.assert_called_once_with(77)
    assert left["cancel_requested"] == [bo.order_id] and left["open_orders"][0]["cancel_requested"]


def _order_row(book):
    from src.infrastructure.models.finance.order.order import OrderModel
    book.trade("F", 1, 10.0)                                   # backtest path creates holding, account and order
    return book.session.query(OrderModel).order_by(OrderModel.id.desc()).first().id


# ---------------------------------------------------------------- P.04.07: reconnect in the middle of a session
class _Conn:
    def __init__(self, alive=True):
        self.alive = alive

    def is_connected(self):
        return self.alive


class _Broker:
    def __init__(self, alive=True, reconnect_ok=True):
        self.ib_connection = _Conn(alive)
        self.reconnect_ok = reconnect_ok
        self.connects = 0

    def disconnect(self):
        self.ib_connection = None

    def connect(self):
        self.connects += 1
        self.ib_connection = _Conn(self.reconnect_ok)       # a reconnect makes a NEW client
        return self.reconnect_ok


def _stack_on(broker):
    from types import SimpleNamespace
    from unittest.mock import Mock
    return SimpleNamespace(client=broker.ib_connection, ledger=Mock())


def test_the_guard_keeps_a_healthy_stack():
    from src.application.services.misbuffet.live.live_stack import LiveConnectionGuard
    broker = _Broker()
    stack = _stack_on(broker)
    guard = LiveConnectionGuard(broker, rebuild=lambda: (_ for _ in ()).throw(AssertionError("no rebuild")))
    assert guard.check(stack) is stack and broker.connects == 0


def test_a_dropped_order_connection_is_reconnected_and_the_stack_rebuilt_on_the_new_client():
    from src.application.services.misbuffet.live.live_stack import LiveConnectionGuard
    broker = _Broker()
    stack = _stack_on(broker)
    broker.ib_connection.alive = False                      # TWS restarted: the socket is gone
    rebuilt = []
    guard = LiveConnectionGuard(broker, rebuild=lambda: rebuilt.append(_stack_on(broker)) or rebuilt[-1])
    new = guard.check(stack)
    stack.ledger.drain.assert_called_once()                 # events received before the drop applied first
    assert broker.connects == 1 and new is rebuilt[0] and new.client is broker.ib_connection
    assert guard.check(new) is new and guard.reconnects == 1


def test_a_failed_reconnect_means_no_order_this_step_and_a_retry_next_step():
    from src.application.services.misbuffet.live.live_stack import LiveConnectionGuard
    broker = _Broker(reconnect_ok=False)
    stack = _stack_on(broker)
    broker.ib_connection.alive = False
    guard = LiveConnectionGuard(broker, rebuild=lambda: _stack_on(broker))
    assert guard.check(stack) is None and guard.failures == 1
    broker.reconnect_ok = True
    assert guard.check(None) is not None and broker.connects == 2


def test_the_data_connection_is_reconnected_in_place():
    from src.application.services.misbuffet.live.live_stack import LiveConnectionGuard
    broker, data = _Broker(), _Broker()
    stack = _stack_on(broker)
    data.ib_connection.alive = False
    guard = LiveConnectionGuard(broker, rebuild=lambda: _stack_on(broker), data_broker=data)
    assert guard.check(stack) is stack                      # the order path is untouched
    assert data.connects == 1 and data.ib_connection.is_connected()


def test_tws_connectivity_codes_reach_recovery_and_streaming():
    from unittest.mock import Mock
    from src.application.services.misbuffet.algorithm.startup_recovery import StartupRecovery
    from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient
    from src.application.services.misbuffet.data.streaming_market_data import StreamingMarketDataService
    client = IBTWSClient("127.0.0.1", 7497, 99)
    client.request_market_data = Mock()
    recovery = StartupRecovery(client, Mock(), Mock())
    streaming = StreamingMarketDataService(client)
    streaming.subscribe("STK:JPM", object())
    recovery._valid = True
    client.error(-1, 1100, "Connectivity between IBKR and Trader Workstation has been lost.")
    assert recovery._valid is False and streaming.connected is False
    recovery._valid = True
    client.error(-1, 1102, "Connectivity restored - data maintained.")
    assert recovery._valid is False and streaming.connected and client.request_market_data.call_count == 1
    client.error(-1, 1101, "Connectivity restored - data lost.")
    assert client.request_market_data.call_count == 2          # 1101: market-data lines requested again
