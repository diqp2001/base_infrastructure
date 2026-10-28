"""
P.03 — order lifecycle and brokerage integration (in-memory SQLite, fake broker events; no IBKR, no orders sent).

Live path: TradeManager with an OrderLedger attached stores the order intent BEFORE sending, the submission outcome
after it, and books nothing at submission; positions and cash move only with broker executions (once per execId)
and commissions.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from src.application.services.misbuffet.algorithm.order_ledger import OrderLedger, parse_ibkr_time
from src.domain.entities.finance.order.broker_order import (
    BrokerOrder,
    Execution,
    SubmissionState,
    status_from_tws,
)
from tests.misbuffet.sqlite_portfolio import T0, SqlitePortfolio

NOW = datetime(2026, 10, 28, 15, 0, tzinfo=timezone.utc)


class FakeSubmission:
    """market_order + QCAlgorithm.last_submitted_order, with the broker's annotation chosen per test."""

    def __init__(self, outcome="sent", broker_order_id=501, ticket=True, raises=None, create_order=True):
        self.outcome, self.broker_order_id, self.ticket, self.raises = outcome, broker_order_id, ticket, raises
        self.create_order = create_order
        self.last_submitted_order = None
        self.calls = []

    def __call__(self, ticker, qty, tag=""):
        self.calls.append((ticker, qty))
        if self.create_order:
            order = SimpleNamespace(id=f"E{len(self.calls)}")
            if self.outcome is not None:
                order.submission_outcome = self.outcome
                order.broker_order_id = self.broker_order_id
                order.broker_client_id = 7
            self.last_submitted_order = order
        if self.raises:
            raise self.raises
        return SimpleNamespace(order_id=f"QC{len(self.calls)}") if self.ticket else None


@pytest.fixture
def live():
    book = SqlitePortfolio(cash=100_000.0, shares=("AAPL", "MSFT"))
    ledger = OrderLedger(book.factory, clock=lambda: NOW)
    sub = FakeSubmission()
    book.tm.attach_ledger(ledger, submission_probe=lambda: sub.last_submitted_order)
    book.ledger, book.sub = ledger, sub
    yield book
    book.close()


def send(book, ticker="AAPL", qty=10, price=150.0):
    return book.trade(ticker, qty, price, submit=book.sub)


def broker_order(book, order_id=None):
    rows = book.ledger.orders.get_all()
    return rows[-1] if order_id is None else book.ledger.orders.get_by_order_id(order_id)


def status(book, s, filled, remaining, avg=0.0, order_id=501, perm_id=9001, client_id=7):
    book.ledger.enqueue({"kind": "status", "order_id": order_id, "status": s, "filled": filled,
                         "remaining": remaining, "avg_fill_price": avg, "perm_id": perm_id, "client_id": client_id})
    book.ledger.drain()


def execution(book, exec_id, shares, price, side="BOT", order_id=501, perm_id=9001, time="20261028  10:31:05"):
    book.ledger.enqueue({"kind": "execution", "exec_id": exec_id, "order_id": order_id, "perm_id": perm_id,
                         "client_id": 7, "shares": shares, "price": price, "side": side, "time": time,
                         "symbol": "AAPL", "account": "DU123"})
    book.ledger.drain()


def commission(book, exec_id, amount, currency="USD"):
    book.ledger.enqueue({"kind": "commission", "exec_id": exec_id, "commission": amount, "currency": currency})
    book.ledger.drain()


# ── submission: intent first, outcome after, nothing booked ─────────────────────────────────────────────────────

def test_the_intent_is_stored_before_sending_and_nothing_is_booked_at_submission(live):
    seen = {}

    def submit(ticker, qty, tag=""):
        seen["rows_when_sent"] = [(o.status.name if hasattr(o.status, "name") else o.status) for o in live.orders()]
        seen["intent"] = broker_order(live).submission_state
        return live.sub(ticker, qty, tag)
    live.sub.calls.clear()
    assert live.trade("AAPL", 10, 150.0, submit=submit) is True
    assert seen == {"rows_when_sent": ["PENDING"], "intent": SubmissionState.INTENT}       # D2
    bo = broker_order(live)
    assert (bo.submission_state, bo.status, bo.broker_order_id, bo.client_id) == \
        (SubmissionState.SUBMITTED, "SUBMITTED", 501, 7)
    assert (live.qty("AAPL"), live.cash(), live.transactions()) == (0, 100_000.0, [])     # D1: no fill booked
    order = live.orders()[0]
    assert order.filled_quantity == 0 and order.external_order_id == "IBKR:501"


def test_an_order_refused_before_sending_is_not_sent_and_rejected(live):
    live.sub.outcome, live.sub.ticket = "not_sent", False
    assert send(live) is False
    bo = broker_order(live)
    assert (bo.submission_state, bo.status) == (SubmissionState.NOT_SENT, "REJECTED")
    assert live.orders()[0].status.name == "REJECTED"


def test_a_failure_before_any_engine_order_is_not_sent(live):
    live.sub.create_order, live.sub.raises = False, RuntimeError("live mode: no transaction handler attached")
    assert send(live) is False
    assert broker_order(live).submission_state is SubmissionState.NOT_SENT


def test_an_ambiguous_send_is_unknown_and_never_resent(live):
    live.sub.outcome, live.sub.ticket, live.sub.raises = "unknown", False, ConnectionResetError("socket closed")
    assert send(live) is False
    bo = broker_order(live)
    assert (bo.submission_state, bo.status, bo.broker_order_id) == (SubmissionState.UNKNOWN, "PENDING", 501)
    assert len(live.sub.calls) == 1 and live.ledger.anomalies                        # sent once, reported
    assert bo in live.ledger.open_orders()                                          # still open: P.04 decides
    status(live, "Submitted", 0, 10)                                                # the broker reports it
    bo = broker_order(live)
    assert (bo.submission_state, bo.status) == (SubmissionState.SUBMITTED, "SUBMITTED")


def test_the_broker_had_it_even_if_the_handler_failed_afterwards(live):
    live.sub.ticket = False                                                         # outcome 'sent', no ticket
    assert send(live) is True
    assert broker_order(live).submission_state is SubmissionState.SUBMITTED


def test_without_a_probe_a_failed_submission_is_unknown(live):
    live.tm._submission_probe = None
    live.sub.ticket = False
    assert send(live) is False
    assert broker_order(live).submission_state is SubmissionState.UNKNOWN


# ── broker statuses: forward only ───────────────────────────────────────────────────────────────────────────────

def test_statuses_move_forward_only_and_mirror_the_order_row(live):
    send(live)
    status(live, "Submitted", 4, 6, 150.1)
    status(live, "Submitted", 2, 8, 150.0)                                          # late, smaller fill: dropped
    status(live, "PreSubmitted", 0, 10)                                             # out of order: dropped
    bo = broker_order(live)
    assert (bo.status, bo.filled_quantity, bo.remaining_quantity, bo.perm_id) == ("PARTIALLY_FILLED", 4, 6, 9001)
    status(live, "Filled", 10, 0, 150.2)
    status(live, "Submitted", 10, 0, 150.2)                                         # after terminal: dropped
    order = live.orders()[0]
    assert (order.status.name, order.filled_quantity, order.average_fill_price) == ("FILLED", 10, 150.2)


def test_an_unrecognised_status_or_an_unknown_order_is_reported_not_applied(live):
    send(live)
    status(live, "Weird", 0, 10)
    status(live, "Submitted", 0, 5, order_id=999, perm_id=0)
    assert broker_order(live).status == "SUBMITTED" and len(live.ledger.anomalies) == 2


def test_cancel_is_only_requested_until_the_broker_confirms(live):
    send(live)
    bo = live.ledger.request_cancel(broker_order(live).order_id)
    assert bo.cancel_requested_at is not None and broker_order(live).status == "SUBMITTED"   # D4
    status(live, "PendingCancel", 3, 7)
    assert broker_order(live).status == "PARTIALLY_FILLED"
    status(live, "Cancelled", 3, 7)
    assert (broker_order(live).status, broker_order(live).filled_quantity) == ("CANCELLED", 3)
    with pytest.raises(ValueError):
        live.ledger.request_cancel(bo.order_id)                                     # terminal


# ── executions and commissions: booked once ────────────────────────────────────────────────────────────────────

def test_executions_book_position_and_cash_once_per_exec_id(live):
    send(live)
    execution(live, "0001.01", 4, 150.0)
    execution(live, "0001.01", 4, 150.0)                                            # replayed: ignored
    execution(live, "0001.02", 6, 151.0)
    assert live.qty("AAPL") == 10
    assert live.cash() == pytest.approx(100_000.0 - 4 * 150.0 - 6 * 151.0)
    assert live.ledger.duplicates == 1
    executions = live.ledger.executions.get_by_order_id(broker_order(live).order_id)
    assert [(e.exec_id, e.booked, e.executed_at) for e in executions] == [
        ("0001.01", True, datetime(2026, 10, 28, 10, 31, 5)), ("0001.02", True, datetime(2026, 10, 28, 10, 31, 5))]


def test_a_commission_is_booked_once_even_when_it_arrives_first(live):
    send(live)
    commission(live, "0002.01", 1.25)                                               # before its execution
    execution(live, "0002.01", 10, 100.0)
    commission(live, "0002.01", 1.25)                                               # repeated
    assert live.cash() == pytest.approx(100_000.0 - 1_000.0 - 1.25)
    ex = live.ledger.executions.get_by_exec_id("IBKR", "0002.01")
    assert (ex.commission, ex.commission_booked) == (1.25, True)
    commission(live, "0002.01", 1.7976931348623157e308)                             # IBKR "not set": ignored
    assert live.cash() == pytest.approx(100_000.0 - 1_001.25)


def test_a_sell_execution_credits_cash_and_reduces_the_position(live):
    send(live)
    execution(live, "B1", 10, 100.0)
    live.sub.broker_order_id = 502
    send(live, qty=-4, price=110.0)
    execution(live, "S1", 4, 110.0, side="SLD", order_id=502, perm_id=9002)
    assert (live.qty("AAPL"), live.cash()) == (6, pytest.approx(100_000.0 - 1_000.0 + 440.0))


@pytest.mark.parametrize("case", ["external", "wrong_side", "overfill"])
def test_unexplained_executions_are_stored_unbooked_and_reported(live, case):
    send(live)
    if case == "external":
        execution(live, "X1", 5, 100.0, order_id=0, perm_id=777)
    elif case == "wrong_side":
        execution(live, "X1", 5, 100.0, side="SLD")
    else:
        execution(live, "X0", 8, 100.0)
        execution(live, "X1", 5, 100.0)
    ex = live.ledger.executions.get_by_exec_id("IBKR", "X1")
    assert ex is not None and not ex.booked and ex.notes and live.ledger.anomalies
    assert live.qty("AAPL") == (8 if case == "overfill" else 0)
    if case == "external":
        assert ex.order_id is None and live.ledger.executions.get_unexplained() == [ex]


def test_a_failed_booking_rolls_back_the_execution_and_keeps_it_visible(live):
    send(live)
    live.tm._update_position = Mock(side_effect=lambda *a: live.tm._step_failed("position: boom"))
    execution(live, "F1", 10, 100.0)
    ex = live.ledger.executions.get_by_exec_id("IBKR", "F1")
    assert ex is not None and not ex.booked and "rolled back" in ex.notes
    assert (live.cash(), live.transactions()) == (100_000.0, [])


def test_the_api_thread_only_queues(live):
    send(live)
    live.ledger.enqueue({"kind": "execution", "exec_id": "Q1", "order_id": 501, "perm_id": 9001, "shares": 1,
                         "price": 1.0, "side": "BOT", "time": ""})
    assert live.ledger.executions.get_by_exec_id("IBKR", "Q1") is None             # nothing until drain
    assert live.ledger.drain() == 1 and live.qty("AAPL") == 1


# ── wiring ───────────────────────────────────────────────────────────────────────────────────────────────────────

def test_live_set_holdings_needs_an_order_ledger_and_drains_it():
    from tests.misbuffet.test_order_safety import make_upm
    upm = make_upm({"SPY": 0}, {"SPY": "CompanyShare"}, live=True)
    upm._reconciler = Mock()
    upm._reconciler.check.return_value = SimpleNamespace(ok=True, pending_tickers=set())
    upm._order_ledger = None
    assert upm.set_holdings({"SPY": 0.5}, SimpleNamespace(time=T0)) == {"SPY": False}
    upm._order_ledger = Mock()
    upm.set_holdings({"SPY": 0.5}, SimpleNamespace(time=T0))
    upm._order_ledger.drain.assert_called_once()


def test_the_ibkr_client_tells_order_listeners_and_records_commissions():
    from src.application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient
    c = IBTWSClient("127.0.0.1", 7497, 99)
    events = []
    c.order_listeners.append(events.append)
    c.orderStatus(5, "Submitted", 0, 10, 0.0, 123, 0, 0.0, 99, "", 0.0)
    c.execDetails(-1, SimpleNamespace(symbol="AAPL", localSymbol="AAPL", secType="STK", conId=265598),
                  SimpleNamespace(orderId=5, execId="E.1", time="20261028  10:00:00", shares=10, price=150.0,
                                  side="BOT", permId=123, clientId=99, acctNumber="DU1"))
    c.commissionReport(SimpleNamespace(execId="E.1", commission=1.0, currency="USD"))
    assert [e["kind"] for e in events] == ["status", "execution", "commission"]
    assert events[1]["perm_id"] == 123 and c.commissions["E.1"]["commission"] == 1.0


def test_the_ibkr_broker_annotates_the_submission_outcome():
    from src.application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker
    broker = InteractiveBrokersBroker.__new__(InteractiveBrokersBroker)
    broker.logger, broker.pending_orders = Mock(), {}
    broker._contract_for_order = lambda o: SimpleNamespace(secType="STK", symbol="AAPL", localSymbol="AAPL")
    broker._order_action = lambda o: "BUY"
    broker._enum_name = lambda v: "MARKET"

    class Conn:
        client_id = 7
        last_send_attempt_order_id = None

        def __init__(self, fail_after_send=False, fail_before_send=False):
            self.after, self.before = fail_after_send, fail_before_send

        def is_connected(self):
            return True

        def create_market_order(self, action, qty):
            return object()

        def place_order(self, contract, order):
            if self.before:
                raise ConnectionError("Not connected to TWS")
            self.last_send_attempt_order_id = 42
            if self.after:
                raise OSError("socket write failed")
            return 42

    for conn, expected, ok in ((Conn(), "sent", True), (Conn(fail_before_send=True), "not_sent", False),
                               (Conn(fail_after_send=True), "unknown", False)):
        broker.ib_connection = conn
        order = SimpleNamespace(id="o", quantity=10)
        assert broker._place_order_impl(order) is ok
        assert order.submission_outcome == expected
        if expected != "not_sent":
            assert order.broker_order_id == 42


# ── pure domain ────────────────────────────────────────────────────────────────────────────────────────────────

def test_domain_rules():
    assert status_from_tws("Submitted", 3, 7) == "PARTIALLY_FILLED"
    assert status_from_tws("Inactive", 0, 10) == "REJECTED" and status_from_tws("Nope", 0, 0) is None
    bo = BrokerOrder(order_id=1, broker="IBKR", symbol="AAPL", side="BUY", requested_quantity=10)
    bo.mark_not_sent("risk gate", NOW)
    with pytest.raises(ValueError):
        bo.mark_submitted(1, NOW)                                                   # NOT_SENT is final
    with pytest.raises(ValueError):
        BrokerOrder(order_id=1, broker="IBKR", symbol="AAPL", side="BUY", requested_quantity=0)
    assert Execution("e", "IBKR", "AAPL", "SLD", 2, 1.0, NOW).signed_quantity == -2
    with pytest.raises(ValueError):
        Execution("e", "IBKR", "AAPL", "XXX", 2, 1.0, NOW)
    assert parse_ibkr_time("20261028-14:30:00", NOW) == datetime(2026, 10, 28, 14, 30)
    assert parse_ibkr_time("garbage", NOW) is NOW
