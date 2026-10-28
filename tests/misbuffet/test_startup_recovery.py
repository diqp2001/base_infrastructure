"""
P.04 — start-up / reconnect recovery (in-memory SQLite, fake read-only IBKR client; no connection, no orders).

The fake client answers reqAllOpenOrders / reqExecutions from scripted rows; executions and commissions reach the
OrderLedger through order_listeners, as IBTWSClient does.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.application.services.misbuffet.algorithm.order_ledger import OrderLedger
from src.application.services.misbuffet.algorithm.position_reconciler import BrokerSnapshot, PositionReconciler
from src.application.services.misbuffet.algorithm.startup_recovery import StartupRecovery
from src.domain.entities.finance.order.broker_order import SubmissionState, order_id_from_ref, order_ref
from src.domain.entities.finance.order.discrepancy import Discrepancy, DiscrepancyKind
from tests.misbuffet.sqlite_portfolio import SqlitePortfolio

NOW = datetime(2026, 10, 29, 14, 0, tzinfo=timezone.utc)


class FakeIB:
    def __init__(self):
        self.connected = True
        self.order_listeners, self.connection_listeners = [], []
        self.open_orders, self.executions, self.positions = [], [], {}
        self.orders_complete = self.executions_complete = True
        self.open_orders_snapshot = []

    def is_connected(self):
        return self.connected

    def request_open_orders_snapshot(self, timeout=10.0):
        self.open_orders_snapshot = [dict(r) for r in self.open_orders]
        return self.orders_complete

    def request_executions_snapshot(self, timeout=10.0):
        for e in self.executions:                         # IBKR replays the day's executions (+ commissions)
            for listener in self.order_listeners:
                listener(dict(e))
        return self.executions_complete

    def close(self):
        self.connected = False
        for listener in self.connection_listeners:
            listener()


def execution(exec_id, internal_id, shares, price=100.0, side="BOT", broker_id=None, symbol="AAPL"):
    return {"kind": "execution", "exec_id": exec_id, "order_id": broker_id or 0, "perm_id": 0,
            "order_ref": order_ref(internal_id) if internal_id else "", "shares": shares, "price": price,
            "side": side, "time": "20261029  09:45:00", "symbol": symbol}


def working(internal_id, broker_id=600, perm=7000, symbol="AAPL", qty=10, status="Submitted", ref=True):
    return {"orderId": broker_id, "permId": perm, "clientId": 7, "symbol": symbol, "localSymbol": symbol,
            "secType": "STK", "action": "BUY", "totalQuantity": qty, "status": status, "remaining": qty,
            "orderRef": f"set_holdings_{symbol}|{order_ref(internal_id)}" if ref else ""}


@pytest.fixture
def env():
    book = SqlitePortfolio(cash=100_000.0, shares=("AAPL", "MSFT"))
    ib = FakeIB()
    ledger = OrderLedger(book.factory, clock=lambda: NOW)
    ledger.attach(ib)
    book.tm.attach_ledger(ledger, submission_probe=lambda: env.probe)
    env = SimpleNamespace(book=book, ib=ib, ledger=ledger, probe=None,
                          repo=book.factory.trading_discrepancy_local_repo)
    reconciler = PositionReconciler(
        strategy_qty=book.qty, managed_tickers=lambda: {"AAPL", "MSFT"},
        snapshot_provider=lambda: BrokerSnapshot(positions=dict(ib.positions), open_orders=[],
                                                 taken_at=datetime.now(timezone.utc)))
    env.recovery = StartupRecovery(ib, ledger, env.repo, reconciler=reconciler, clock=lambda: NOW)
    yield env
    book.close()


def place(env, outcome="sent", broker_id=600, qty=10, ticker="AAPL"):
    """One live order through TradeManager; returns its BrokerOrder."""
    def submit(t, q, tag=""):
        env.tags.append(tag)
        env.probe = SimpleNamespace(submission_outcome=outcome, broker_order_id=broker_id, broker_client_id=7)
        return SimpleNamespace(order_id="QC") if outcome == "sent" else None
    env.tags = getattr(env, "tags", [])
    env.book.trade(ticker, qty, 100.0, submit=submit)
    return env.ledger.orders.get_all()[-1]


def kinds(report):
    return sorted(d.kind.value for d in report.new_discrepancies)


def test_the_order_reference_travels_with_the_order(env):
    bo = place(env)
    assert env.tags[-1].endswith(order_ref(bo.order_id)) and order_id_from_ref(env.tags[-1]) == bo.order_id


def test_a_clean_start_allows_trading(env):
    report = env.recovery.run()
    assert report.ok and report.lists_complete and env.recovery.trading_allowed() and report.new_discrepancies == []


def test_fills_missed_while_down_are_booked_once_and_the_order_closed(env):
    bo = place(env)
    env.ib.executions = [execution("E1", bo.order_id, 4), execution("E2", bo.order_id, 6),
                         {"kind": "commission", "exec_id": "E2", "commission": 1.0, "currency": "USD"}]
    env.ib.positions = {"AAPL": 10}
    report = env.recovery.run()
    assert report.ok, report.summary()
    assert report.orders_closed == {bo.order_id: "FILLED"}
    assert (env.book.qty("AAPL"), env.book.cash()) == (10, pytest.approx(100_000.0 - 1_000.0 - 1.0))
    report = env.recovery.run()                                          # replayed again: nothing booked twice
    assert env.book.qty("AAPL") == 10 and env.ledger.duplicates >= 2 and report.ok
    assert [d.kind for d in env.repo.get_all()] == [DiscrepancyKind.ORDER_CLOSED_ON_RECOVERY]
    assert not env.repo.get_open()                                       # recorded, resolved, not blocking


def test_an_unknown_order_found_working_at_the_broker_becomes_submitted(env):
    bo = place(env, outcome="unknown", broker_id=None)
    assert bo.submission_state is SubmissionState.UNKNOWN
    env.ib.open_orders = [working(bo.order_id, broker_id=612, perm=7612)]
    report = env.recovery.run()
    bo = env.ledger.orders.get_by_order_id(bo.order_id)
    assert (bo.submission_state, bo.broker_order_id, bo.perm_id) == (SubmissionState.SUBMITTED, 612, 7612)
    assert report.orders_kept_open == [bo.order_id] and report.ok


@pytest.mark.parametrize("state", ["unknown", "intent"])
def test_an_order_the_broker_never_had_is_closed_as_rejected_and_recorded(env, state):
    if state == "unknown":
        bo = place(env, outcome="unknown", broker_id=None)
    else:
        bo = env.ledger.record_intent(*_intent(env))                     # crash right after the intent was stored
    report = env.recovery.run()
    bo = env.ledger.orders.get_by_order_id(bo.order_id)
    assert (bo.status, bo.submission_state) == ("REJECTED", SubmissionState.NOT_SENT)
    assert kinds(report) == ["order_not_found"] and report.ok


def _intent(env):
    from src.infrastructure.models.finance.order.order import OrderModel
    container = env.book.container("AAPL")
    env.book.trade("AAPL", 1, 100.0, submit=lambda *a, **k: None)       # creates holding / account; outcome NOT_SENT
    row = env.book.session.query(OrderModel).order_by(OrderModel.id.desc()).first()
    row2 = OrderModel(holding_id=row.holding_id, order_type=row.order_type, side=row.side, quantity=5,
                      created_at=row.created_at, status="PENDING", account_id=row.account_id)
    env.book.session.add(row2)
    env.book.session.commit()
    return row2.id, "AAPL", "BUY", 5, container, env.book.portfolio.id


def test_a_submitted_order_partly_filled_and_gone_is_cancelled_with_its_fill(env):
    bo = place(env)
    env.ib.executions = [execution("P1", bo.order_id, 3)]
    env.ib.positions = {"AAPL": 3}
    report = env.recovery.run()
    bo = env.ledger.orders.get_by_order_id(bo.order_id)
    assert (bo.status, bo.filled_quantity, bo.remaining_quantity) == ("CANCELLED", 3, 7) and report.ok


def test_a_position_mismatch_blocks_until_it_matches_again(env):
    env.ib.positions = {"AAPL": 5}                                       # e.g. bought by hand in TWS
    report = env.recovery.run()
    assert not report.ok and kinds(report) == ["position_mismatch"] and not env.recovery.trading_allowed()
    env.ib.positions = {}
    report = env.recovery.run()
    assert report.ok and [d.kind for d in report.resolved_discrepancies] == [DiscrepancyKind.POSITION_MISMATCH]
    assert "matched on recovery" in env.repo.get_all()[0].resolution


def test_an_external_execution_on_a_managed_instrument_blocks_until_the_owner_resolves_it(env):
    env.ib.executions = [execution("X1", None, 2, symbol="MSFT", broker_id=999)]
    env.ib.positions = {}
    report = env.recovery.run()
    assert not report.ok and kinds(report) == ["external_execution"]
    d = env.repo.get_open(DiscrepancyKind.EXTERNAL_EXECUTION)[0]
    with pytest.raises(ValueError):
        env.recovery.resolve(d.id, "  ")
    env.recovery.resolve(d.id, "test trade by the owner, flattened in TWS")
    assert not env.recovery.trading_allowed()                            # re-checked before trading again
    assert env.recovery.ensure()                                         # replay: same execId, not reported again
    assert env.recovery.last_report.new_discrepancies == []


def test_foreign_working_orders_are_recorded_and_block_only_on_managed_instruments(env):
    env.ib.open_orders = [working(0, broker_id=50, perm=5050, symbol="TSLA", ref=False)]
    report = env.recovery.run()
    assert kinds(report) == ["unmanaged_working_order"] and report.ok
    env.ib.open_orders.append(working(0, broker_id=51, perm=5151, symbol="MSFT", ref=False))
    report = env.recovery.run()
    assert not report.ok and [d.key for d in report.blocking] == ["5151"]


@pytest.mark.parametrize("case", ["orders", "executions", "disconnected"])
def test_incomplete_broker_lists_or_no_connection_block(env, case):
    if case == "orders":
        env.ib.orders_complete = False
    elif case == "executions":
        env.ib.executions_complete = False
    else:
        env.ib.connected = False
    report = env.recovery.run()
    assert not report.ok and kinds(report) == ["incomplete_snapshot"] and not env.recovery.trading_allowed()
    env.ib.orders_complete = env.ib.executions_complete = env.ib.connected = True
    report = env.recovery.run()
    assert report.ok and report.resolved_discrepancies


def test_a_disconnection_invalidates_and_ensure_runs_recovery_again(env):
    assert env.recovery.ensure()
    env.ib.close()
    assert not env.recovery.trading_allowed()
    env.ib.connected = True
    env.ib.positions = {"AAPL": 1}                                       # something changed while disconnected
    assert env.recovery.ensure() is False
    assert env.recovery.last_report.blocking[0].kind is DiscrepancyKind.POSITION_MISMATCH


def test_a_recovery_failure_is_reported_and_blocks(env):
    env.ib.request_open_orders_snapshot = Mock(side_effect=RuntimeError("socket"))
    report = env.recovery.run()
    assert not report.ok and "socket" in report.error and not env.recovery.trading_allowed()


def test_live_set_holdings_needs_a_successful_recovery():
    from tests.misbuffet.test_order_safety import make_upm
    upm = make_upm({"SPY": 0}, {"SPY": "CompanyShare"}, live=True)
    upm._reconciler = Mock()
    upm._reconciler.check.return_value = SimpleNamespace(ok=True, pending_tickers=set())
    upm._recovery = Mock(**{"ensure.return_value": False})
    assert upm.set_holdings({"SPY": 0.5}, SimpleNamespace(time=NOW)) == {"SPY": False}
    upm._recovery = None
    assert upm.set_holdings({"SPY": 0.5}, SimpleNamespace(time=NOW)) == {"SPY": False}


def test_domain_rules():
    assert order_id_from_ref("set_holdings_AAPL|MB42") == 42 and order_id_from_ref("MBX") is None
    assert order_id_from_ref(None) is None
    d = Discrepancy(DiscrepancyKind.POSITION_MISMATCH, "AAPL", "x", NOW, True)
    d.resolve("ok", NOW)
    with pytest.raises(ValueError):
        d.resolve("again", NOW)


def test_the_ibkr_client_collects_executions_and_order_refs():
    from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient
    c = IBTWSClient("127.0.0.1", 7497, 99)
    events = []
    c.order_listeners.append(events.append)
    c._executions_req_id = 90_001
    c.execDetails(90_001, SimpleNamespace(symbol="AAPL", localSymbol="AAPL", secType="STK", conId=1),
                  SimpleNamespace(orderId=5, execId="E.9", time="20261029  10:00:00", shares=2, price=1.0,
                                  side="BOT", permId=1, clientId=7, acctNumber="DU1", orderRef="x|MB3"))
    c.execDetailsEnd(90_001)
    assert c.executions_snapshot[0]["orderRef"] == "x|MB3" and events[0]["order_ref"] == "x|MB3"
    assert c._executions_end_event.is_set()
