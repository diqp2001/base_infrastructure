"""
LiveClock — paces the Misbuffet engine loop on the wall clock for live / paper trading.

The engine steps through naive EXCHANGE times (e.g. 10:10 New York = the decision that sees the 10:00 bar). In a
backtest it runs them as fast as it can; with ``config.live_clock`` set it asks the clock before each step:

    RUN   the wall clock has reached the step time + grace (the bar has closed and IBKR has published it)
    SKIP  the step was reached too late (more than ``max_lag_seconds`` after it was due, e.g. a long retraining or
          a start in the middle of a session): deciding on it would trade on an old bar, so it is not run
    STOP  a stop was requested (request_stop, Ctrl+C handler, end of session): the engine leaves the loop

The clock never runs a step early: the frontier of a decision must be in the past.
"""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Callable, List, Optional
from zoneinfo import ZoneInfo

RUN, SKIP, STOP = "run", "skip", "stop"


class LiveClock:

    def __init__(self, timezone_name: str = "America/New_York", grace_seconds: float = 20.0,
                 max_lag_seconds: float = 300.0, now: Optional[Callable[[], datetime]] = None,
                 sleep: Callable[[float], None] = time.sleep, poll_seconds: float = 5.0, logger=None):
        self.tz = ZoneInfo(timezone_name)
        self.grace = timedelta(seconds=grace_seconds)
        self.max_lag = timedelta(seconds=max_lag_seconds)
        self._now = now or (lambda: datetime.now(timezone.utc))
        self._sleep = sleep
        self.poll_seconds = poll_seconds
        self._stop = threading.Event()
        self.stop_reason: Optional[str] = None
        self.skipped: List[datetime] = []
        self.logger = logger or logging.getLogger("live_clock")

    def request_stop(self, reason: str = "stop requested") -> None:
        self.stop_reason = self.stop_reason or reason
        self._stop.set()

    @property
    def stopped(self) -> bool:
        return self._stop.is_set()

    def exchange_now(self) -> datetime:
        """Current exchange time, naive (same convention as the engine clock)."""
        return self._now().astimezone(self.tz).replace(tzinfo=None)

    def due(self, step_time: datetime) -> datetime:
        """Wall-clock instant (aware) at which the step may run."""
        return step_time.replace(tzinfo=self.tz) + self.grace

    def wait_for(self, step_time: datetime) -> str:
        due = self.due(step_time)
        while not self._stop.is_set():
            remaining = (due - self._now()).total_seconds()
            if remaining <= 0:
                break
            self._sleep(min(remaining, self.poll_seconds))
        if self._stop.is_set():
            return STOP
        lag = self._now() - due
        if lag > self.max_lag:
            self.skipped.append(step_time)
            self.logger.warning(f"live clock: step {step_time} skipped, reached {lag.total_seconds():.0f}s late "
                                f"(max {self.max_lag.total_seconds():.0f}s)")
            return SKIP
        return RUN
