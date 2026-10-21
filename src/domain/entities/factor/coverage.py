"""
Historical data coverage (BI-029): which bars SHOULD be stored for a series over a window, which are, and the open
gaps between them. A successful download is not complete coverage — completeness is judged against the trading
calendar (`bar_calendar`), so exchange closures (weekends, holidays) are never reported as gaps.

Granularity: one expected unit per trading day.
  bars of a day or longer   the day's bar (matched by date: IBKR stamps daily bars by session date)
  intraday bars             at least one bar of that trading day; holes inside a day are not detected (IBKR's
                            intraday bar alignment is not modelled), a day without any bar is

Only days whose session has closed by `as_of` are expected: today's bar is not missing before 16:00.
No value is ever filled in — a gap stays a gap until data is stored (no forward-fill).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Iterable, List, Tuple

from src.domain.entities.factor.bar_calendar import SESSION_CLOSE, is_trading_day


@dataclass(frozen=True)
class Gap:
    first: date                  # first missing trading day
    last: date                   # last missing trading day (inclusive)
    days: int                    # missing trading days in the run

    def __str__(self) -> str:
        return f"{self.first}" if self.first == self.last else f"{self.first}..{self.last} ({self.days} days)"


@dataclass(frozen=True)
class CoverageReport:
    start: date
    end: date
    expected: Tuple[date, ...]           # trading days that should have data
    received: Tuple[date, ...]           # expected days that have data
    gaps: Tuple[Gap, ...]                # contiguous runs of missing trading days (closures do not split runs)
    unexpected: Tuple[date, ...] = ()    # stored on non-trading days (calendar or data problem: reported, kept)

    @property
    def missing(self) -> Tuple[date, ...]:
        received = set(self.received)
        return tuple(d for d in self.expected if d not in received)

    @property
    def completeness(self) -> float:
        return 1.0 if not self.expected else len(self.received) / len(self.expected)

    def is_complete(self, threshold: float = 1.0) -> bool:
        """Per instrument / strategy threshold (1.0 = every expected bar)."""
        return self.completeness >= threshold

    def summary(self) -> str:
        gaps = ", ".join(str(g) for g in self.gaps) or "none"
        return (f"{len(self.received)}/{len(self.expected)} trading days ({self.completeness:.1%}) "
                f"{self.start}..{self.end}; gaps: {gaps}")


def expected_days(start: date, end: date, as_of: datetime) -> List[date]:
    """Trading days in [start, end] whose session closed by `as_of`."""
    days, d = [], start
    while d <= end:
        if is_trading_day(d) and datetime.combine(d, SESSION_CLOSE) <= as_of:
            days.append(d)
        d += timedelta(days=1)
    return days


def coverage(stored: Iterable[datetime], start: date, end: date, as_of: datetime) -> CoverageReport:
    """Coverage of a series from the timestamps of its stored bars (see module docstring)."""
    expected = expected_days(start, end, as_of)
    stored_days = {(t.date() if isinstance(t, datetime) else t) for t in stored}
    stored_days = {d for d in stored_days if start <= d <= end}
    received = tuple(d for d in expected if d in stored_days)
    unexpected = tuple(sorted(d for d in stored_days if not is_trading_day(d)))
    gaps, run = [], []
    for d in expected:
        if d in stored_days:
            if run:
                gaps.append(Gap(run[0], run[-1], len(run)))
                run = []
        else:
            run.append(d)
    if run:
        gaps.append(Gap(run[0], run[-1], len(run)))
    return CoverageReport(start, end, tuple(expected), received, tuple(gaps), unexpected)
