"""
Status vocabulary and the per-section snapshot used by every dashboard response.

A Section holds the latest collected data plus *when* it was collected. Freshness is computed
at read time: data older than ``stale_after_seconds`` is reported as ``stale`` instead of its
last status, so cached data never makes a component look healthy.
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

HEALTHY = "healthy"
DEGRADED = "degraded"
DISCONNECTED = "disconnected"
ERROR = "error"
UNKNOWN = "unknown"
STALE = "stale"
STATUSES = (HEALTHY, DEGRADED, DISCONNECTED, ERROR, UNKNOWN, STALE)
# severity for aggregation (higher is worse)
_SEVERITY = {HEALTHY: 0, UNKNOWN: 1, STALE: 2, DEGRADED: 3, DISCONNECTED: 4, ERROR: 5}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def iso(ts: Optional[datetime]) -> Optional[str]:
    if ts is None:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat(timespec="seconds")


def worst(*statuses: str) -> str:
    present = [s for s in statuses if s]
    return max(present, key=lambda s: _SEVERITY.get(s, 1)) if present else UNKNOWN


def make_view(name: str, status: str, data: Any, updated_at: Optional[datetime], stale_after: float,
              error: Optional[str] = None, now: Optional[datetime] = None) -> Dict[str, Any]:
    """Same envelope as Section.view for data kept elsewhere (e.g. the IBKR monitor)."""
    now = now or utcnow()
    age = (now - updated_at).total_seconds() if updated_at else None
    stale = age is not None and age > stale_after
    shown = status
    if stale and status not in (ERROR, DISCONNECTED):
        shown = STALE
    return {"section": name, "status": shown, "collected_status": status, "stale": bool(stale),
            "age_seconds": None if age is None else round(age, 1), "stale_after_seconds": stale_after,
            "updated_at": iso(updated_at), "last_success": iso(updated_at), "last_error_at": None,
            "error": error, "data": data}


@dataclass
class Section:
    name: str
    stale_after_seconds: float
    status: str = UNKNOWN
    data: Any = None
    error: Optional[str] = None
    updated_at: Optional[datetime] = None       # last collection attempt that produced data
    last_success: Optional[datetime] = None     # last collection without error
    last_error_at: Optional[datetime] = None
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def update(self, status: str, data: Any = None, error: Optional[str] = None,
               keep_data_on_error: bool = True) -> None:
        now = utcnow()
        with self._lock:
            self.status = status
            if error is None:
                self.data = data
                self.error = None
                self.updated_at = now
                self.last_success = now
            else:
                self.error = error
                self.last_error_at = now
                if data is not None or not keep_data_on_error:
                    self.data = data
                    self.updated_at = now

    def view(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        now = now or utcnow()
        with self._lock:
            age = (now - self.updated_at).total_seconds() if self.updated_at else None
            stale = age is not None and age > self.stale_after_seconds
            status = self.status
            if self.updated_at is None and self.error is None:
                status = UNKNOWN
            elif stale and status not in (ERROR, DISCONNECTED):
                status = STALE
            return {
                "section": self.name,
                "status": status,
                "collected_status": self.status,
                "stale": bool(stale),
                "age_seconds": None if age is None else round(age, 1),
                "stale_after_seconds": self.stale_after_seconds,
                "updated_at": iso(self.updated_at),
                "last_success": iso(self.last_success),
                "last_error_at": iso(self.last_error_at),
                "error": self.error,
                "data": self.data,
            }
