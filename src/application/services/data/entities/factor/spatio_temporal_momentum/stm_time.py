"""
Time keys of the Spatio-Temporal Momentum pipeline: one row per SESSION (daily, `bar_minutes` None — the
original projects) or one row per INTRADAY BAR (`bar_minutes` = 10 for 10-minute bars).

    bar_key(ts, None) -> the session date (00:00)        bar_key(ts, 10) -> ts floored to its 10-minute bar
    next_key(ts, m)   -> exclusive end of that key         periods_per_year(m) -> 252 or 252 x bars per session
"""

from typing import Optional

import pandas as pd

SESSION_MINUTES = 390            # US regular session 09:30-16:00


def _naive(ts) -> pd.Timestamp:
    ts = pd.Timestamp(ts)
    return ts.tz_localize(None) if ts.tzinfo is not None else ts


def bar_key(ts, bar_minutes: Optional[int]) -> pd.Timestamp:
    ts = _naive(ts)
    return ts.normalize() if not bar_minutes else ts.floor(f"{int(bar_minutes)}min")


def next_key(ts, bar_minutes: Optional[int]) -> pd.Timestamp:
    key = bar_key(ts, bar_minutes)
    return key + (pd.Timedelta(days=1) if not bar_minutes else pd.Timedelta(minutes=int(bar_minutes)))


def bars_per_session(bar_minutes: Optional[int]) -> int:
    return 1 if not bar_minutes else int(round(SESSION_MINUTES / int(bar_minutes)))


def periods_per_year(bar_minutes: Optional[int]) -> int:
    return 252 * bars_per_session(bar_minutes)


def frequency(bar_minutes: Optional[int]) -> str:
    """Factor.FREQUENCIES key of the rows: '1d' or e.g. '10m'."""
    return "1d" if not bar_minutes else f"{int(bar_minutes)}m"
