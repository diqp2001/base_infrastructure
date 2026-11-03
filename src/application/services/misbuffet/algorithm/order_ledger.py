"""
OrderLedger — the durable record of live orders at the broker, and the only path from broker executions to the
books (P.03; tables broker_orders / broker_executions).

Submission (engine thread, called by TradeManager in live mode):
    record_intent      BEFORE sending: orders row (PENDING) + broker_orders row (INTENT), one transaction
    mark_submitted     the broker took it (broker order id)
    mark_not_sent      it definitely never left -> REJECTED
    mark_unknown       sending was attempted and failed: never resent; a later broker event resolves it (P.04)

Broker events (IBTWSClient.order_listeners, API thread): ``enqueue`` only queues them; ``drain`` applies them on
the engine thread (the API thread never touches the database session):
    status       order status moved FORWARD only (order_state.advances); late / repeated / out-of-order events never
                 move it back; the orders row mirrors status, filled quantity and average price
    execution    stored once per execId (unique) and booked once: transaction + position + cash, in ONE database
                 transaction with the execution row. An execution no internal order explains (manual / external
                 trade), on the wrong side, or that would overfill the order is stored UNBOOKED and reported in
                 ``anomalies`` — never booked silently.
    commission   booked once per execution as a cash debit (credit for a rebate); a commission that arrives before
                 its execution waits for it.

Cancel (D4): ``request_cancel`` records the request; the order is CANCELLED only when the broker says so.
"""

from __future__ import annotations

import logging
import math
import threading
from collections import deque
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from src.domain.entities.finance.order.broker_order import (
    BrokerOrder,
    Execution,
    SubmissionState,
    order_id_from_ref,
    status_from_tws,
)

UNSET_DOUBLE = 1e300                    # IBKR sends Double.MAX_VALUE for "not set" commissions
# IBKR order-level error codes that mean the order was NOT accepted (P.06). Only these reject an unacknowledged
# order: rejecting on any other code would free a symbol whose order may still be working (duplicate-order risk).
# Every other code (e.g. 399 held until the open, 10349 TIF set to DAY by a preset, 202 cancel confirmation) is
# logged; the broker's order statuses and P.04 recovery settle the order.
ORDER_REJECTION_CODES = frozenset({103, 104, 105, 106, 107, 109, 110, 111, 113, 116, 117, 118, 135, 200, 201, 203,
                                   321, 382, 383, 387, 388, 10268})


class LedgerStorageError(RuntimeError):
    """A ledger row could not be written (database unavailable): the broker event must be retried, not dropped."""


MAX_EVENT_ATTEMPTS = 20                 # a failed event is retried this many drains, then dropped (reported)
_OUTAGE_ERRORS = {"OperationalError", "InterfaceError", "DisconnectionError", "TimeoutError"}


def _is_storage_failure(e: Exception) -> bool:
    """An outage worth retrying (connection lost, database unavailable) — not a data error such as an
    IntegrityError, which would fail again forever."""
    if isinstance(e, (LedgerStorageError, ConnectionError, OSError)):
        return True
    return any(cls.__name__ in _OUTAGE_ERRORS for cls in type(e).__mro__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_ibkr_time(value, fallback: datetime) -> datetime:
    """IBKR execution time ('20261028  14:30:00 US/Eastern', '20261028-14:30:00', '20261028 14:30:00') -> datetime;
    the trailing time zone name is dropped (kept naive, as IBKR's text gives it)."""
    if isinstance(value, datetime):
        return value
    text = str(value or "").strip()
    parts = text.replace("-", " ").split()
    if len(parts) >= 2:
        try:
            return datetime.strptime(f"{parts[0]} {parts[1]}", "%Y%m%d %H:%M:%S")
        except ValueError:
            pass
    return fallback


class OrderLedger:

    def __init__(self, repository_factory, trade_manager=None, broker: str = "IBKR",
                 clock: Callable[[], datetime] = _utcnow, logger=None):
        self.orders = repository_factory.broker_order_local_repo
        self.executions = repository_factory.broker_execution_local_repo
        self.session = self.orders.session
        self.trade_manager = trade_manager
        self.broker = broker
        self.clock = clock
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._events: "deque[dict]" = deque()
        self._events_lock = threading.Lock()
        self.storage_failures = 0                  # drains stopped by a database failure (events kept, retried)
        self.last_storage_error: Optional[str] = None
        self._pending_commissions: Dict[str, dict] = {}
        self.anomalies: List[str] = []
        self.current_decision_id: Optional[int] = None   # set by the strategy around a rebalance (P.06.05)
        self.duplicates = 0

    # -- wiring ------------------------------------------------------------------------------------------------------
    def attach(self, client) -> None:
        """Listen to an IBTWSClient's order callbacks (orderStatus / execDetails / commissionReport)."""
        client.order_listeners.append(self.enqueue)

    def enqueue(self, event: dict) -> None:
        """Called on the broker's API thread: queue only."""
        with self._events_lock:
            self._events.append(dict(event))

    # -- submission (engine thread) ----------------------------------------------------------------------------------
    def record_intent(self, order_id: int, symbol: str, side: str, quantity: float, portfolio_id: int,
                      cash_portfolio_id: int, account: Optional[str] = None) -> BrokerOrder:
        bo = BrokerOrder(order_id=int(order_id), broker=self.broker, symbol=symbol, side=side,
                         requested_quantity=float(quantity), account=account, portfolio_id=portfolio_id,
                         cash_portfolio_id=cash_portfolio_id, created_at=self._naive(self.clock()),
                         decision_id=self.current_decision_id)
        return self.orders.add(bo)

    def mark_submitted(self, bo: BrokerOrder, broker_order_id: Optional[int], client_id: Optional[int] = None):
        bo.mark_submitted(broker_order_id, self._naive(self.clock()), client_id=client_id)
        return self._save(bo)

    def mark_not_sent(self, bo: BrokerOrder, reason: str):
        bo.mark_not_sent(reason, self._naive(self.clock()))
        return self._save(bo)

    def mark_unknown(self, bo: BrokerOrder, reason: str, broker_order_id: Optional[int] = None):
        bo.mark_unknown(reason, self._naive(self.clock()), broker_order_id=broker_order_id)
        self._anomaly(f"order {bo.order_id} ({bo.side} {bo.requested_quantity:g} {bo.symbol}): submission outcome "
                      f"UNKNOWN ({reason}) — not resent; the broker's state decides")
        return self._save(bo)

    def request_cancel(self, order_id: int) -> BrokerOrder:
        """Record a cancel request (D4): the status stays as it is until the broker confirms the cancel."""
        bo = self.orders.get_by_order_id(order_id)
        if bo is None:
            raise LookupError(f"no broker order for order {order_id}")
        bo.request_cancel(self._naive(self.clock()))
        return self._save(bo)

    def open_orders(self) -> List[BrokerOrder]:
        return self.orders.get_open()

    # -- broker events (engine thread) -------------------------------------------------------------------------------
    def pending_events(self) -> int:
        with self._events_lock:
            return len(self._events)

    def drain(self, max_events: Optional[int] = None) -> int:
        """Apply the queued broker events in arrival order; returns how many were applied. A DATABASE failure puts
        the event back at the front and stops the drain (P.06.07): nothing is lost, the next drain retries it in
        order. Any other failure is reported and the event dropped (the broker replays executions on recovery)."""
        n = 0
        while max_events is None or n < max_events:
            with self._events_lock:
                if not self._events:
                    break
                event = self._events.popleft()
            try:
                kind = event.get("kind")
                if kind == "status":
                    self.on_status(event)
                elif kind == "execution":
                    self.on_execution(event)
                elif kind == "commission":
                    self.on_commission(event)
                elif kind == "order_error":
                    self.on_order_error(event)
                else:
                    self._anomaly(f"unknown broker event kind {kind!r}")
                n += 1
            except Exception as e:
                event["_attempts"] = event.get("_attempts", 0) + 1
                if _is_storage_failure(e) and event["_attempts"] < MAX_EVENT_ATTEMPTS:
                    with self._events_lock:
                        self._events.appendleft(event)
                    self.storage_failures += 1
                    self.last_storage_error = repr(e)[:500]
                    self.logger.critical(f"OrderLedger: database failure, {self.pending_events()} broker event(s) "
                                         f"kept for retry: {e!r}")
                    break
                n += 1
                self._anomaly(f"broker event {event.get('kind')} not applied: {e!r}")
        return n

    def on_status(self, event: dict) -> bool:
        bo = self._match(event.get("perm_id"), event.get("order_id"), event.get("client_id"), event.get("order_ref"))
        if bo is None:
            self._anomaly(f"status {event.get('status')} for broker order {event.get('order_id')} / perm "
                          f"{event.get('perm_id')}: no internal order (external order?)")
            return False
        filled = float(event.get("filled") or 0)
        remaining = event.get("remaining")
        remaining = float(remaining) if remaining is not None else None
        status = status_from_tws(event.get("status"), filled, remaining or 0.0)
        if status is None:
            self._anomaly(f"order {bo.order_id}: unrecognised broker status {event.get('status')!r} — ignored")
            return False
        at = self._naive(event.get("received_at") or self.clock())
        if bo.submission_state is SubmissionState.UNKNOWN:
            bo.mark_submitted(event.get("order_id"), at, client_id=event.get("client_id"))   # the broker has it
        avg = event.get("avg_fill_price")
        changed = bo.apply_status(status, filled, remaining, float(avg) if avg else None, at,
                                  perm_id=event.get("perm_id"))
        self._save(bo)
        return changed

    def on_order_error(self, event: dict) -> bool:
        """An IBKR error for one of our orders. Before the broker acknowledged the order (no permId, nothing
        filled), a rejection code (ORDER_REJECTION_CODES: e.g. 321 API read-only, 201 rejected, 10268) rejects it.
        After that, the broker's statuses decide: the error is reported, not applied."""
        code, message = int(event.get("code") or 0), str(event.get("message") or "")
        bo = self._match(None, event.get("order_id"), event.get("client_id"))
        if bo is None:
            self._anomaly(f"IBKR error {code} for broker order {event.get('order_id')}: no internal order ({message})")
            return False
        if code not in ORDER_REJECTION_CODES:
            self.logger.warning(f"OrderLedger: order {bo.order_id} notice {code}: {message}")
            return False
        if bo.is_terminal:
            return False
        if bo.perm_id or bo.filled_quantity > 0:
            self._anomaly(f"order {bo.order_id}: IBKR error {code} after acknowledgement ({message}) — status "
                          f"left to the broker's order status")
            return False
        at = self._naive(event.get("received_at") or self.clock())
        changed = bo.apply_status("REJECTED", 0.0, bo.requested_quantity, None, at)
        bo.message = f"IBKR {code}: {message}"[:2000]
        self._save(bo)
        self.logger.critical(f"OrderLedger: order {bo.order_id} REJECTED by IBKR {code}: {message}")
        return changed

    def on_execution(self, event: dict) -> Optional[Execution]:
        exec_id = str(event.get("exec_id") or "")
        if not exec_id:
            self._anomaly("execution without an execId — ignored")
            return None
        if self.executions.get_by_exec_id(self.broker, exec_id) is not None:
            self.duplicates += 1                                   # replayed (reqExecutions, reconnect): once only
            return None
        received = self._naive(event.get("received_at") or self.clock())
        bo = self._match(event.get("perm_id"), event.get("order_id"), event.get("client_id"), event.get("order_ref"))
        ex = Execution(exec_id=exec_id, broker=self.broker, symbol=bo.symbol if bo else str(event.get("symbol") or ""),
                       side=event.get("side"), quantity=float(event.get("shares")), price=float(event.get("price")),
                       executed_at=parse_ibkr_time(event.get("time"), received), broker_order_id=event.get("order_id"),
                       perm_id=event.get("perm_id"), order_id=bo.order_id if bo else None,
                       account=event.get("account"), received_at=received)
        problem = self._booking_problem(ex, bo)
        if problem is None:
            ex.booked = True
            if self._atomically(lambda: self._store_and_book(ex, bo)):
                self._apply_pending_commission(ex, bo)
                return ex
            problem = "booking failed and was rolled back"
            ex.booked, ex.id = False, None
        ex.notes = problem
        self._anomaly(f"execution {exec_id} ({ex.side} {ex.quantity:g} {ex.symbol} @ {ex.price}): {problem} — "
                      f"stored unbooked")
        self.executions.add(ex)
        return ex

    def on_commission(self, event: dict) -> bool:
        exec_id = str(event.get("exec_id") or "")
        amount = event.get("commission")
        if amount is None or not math.isfinite(float(amount)) or abs(float(amount)) >= UNSET_DOUBLE:
            return False                                           # IBKR "not set"
        ex = self.executions.get_by_exec_id(self.broker, exec_id)
        if ex is None:
            self._pending_commissions[exec_id] = dict(event)       # the execution has not arrived yet
            return False
        bo = self.orders.get_by_order_id(ex.order_id) if ex.order_id is not None else None
        return self._book_commission(ex, bo, float(amount), event.get("currency"))

    # -- adoption (P.06.15) ------------------------------------------------------------------------------------------
    def adopt(self, exec_id: str, portfolio_id: int, cash_portfolio_id: int, reason: str) -> BrokerOrder:
        """Adopt an external execution (e.g. a manual flatten in TWS) into the strategy's book, as if it were a fill
        of our own order: the internal order it lacks is created (FILLED at the execution's quantity and price, perm
        id kept) and the fill is booked — transaction, position, cash, and its USD commission — in ONE database
        transaction with the execution row. Raises ValueError when it cannot be adopted; nothing is written then."""
        if not reason or not reason.strip():
            raise ValueError("an adoption needs a reason")
        if self.trade_manager is None:
            raise ValueError("no trade manager to book it")
        ex = self.executions.get_by_exec_id(self.broker, str(exec_id))
        if ex is None:
            raise ValueError(f"execution {exec_id} is not stored")
        if ex.order_id is not None or ex.booked:
            raise ValueError(f"execution {exec_id} already belongs to order {ex.order_id} (booked: {ex.booked}) — "
                             f"only an execution no internal order explains can be adopted")
        tm, now = self.trade_manager, self._naive(self.clock())
        book_commission = (ex.commission is not None and not ex.commission_booked
                           and ex.commission_currency in (None, "", "USD"))
        outcome: dict = {}

        def write() -> bool:
            holding_id = tm._resolve_holding_id(ex.symbol, portfolio_id, ex.executed_at)
            account_id = tm._resolve_account_id(ex.executed_at)
            if holding_id is None or account_id is None:
                outcome["problem"] = f"cannot be booked (holding={holding_id}, account={account_id})"
                return False
            order = tm.order_repo._create_or_get(
                external_order_id=f"{self.broker}:ADOPTED:{ex.exec_id}", portfolio_id=portfolio_id,
                order_type="MARKET", side=ex.side, quantity=ex.quantity, created_at=ex.executed_at, status="FILLED",
                symbol=ex.symbol, holding_id=holding_id, account_id=account_id, price=ex.price,
                filled_quantity=ex.quantity, average_fill_price=ex.price)
            if order is None:
                outcome["problem"] = "the internal order could not be created"
                return False
            bo = self.orders.add(BrokerOrder(
                order_id=order.id, broker=self.broker, symbol=ex.symbol, side=ex.side,
                requested_quantity=ex.quantity, account=ex.account, portfolio_id=portfolio_id,
                cash_portfolio_id=cash_portfolio_id, submission_state=SubmissionState.SUBMITTED,
                perm_id=ex.perm_id, status="FILLED", filled_quantity=ex.quantity, remaining_quantity=0.0,
                average_fill_price=ex.price, created_at=now, submitted_at=ex.executed_at, last_event_at=now,
                message=f"adopted external execution {ex.exec_id}: {reason}"))
            ex.order_id, ex.booked, ex.commission_booked = bo.order_id, True, book_commission
            ex.notes = (f"{ex.notes}; " if ex.notes else "") + f"adopted into order {bo.order_id}: {reason}"
            self.executions.update(ex)
            if not tm.book_execution(order_id=bo.order_id, ticker=ex.symbol, signed_qty=ex.signed_quantity,
                                     price=ex.price, portfolio_id=portfolio_id, cash_portfolio_id=cash_portfolio_id,
                                     when=ex.executed_at, ref=ex.exec_id):
                return False
            if book_commission and not tm.book_commission(ex.commission, cash_portfolio_id, ex.executed_at):
                return False
            outcome["order"] = bo
            return True

        if not self._atomically(write):
            ex.order_id, ex.booked, ex.commission_booked = None, False, False
            raise ValueError(f"execution {exec_id} not adopted: "
                             f"{outcome.get('problem', 'booking failed and was rolled back')}")
        if ex.commission is not None and not book_commission and not ex.commission_booked:
            self._anomaly(f"commission {ex.commission} {ex.commission_currency} on adopted {ex.exec_id}: "
                          f"non-USD commission not booked")
        return outcome["order"]

    # -- internals ---------------------------------------------------------------------------------------------------
    def _booking_problem(self, ex: Execution, bo: Optional[BrokerOrder]) -> Optional[str]:
        if bo is None:
            return "no internal order explains it (manual / external trade)"
        if self.trade_manager is None:
            return "no trade manager to book it"
        if ex.side != bo.side:
            return f"side {ex.side} differs from the order's {bo.side}"
        booked = sum(e.quantity for e in self.executions.get_by_order_id(bo.order_id) if e.booked)
        if booked + ex.quantity > bo.requested_quantity + 1e-9:
            return (f"would overfill the order ({booked:g} booked + {ex.quantity:g} > "
                    f"{bo.requested_quantity:g} requested)")
        if bo.portfolio_id is None or bo.cash_portfolio_id is None:
            return "the order has no portfolio to book into"
        return None

    def _store_and_book(self, ex: Execution, bo: BrokerOrder) -> bool:
        self.executions.add(ex)
        return self.trade_manager.book_execution(order_id=bo.order_id, ticker=bo.symbol,
                                                 signed_qty=ex.signed_quantity, price=ex.price,
                                                 portfolio_id=bo.portfolio_id,
                                                 cash_portfolio_id=bo.cash_portfolio_id,
                                                 when=ex.executed_at, ref=ex.exec_id)

    def _apply_pending_commission(self, ex: Execution, bo: BrokerOrder) -> None:
        pending = self._pending_commissions.pop(ex.exec_id, None)
        if pending is not None:
            self._book_commission(ex, bo, float(pending["commission"]), pending.get("currency"))

    def _book_commission(self, ex: Execution, bo: Optional[BrokerOrder], amount: float, currency) -> bool:
        if ex.commission_booked:
            self.duplicates += 1
            return False
        ex.commission, ex.commission_currency = amount, currency
        if bo is None or not ex.booked or self.trade_manager is None:
            self.executions.update(ex)                             # recorded, not booked (unexplained execution)
            return False
        if currency not in (None, "", "USD"):
            self._anomaly(f"commission {amount} {currency} on {ex.exec_id}: non-USD commission not booked")
            self.executions.update(ex)
            return False

        def book():
            ex.commission_booked = True
            self.executions.update(ex)
            return self.trade_manager.book_commission(amount, bo.cash_portfolio_id, ex.executed_at)
        if self._atomically(book):
            return True
        ex.commission_booked = False
        self._anomaly(f"commission {amount} on {ex.exec_id}: booking failed and was rolled back")
        return False

    def match(self, perm_id=None, broker_order_id=None, client_id=None, order_ref=None) -> Optional[BrokerOrder]:
        return self._match(perm_id, broker_order_id, client_id, order_ref)

    def _match(self, perm_id, broker_order_id, client_id, order_ref=None) -> Optional[BrokerOrder]:
        """permId, then our own reference (orderRef 'MB<id>': survives a crash before the broker id was stored),
        then orderId (+ client id)."""
        if perm_id:
            bo = self.orders.get_by_perm_id(self.broker, int(perm_id))
            if bo is not None:
                return bo
        internal = order_id_from_ref(order_ref)
        if internal is not None:
            bo = self.orders.get_by_order_id(internal)
            if bo is not None:
                return bo
        if broker_order_id is None or int(broker_order_id) <= 0:
            return None
        if client_id is not None:
            bo = self.orders.get_by_broker_order_id(self.broker, int(broker_order_id), client_id=int(client_id))
            if bo is not None:
                return bo
        # orderIds are per client id: another client's order 1 is not ours (paper 2026-11-03: an external BUY BAC
        # from client 45 matched an old strategy order 1). Only a row without a stored client id may match, and
        # never when either identifier contradicts it.
        bo = self.orders.get_by_broker_order_id(self.broker, int(broker_order_id))
        if bo is None:
            return None
        if client_id is not None and bo.client_id is not None and int(bo.client_id) != int(client_id):
            return None
        if perm_id and bo.perm_id and int(bo.perm_id) != int(perm_id):
            return None
        return bo

    def _save(self, bo: BrokerOrder) -> BrokerOrder:
        """broker_orders row + the orders row it mirrors (status, filled quantity, average price), one transaction."""
        def write():
            self.orders.update(bo)
            self.orders.mirror_to_order(bo)
            return True
        if not self._atomically(write):
            raise LedgerStorageError(f"broker order {bo.order_id} not stored")
        return bo

    def _atomically(self, step) -> bool:
        if self.trade_manager is not None:
            return self.trade_manager._book_atomically(step)
        from src.infrastructure.database.unit_of_work import atomic
        try:
            with atomic(self.session) as tx:
                if not step():
                    tx.fail("step failed")
            return True
        except Exception as e:
            self.logger.error(f"OrderLedger: rolled back ({e!r})")
            return False

    def _anomaly(self, message: str) -> None:
        self.anomalies.append(message)
        self.logger.critical(f"OrderLedger: {message}")

    @staticmethod
    def _naive(value: datetime) -> datetime:
        """Stored as naive UTC (DateTime columns without time zone)."""
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        return value

