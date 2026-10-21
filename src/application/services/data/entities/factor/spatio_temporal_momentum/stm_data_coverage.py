"""
Data coverage of an STM run: how many of the bars the strategy should have had were actually stored.

Expected bars come from the NYSE calendar (holidays and early closes included): one per session when
``bar_minutes`` is None, otherwise one per ``bar_minutes`` bar from the open to the close (bar START stamps,
exchange-local naive time, the way IBKR bars are stored). Two windows are measured:

    history  — from the history start to the first decision (what the first model was trained on)
    backtest — from the first to the last decision bar

Per asset: expected / present / coverage / missing bars, the longest run of consecutive missing bars,
first and last stored bar, stored bars outside the expected grid, and how many decisions scored the asset.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import bar_key

CALENDAR = "XNYS"

ASSET_COLUMNS = ["Backtest expected", "Backtest present", "Backtest coverage %", "Backtest missing",
                 "Longest gap (bars)", "History coverage %", "Decisions scored", "First bar", "Last bar",
                 "Off-grid bars"]


def expected_bars(start, end, bar_minutes: Optional[int]) -> pd.DatetimeIndex:
    """Bar keys the exchange was open for, start <= key <= end (both bar keys)."""
    import pandas_market_calendars as mcal
    start, end = bar_key(start, bar_minutes), bar_key(end, bar_minutes)
    if end < start:
        return pd.DatetimeIndex([])
    schedule = mcal.get_calendar(CALENDAR).schedule(start_date=start.normalize(), end_date=end.normalize())
    if not bar_minutes:
        keys = pd.DatetimeIndex(schedule.index).normalize()
    else:
        step = pd.Timedelta(minutes=int(bar_minutes))
        stamps: List[pd.Timestamp] = []
        for open_, close in zip(schedule["market_open"], schedule["market_close"]):
            o = pd.Timestamp(open_).tz_convert("America/New_York").tz_localize(None)
            c = pd.Timestamp(close).tz_convert("America/New_York").tz_localize(None)
            stamps.extend(pd.date_range(o, c - step, freq=step))
        keys = pd.DatetimeIndex(stamps)
    return keys[(keys >= start) & (keys <= end)]


def _longest_gap(present: np.ndarray) -> int:
    longest = run = 0
    for ok in present:
        run = 0 if ok else run + 1
        longest = max(longest, run)
    return longest


def _pct(n: int, d: int) -> float:
    return 100.0 * n / d if d else float("nan")


def data_coverage(closes: pd.DataFrame, universe: Iterable[str], decision_keys: List[pd.Timestamp],
                  scored: Dict[str, int], bar_minutes: Optional[int], history_start=None,
                  scored_per_decision: Optional[List[int]] = None) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """
    (summary, per-asset table, coverage % per session over both windows).

    ``closes``: date x ticker raw close panel (index = bar keys, before any alignment);
    ``decision_keys``: the bar key of every decision; ``scored``: ticker -> decisions that scored it;
    ``scored_per_decision``: number of assets scored at each decision.
    """
    closes = closes.copy()
    closes.index = pd.DatetimeIndex(closes.index)
    universe = list(dict.fromkeys(list(universe) + [c for c in closes.columns if c not in universe]))
    decisions = sorted(set(decision_keys))
    first, last = decisions[0], decisions[-1]
    start = bar_key(history_start if history_start is not None else
                    (closes.index.min() if len(closes) else first), bar_minutes)
    grid_bt = expected_bars(first, last, bar_minutes)
    grid_hist = expected_bars(start, first, bar_minutes)
    grid_hist = grid_hist[grid_hist < first]
    grid_all = grid_hist.append(grid_bt)

    rows = {}
    hist_present = 0
    present_all = pd.DataFrame(False, index=grid_all, columns=universe)
    for a in universe:
        series = closes[a].dropna() if a in closes else pd.Series(dtype=float, index=pd.DatetimeIndex([]))
        stored = series.index
        in_bt = grid_bt.isin(stored)
        in_hist = grid_hist.isin(stored)
        present_all[a] = grid_all.isin(stored)
        hist_present += int(in_hist.sum())
        window = stored[(stored >= start) & (stored <= last)]
        rows[a] = {
            "Backtest expected": len(grid_bt),
            "Backtest present": int(in_bt.sum()),
            "Backtest coverage %": _pct(int(in_bt.sum()), len(grid_bt)),
            "Backtest missing": int(len(grid_bt) - in_bt.sum()),
            "Longest gap (bars)": _longest_gap(in_bt),
            "History coverage %": _pct(int(in_hist.sum()), len(grid_hist)),
            "Decisions scored": int(scored.get(a, 0)),
            "First bar": str(stored.min()) if len(stored) else "none",
            "Last bar": str(stored.max()) if len(stored) else "none",
            "Off-grid bars": int((~window.isin(grid_all)).sum()),
        }
    per_asset = pd.DataFrame.from_dict(rows, orient="index")[ASSET_COLUMNS]
    per_asset = per_asset.sort_values(["Backtest coverage %", "History coverage %"], na_position="first")

    no_data = [a for a in universe if rows[a]["Backtest present"] == 0 and rows[a]["First bar"] == "none"]
    no_bt = [a for a in universe if rows[a]["Backtest present"] == 0 and a not in no_data]
    total_bt = len(grid_bt) * len(universe)
    total_hist = len(grid_hist) * len(universe)
    per_decision = list(scored_per_decision or [])
    summary: Dict[str, Any] = {
        "Bar": "1 session" if not bar_minutes else f"{int(bar_minutes)} minutes",
        "History window": f"{start} to {first} (excl.)",
        "Backtest window": f"{first} to {last}",
        "Universe (assets)": len(universe),
        "Expected bars per asset — history": len(grid_hist),
        "Expected bars per asset — backtest": len(grid_bt),
        "Coverage % — history": _pct(hist_present, total_hist),
        "Coverage % — backtest": _pct(int(per_asset["Backtest present"].sum()), total_bt),
        "Assets fully covered in backtest": int((per_asset["Backtest missing"] == 0).sum()),
        "Assets below 95% in backtest": int((per_asset["Backtest coverage %"] < 95).sum()),
        "Assets without any stored bar": ", ".join(no_data) or "none",
        "Assets without a backtest bar": ", ".join(no_bt) or "none",
        "Decisions": len(decision_keys),
    }
    if per_decision:
        summary["Assets scored per decision (min / mean / max)"] = (
            f"{min(per_decision)} / {np.mean(per_decision):.1f} / {max(per_decision)}")
        summary["Decisions without scores"] = int(sum(1 for n in per_decision if n == 0))
    summary_df = pd.DataFrame({"Value": pd.Series(summary, dtype=object)})

    sessions = present_all.groupby(present_all.index.normalize())
    by_session = sessions.apply(lambda f: 100.0 * f.to_numpy().mean()) if len(present_all) else pd.Series(dtype=float)
    by_session.index.name = "session"
    return summary_df, per_asset, by_session
