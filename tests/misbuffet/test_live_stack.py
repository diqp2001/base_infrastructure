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
