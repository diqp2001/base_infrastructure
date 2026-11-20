"""
The window of ONE backtest: start, end, starting capital (owner 2026-11-19: a strategy runs over any window; the
window belongs to the backtest - strategy_experiments - not to the strategy).

* ``default_window(config)``   the window a project's config states (the launch form's default);
* ``apply_window(config, w)``  writes the window over a project's config, in place:
    - backtest_start / backtest_end take the dates of the window at the project's own time of day (a daily project
      decides at 16:00, an intraday one from 09:40);
    - initial_capital and Portfolio.initial_cash take the capital;
    - price_history_start keeps the project's lead before the start (history for the features' warm-up and the
      first training): moved earlier when the window starts earlier, never later than the project's own.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Dict, Optional

import pandas as pd


@dataclass(frozen=True)
class BacktestWindow:
    start: date
    end: date
    initial_capital: float

    def __post_init__(self):
        if self.end <= self.start:
            raise ValueError(f"the backtest end {self.end} must be after its start {self.start}")
        if not self.initial_capital or float(self.initial_capital) <= 0:
            raise ValueError("the starting capital must be positive")

    @classmethod
    def parse(cls, start, end, initial_capital) -> "BacktestWindow":
        """From form text ('2026-06-01', '1000000')."""
        try:                                            # strictly YYYY-MM-DD (what a date field sends)
            s, e = date.fromisoformat(str(start).strip()[:10]), date.fromisoformat(str(end).strip()[:10])
        except (TypeError, ValueError):
            raise ValueError(f"backtest dates must be dates (YYYY-MM-DD), got {start!r} .. {end!r}")
        try:
            capital = float(str(initial_capital).replace(",", "").replace("_", ""))
        except (TypeError, ValueError):
            raise ValueError(f"the starting capital must be a number, got {initial_capital!r}")
        return cls(s, e, capital)

    def label(self) -> str:
        return f"{self.start} .. {self.end}"


def _time_of_day(value: Any, default: str) -> str:
    text = str(value or "")
    return text[11:19] if len(text) >= 19 else default


def default_window(config: Dict[str, Any]) -> Optional[BacktestWindow]:
    """The window the project's config states (None when it states none)."""
    if not config.get("backtest_start") or not config.get("backtest_end"):
        return None
    try:
        return BacktestWindow(pd.Timestamp(config["backtest_start"]).date(), pd.Timestamp(config["backtest_end"]).date(),
                              float(config.get("initial_capital") or 100_000))
    except ValueError:
        return None


def history_start(config: Dict[str, Any], window: BacktestWindow) -> Optional[str]:
    """price_history_start for the window: the project's lead before its start, kept (never later than its own)."""
    own = config.get("price_history_start")
    base_start = config.get("backtest_start")
    if not own or not base_start:
        return own
    lead = pd.Timestamp(base_start).normalize() - pd.Timestamp(own).normalize()
    wanted = (pd.Timestamp(window.start) - lead).date()
    return min(pd.Timestamp(own).date(), wanted).isoformat()


def apply_window(config: Dict[str, Any], window: Optional[BacktestWindow]) -> Dict[str, Any]:
    if window is None:
        return config
    history = history_start(config, window)
    config["backtest_start"] = f"{window.start.isoformat()} {_time_of_day(config.get('backtest_start'), '16:00:00')}"
    config["backtest_end"] = f"{window.end.isoformat()} {_time_of_day(config.get('backtest_end'), '16:00:00')}"
    if history:
        config["price_history_start"] = history
    capital = float(window.initial_capital)
    config["initial_capital"] = int(capital) if capital.is_integer() else capital
    if isinstance(config.get("Portfolio"), dict):
        config["Portfolio"] = {**config["Portfolio"], "initial_cash": config["initial_capital"]}
    return config


def as_datetime(d: date) -> datetime:
    return datetime(d.year, d.month, d.day)


def window_of(experiment) -> Optional[BacktestWindow]:
    """The window recorded on a backtest (None for the backtests recorded before windows existed)."""
    if not getattr(experiment, "backtest_start", None) or not getattr(experiment, "backtest_end", None):
        return None
    return BacktestWindow(pd.Timestamp(experiment.backtest_start).date(), pd.Timestamp(experiment.backtest_end).date(),
                          float(experiment.initial_capital))

