"""
Trading calendar of raw bars (US exchanges, exchange-local times as IBKR stamps them).

`bar_is_current` decides whether the latest CLOSED bar stored for a series may stand for the value at a
decision time, or whether a newer bar should exist (the caller then fetches it, and a bar that still does
not exist is missing data — never a frozen price):

  bars of a day or longer   no trading day may be skipped between the bar and the decision
                            (Friday's daily bar on Monday: current; on Tuesday: Monday's bar is due)
  intraday bars             once the decision is past the first bar of its trading day
                            (session open + one bar, capped at the session close), the bar must come from
                            that day and have closed at most one bar before the decision; before that, the
                            last bar of the previous trading day is current

Example (8h bars, stamped 09:30 and 12:00, decision 16:00): the bar due is that day's 09:30 bar; the
previous day's 12:00 bar is stale and triggers a fetch.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, time, timedelta
from functools import lru_cache
from typing import FrozenSet

from dateutil.easter import easter

SESSION_OPEN = time(9, 30)
SESSION_CLOSE = time(16, 0)
DAY_SECONDS = 86400


# Unscheduled full-day closures (not derivable from rules). Kept in step with pandas_market_calendars' NYSE
# calendar by tests/unit/domain/test_bar_calendar.py; add new ones there and here. Early closes (13:00) are not
# modelled: a half day counts as a full session.
SPECIAL_CLOSURES = frozenset({
    date(2001, 9, 11), date(2001, 9, 12), date(2001, 9, 13), date(2001, 9, 14),   # September 11
    date(2004, 6, 11),                                                            # President Reagan mourning
    date(2007, 1, 2),                                                             # President Ford mourning
    date(2012, 10, 29), date(2012, 10, 30),                                       # Hurricane Sandy
    date(2018, 12, 5),                                                            # President G.H.W. Bush mourning
    date(2025, 1, 9),                                                             # President Carter mourning
})


@lru_cache(maxsize=None)
def us_market_holidays(year: int) -> FrozenSet[date]:
    """NYSE full-day holidays of `year`."""
    def observed(d):
        if d.weekday() == 5:
            return d - timedelta(days=1)
        if d.weekday() == 6:
            return d + timedelta(days=1)
        return d

    def nth_weekday(month, n, weekday):
        first = date(year, month, 1)
        return first + timedelta(days=(weekday - first.weekday()) % 7) + timedelta(weeks=n - 1)

    def last_weekday(month, weekday):
        last_day = date(year, month, calendar.monthrange(year, month)[1])
        return last_day - timedelta(days=(last_day.weekday() - weekday) % 7)

    days = {
        observed(date(year, 1, 1)),                 # New Year's Day
        nth_weekday(1, 3, 0),                       # Martin Luther King Jr. Day
        nth_weekday(2, 3, 0),                       # Presidents' Day
        easter(year) - timedelta(days=2),           # Good Friday
        last_weekday(5, 0),                         # Memorial Day
        observed(date(year, 7, 4)),                 # Independence Day
        nth_weekday(9, 1, 0),                       # Labor Day
        nth_weekday(11, 4, 3),                      # Thanksgiving
        observed(date(year, 12, 25)),               # Christmas
    }
    if year >= 2022:
        days.add(observed(date(year, 6, 19)))       # Juneteenth
    days |= {d for d in SPECIAL_CLOSURES if d.year == year}
    return frozenset(days)


def is_trading_day(d: date) -> bool:
    return d.weekday() < 5 and d not in us_market_holidays(d.year)


def trading_days_between(start: date, end: date) -> int:
    """Trading days strictly between two dates."""
    d, n = start + timedelta(days=1), 0
    while d < end:
        n += is_trading_day(d)
        d += timedelta(days=1)
    return n


def previous_trading_day(d: date) -> date:
    d -= timedelta(days=1)
    while not is_trading_day(d):
        d -= timedelta(days=1)
    return d


def bar_is_current(bar_start: datetime, bar_close: datetime, target: datetime, bar_seconds: int) -> bool:
    """True when no newer bar of the series should have closed by `target` (see module docstring)."""
    if bar_seconds >= DAY_SECONDS:
        allowed = max(0, round(bar_seconds / DAY_SECONDS) - 1)      # daily 0, weekly 6 calendar -> ~4-5 trading
        return trading_days_between(bar_start.date(), target.date()) <= allowed
    day = target.date()
    first_close = min(datetime.combine(day, SESSION_OPEN) + timedelta(seconds=bar_seconds),
                      datetime.combine(day, SESSION_CLOSE))
    if is_trading_day(day) and target >= first_close:
        return bar_start.date() == day and (target - bar_close).total_seconds() <= bar_seconds
    # before the day's first bar has closed (or on a non-trading day): the previous trading day's bars
    return bar_start.date() >= previous_trading_day(day)
