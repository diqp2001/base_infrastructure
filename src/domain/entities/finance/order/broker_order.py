"""
An internal order's life at a broker, and the broker's executions (pure; no I/O). P.03.

BrokerOrder — one per internal Order sent (or about to be sent) to a broker:
    submission_state  INTENT (recorded BEFORE sending), SUBMITTED (the broker took it; broker order id known),
                      NOT_SENT (definitely never left: validation, risk gate, no connection),
                      UNKNOWN (sending was attempted and its outcome is not known: an exception or a timeout after the
                      send call — never resubmitted automatically; the broker's state decides, see P.04)
    status            the order status, moved FORWARD only (order_state.advances): late, repeated or out-of-order
                      broker events never move it back; filled / remaining quantities and the average fill price
                      follow the broker's cumulative figures
    cancel_requested  a cancel was asked; the order is CANCELLED only when the broker confirms it

Execution — one per broker execution id (IBKR execId): idempotent by that id; ``order_id`` None means the broker
reports a trade no internal order explains (manual / external trade: visible, never booked silently).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

from src.domain.entities.finance.order.order_state import advances, is_terminal


class SubmissionState(str, Enum):
    INTENT = "intent"
    SUBMITTED = "submitted"
    NOT_SENT = "not_sent"
    UNKNOWN = "unknown"


# IBKR orderStatus strings -> internal order status names (order.OrderStatus values)
TWS_STATUS = {
    "PendingSubmit": "SUBMITTED", "ApiPending": "SUBMITTED", "PreSubmitted": "SUBMITTED", "Submitted": "SUBMITTED",
    "PendingCancel": "SUBMITTED", "ApiCancelled": "CANCELLED", "Cancelled": "CANCELLED", "Filled": "FILLED",
    "Inactive": "REJECTED",
}


def status_from_tws(tws_status: str, filled: float, remaining: float) -> Optional[str]:
    """Internal status for an IBKR orderStatus; None when the string is not one IBKR documents."""
    base = TWS_STATUS.get(str(tws_status or ""))
    if base is None:
        return None
    if base == "SUBMITTED" and filled > 0 and remaining > 0:
        return "PARTIALLY_FILLED"
    return base


@dataclass
class BrokerOrder:
    order_id: int                                   # internal orders.id
    broker: str
    symbol: str
    side: str                                       # BUY / SELL
    requested_quantity: float
    account: Optional[str] = None
    portfolio_id: Optional[int] = None              # portfolio whose position a fill moves
    cash_portfolio_id: Optional[int] = None         # portfolio whose cash a fill / commission moves
    id: Optional[int] = None
    submission_state: SubmissionState = SubmissionState.INTENT
    broker_order_id: Optional[int] = None           # IBKR orderId (per client id)
    perm_id: Optional[int] = None                   # IBKR permId (stable across sessions)
    client_id: Optional[int] = None
    status: str = "PENDING"
    filled_quantity: float = 0.0
    remaining_quantity: Optional[float] = None
    average_fill_price: Optional[float] = None
    created_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    last_event_at: Optional[datetime] = None
    cancel_requested_at: Optional[datetime] = None
    message: str = ""

    def __post_init__(self):
        if self.requested_quantity <= 0:
            raise ValueError("requested quantity must be positive (the side gives the direction)")
        if self.remaining_quantity is None:
            self.remaining_quantity = float(self.requested_quantity)

    @property
    def is_terminal(self) -> bool:
        return is_terminal(self.status)

    def mark_submitted(self, broker_order_id: Optional[int], at: datetime, client_id: Optional[int] = None) -> None:
        """The broker took the order (or, from UNKNOWN, the broker reported it: the ambiguity is resolved)."""
        if self.submission_state not in (SubmissionState.INTENT, SubmissionState.UNKNOWN):
            raise ValueError(f"cannot mark a {self.submission_state.value} order submitted")
        self.submission_state = SubmissionState.SUBMITTED
        if broker_order_id is not None:
            self.broker_order_id = int(broker_order_id)
        self.client_id = client_id if client_id is not None else self.client_id
        self.submitted_at = at
        if self.status == "PENDING":
            self.status = "SUBMITTED"

    def mark_not_sent(self, reason: str, at: datetime) -> None:
        if self.submission_state is not SubmissionState.INTENT:
            raise ValueError(f"cannot mark a {self.submission_state.value} order not sent")
        self.submission_state = SubmissionState.NOT_SENT
        self.status = "REJECTED"
        self.message = reason
        self.last_event_at = at

    def mark_unknown(self, reason: str, at: datetime, broker_order_id: Optional[int] = None) -> None:
        """The send was attempted but its outcome is unknown: nothing is resent; the broker's state decides."""
        if self.submission_state is not SubmissionState.INTENT:
            raise ValueError(f"cannot mark a {self.submission_state.value} order unknown")
        self.submission_state = SubmissionState.UNKNOWN
        if broker_order_id is not None:
            self.broker_order_id = int(broker_order_id)     # the id the send used: a later status resolves it
        self.message = reason
        self.last_event_at = at

    def apply_status(self, status: str, filled: float, remaining: Optional[float], average_price: Optional[float],
                     at: datetime, perm_id: Optional[int] = None) -> bool:
        """Apply a broker status if it moves the order forward (returns whether it did)."""
        if perm_id:
            self.perm_id = int(perm_id)
        if not advances(self.status, self.filled_quantity, status, float(filled)):
            return False
        self.status = status
        self.filled_quantity = float(filled)
        if remaining is not None:
            self.remaining_quantity = float(remaining)
        if average_price is not None and average_price > 0:
            self.average_fill_price = float(average_price)
        self.last_event_at = at
        return True

    def request_cancel(self, at: datetime) -> None:
        if self.is_terminal:
            raise ValueError(f"order {self.order_id} is already {self.status}")
        self.cancel_requested_at = at


@dataclass
class Execution:
    exec_id: str
    broker: str
    symbol: str
    side: str                                       # BUY / SELL (IBKR BOT / SLD normalised)
    quantity: float
    price: float
    executed_at: datetime
    broker_order_id: Optional[int] = None
    perm_id: Optional[int] = None
    order_id: Optional[int] = None                  # internal order; None = external / unexplained
    account: Optional[str] = None
    commission: Optional[float] = None
    commission_currency: Optional[str] = None
    commission_booked: bool = False
    booked: bool = False                            # fill booked into transaction / position / cash
    received_at: Optional[datetime] = None
    id: Optional[int] = None
    notes: str = field(default="")

    def __post_init__(self):
        side = {"BOT": "BUY", "SLD": "SELL"}.get(str(self.side).upper(), str(self.side).upper())
        if side not in ("BUY", "SELL"):
            raise ValueError(f"unknown execution side {self.side!r}")
        self.side = side
        if not self.quantity > 0 or not self.price > 0:
            raise ValueError("an execution needs a positive quantity and price")

    @property
    def signed_quantity(self) -> float:
        return self.quantity if self.side == "BUY" else -self.quantity
