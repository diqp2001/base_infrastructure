"""
A difference between the strategy's books and the broker, found by start-up / reconnect recovery (P.04), with how it
was resolved. Pure; no I/O.

kind       what was found (DiscrepancyKind)
key        what it is about (ticker, broker order id, exec id ...): one OPEN discrepancy per (kind, key)
blocking   True: no new order may be sent while it is open (position mismatch, external trade on a managed instrument,
           incomplete broker snapshot); False: recorded for audit only (an order closed during recovery ...)
resolution how it was closed — automatically ("matched on recovery ...") or by the owner (``resolve``)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class DiscrepancyKind(str, Enum):
    POSITION_MISMATCH = "position_mismatch"            # strategy quantity != broker quantity
    EXTERNAL_EXECUTION = "external_execution"          # an execution no internal order explains
    UNMANAGED_WORKING_ORDER = "unmanaged_working_order"  # a working broker order no internal order explains
    ORDER_NOT_FOUND = "order_not_found"                # INTENT / UNKNOWN order: no working order, no execution
    ORDER_CLOSED_ON_RECOVERY = "order_closed_on_recovery"  # open internal order no longer working at the broker
    INCOMPLETE_SNAPSHOT = "incomplete_snapshot"        # the broker did not confirm the end of a list / not connected
    CASH_DRIFT = "cash_drift"                          # broker vs book cash change above the threshold (P.04.04)


@dataclass
class Discrepancy:
    kind: DiscrepancyKind
    key: str
    detail: str
    detected_at: datetime
    blocking: bool
    broker: str = "IBKR"
    order_id: Optional[int] = None
    resolved_at: Optional[datetime] = None
    resolution: Optional[str] = None
    id: Optional[int] = None

    @property
    def is_open(self) -> bool:
        return self.resolved_at is None

    def resolve(self, resolution: str, at: datetime) -> None:
        if not resolution or not resolution.strip():
            raise ValueError("a resolution must say how the discrepancy was resolved")
        if not self.is_open:
            raise ValueError(f"discrepancy {self.id} is already resolved")
        self.resolution = resolution.strip()
        self.resolved_at = at
