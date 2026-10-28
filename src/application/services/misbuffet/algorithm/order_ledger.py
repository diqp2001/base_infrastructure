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
import queue
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional

from src.domain.entities.finance.order.broker_order import BrokerOrder, Execution, SubmissionState, status_from_tws

UNSET_DOUBLE = 1e300                    # IBKR sends Double.MAX_VALUE for "not set" commissions


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
        self._events: "queue.Queue[dict]" = queue.Queue()
        self._pending_commissions: Dict[str, dict] = {}
        self.anomalies: List[str] = []
        self.duplicates = 0

    # -- wiring ------------------------------------------------------------------------------------------------------
    def attach(self, client) -> None:
        """Listen to an IBTWSClient's order callbacks (orderStatus / execDetails / commissionReport)."""
        client.order_listeners.append(self.enqueue)

    def enqueue(self, event: dict) -> None:
        """Called on the broker's API thread: queue only."""
        self._events.put(dict(event))

    # -- submission (engine thread) ----------------------------------------------------------------------------------
    def record_intent(self, order_id: int, symbol: str, side: str, quantity: float, portfolio_id: int,
                      cash_portfolio_id: int, account: Optional[str] = None) -> BrokerOrder:
        bo = BrokerOrder(order_id=int(order_id), broker=self.broker, symbol=symbol, side=side,
                         requested_quantity=float(quantity), account=account, portfolio_id=portfolio_id,
                         cash_portfolio_id=cash_portfolio_id, created_at=self._naive(self.clock()))
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
    def drain(self, max_events: Optional[int] = None) -> int:
        """Apply the queued broker events in arrival order; returns how many were applied."""
        n = 0
        while max_events is None or n < max_events:
            try:
                event = self._events.get_nowait()
            except queue.Empty:
                break
            n += 1
            try:
                kind = event.get("kind")
                if kind == "status":
                    self.on_status(event)
                elif kind == "execution":
                    self.on_execution(event)
                elif kind == "commission":
                    self.on_commission(event)
                else:
                    self._anomaly(f"unknown broker event kind {kind!r}")
            except Exception as e:
                self._anomaly(f"broker event {event.get('kind')} not applied: {e!r}")
        return n

    def on_status(self, event: dict) -> bool:
        bo = self._match(event.get("perm_id"), event.get("order_id"), event.get("client_id"))
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

    def on_execution(self, event: dict) -> Optional[Execution]:
        exec_id = str(event.get("exec_id") or "")
        if not exec_id:
            self._anomaly("execution without an execId — ignored")
            return None
        if self.executions.get_by_exec_id(self.broker, exec_id) is not None:
            self.duplicates += 1                                   # replayed (reqExecutions, reconnect): once only
            return None
        received = self._naive(event.get("received_at") or self.clock())
        bo = self._match(event.get("perm_id"), event.get("order_id"), event.get("client_id"))
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

    def _match(self, perm_id, broker_order_id, client_id) -> Optional[BrokerOrder]:
        if perm_id:
            bo = self.orders.get_by_perm_id(self.broker, int(perm_id))
            if bo is not None:
                return bo
        if broker_order_id is None or int(broker_order_id) <= 0:
            return None
        bo = None
        if client_id is not None:
            bo = self.orders.get_by_broker_order_id(self.broker, int(broker_order_id), client_id=int(client_id))
        return bo or self.orders.get_by_broker_order_id(self.broker, int(broker_order_id))

    def _save(self, bo: BrokerOrder) -> BrokerOrder:
        """broker_orders row + the orders row it mirrors (status, filled quantity, average price), one transaction."""
        def write():
            self.orders.update(bo)
            self.orders.mirror_to_order(bo)
            return True
        if not self._atomically(write):
            raise RuntimeError(f"broker order {bo.order_id} not stored")
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

