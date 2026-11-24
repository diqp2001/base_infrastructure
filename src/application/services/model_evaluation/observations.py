"""
The classifier observation table (see ClassifierObservationSourcePort) — checks and the label rules shared by the
adapters. Pure pandas, no I/O.

Temporal rules enforced here:
* the probabilities, the predicted class and the probability quintiles of date T use only the row's own date T
  (every cross-sectional operation groups by date; nothing is ranked across dates);
* the true class and the forward return come from the period AFTER T (computed by the adapters from returns stamped
  at T for the period T -> T + horizon);
* a run's observations start at its ``evaluable_from`` date (its training labels cannot overlap the forward period).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd

REQUIRED = ("date", "asset", "run_id", "true_class", "predicted_class", "forward_return")


@dataclass
class ObservationResult:
    """What an observation source returns: the table, the forward-return horizon (bars) used and its notes."""
    frame: pd.DataFrame
    horizon: int
    notes: List[str] = field(default_factory=list)


def probability_column(k: int) -> str:
    return f"p_{k}"


def probability_columns(classes: Sequence[int]) -> List[str]:
    return [probability_column(k) for k in classes]


def validate(frame: pd.DataFrame, classes: Sequence[int], score_only: bool = False) -> pd.DataFrame:
    """Columns present, one row per (date, asset), probabilities in [0, 1] summing to 1 (tolerance 1e-6) where all
    are known (a score-only model has a ``score`` column instead). Returns the frame sorted by (date, asset)."""
    needed = list(REQUIRED) + (["score"] if score_only else probability_columns(classes))
    missing = [c for c in needed if c not in frame.columns]
    if missing:
        raise ValueError(f"observation table without columns {missing}")
    if frame.duplicated(["date", "asset"]).any():
        dup = frame[frame.duplicated(["date", "asset"], keep=False)][["date", "asset"]].head(3).to_dict("records")
        raise ValueError(f"several observations for the same (date, asset), e.g. {dup}: runs mixed?")
    if score_only:
        out = frame.copy()
        out["date"] = pd.to_datetime(out["date"])
        return out.sort_values(["date", "asset"], kind="mergesort").reset_index(drop=True)
    p = frame[probability_columns(classes)].to_numpy(dtype=float)
    known = np.isfinite(p).all(axis=1)
    if known.any():
        if ((p[known] < -1e-9) | (p[known] > 1 + 1e-9)).any():
            raise ValueError("class probabilities outside [0, 1]")
        if (np.abs(p[known].sum(axis=1) - 1.0) > 1e-6).any():
            raise ValueError("class probabilities do not sum to 1")
    out = frame.copy()
    out["date"] = pd.to_datetime(out["date"])
    return out.sort_values(["date", "asset"], kind="mergesort").reset_index(drop=True)


def predicted_classes(probabilities: np.ndarray, classes: Sequence[int]) -> np.ndarray:
    """argmax of each row (the first class on a tie); NaN for a row without probabilities."""
    p = np.asarray(probabilities, dtype=float)
    out = np.full(len(p), np.nan)
    ok = np.isfinite(p).all(axis=1)
    out[ok] = np.asarray(classes, dtype=float)[np.argmax(p[ok], axis=1)]
    return out


def ordinal_quantile_labels(values: pd.Series, n: int) -> pd.Series:
    """Cross-section of ONE date -> class 1..n by the ordinal rule of the LGBM momentum trainer
    (_assign_quintile_labels): rank 0..N-1 (ties in the series' order), label = floor(rank / N x n) + 1."""
    v = values.dropna()
    if v.empty:
        return pd.Series(dtype=float)
    ranks = pd.Series(np.argsort(np.argsort(v.to_numpy(), kind="mergesort"), kind="mergesort"), index=v.index)
    return (np.floor(ranks / len(v) * n).astype(int) + 1).clip(1, n).astype(float)


def cross_sectional_classes(frame: pd.DataFrame, value: str, n: int) -> pd.Series:
    """Per date (never across dates), ``value`` -> class 1..n with ordinal_quantile_labels. Rows in (asset) order
    inside a date, so ties are broken by asset id."""
    out = pd.Series(np.nan, index=frame.index)
    for _, g in frame.sort_values(["date", "asset"], kind="mergesort").groupby("date", sort=False):
        labels = ordinal_quantile_labels(g[value], n)
        out.loc[labels.index] = labels
    return out


def median_split_classes(frame: pd.DataFrame, value: str) -> pd.Series:
    """Per date: 1 when ``value`` is above the date's cross-sectional median, else 0 (the CSM label rule,
    csm_features.build_dataset); NaN where the value is missing."""
    med = frame.groupby("date")[value].transform("median")
    out = (frame[value] > med).astype(float)
    return out.where(frame[value].notna())


def ranking_score(frame: pd.DataFrame, classes: Sequence[int], score_only: bool = False) -> pd.Series:
    """One number per observation that orders the stocks by the model's expected performance, known at T:
    the score (score models), P(best class) for a binary model, the expected class sum_k k x P(k) otherwise (the
    whole distribution, not only its argmax)."""
    if score_only:
        return frame["score"].astype(float)
    if len(classes) == 2:
        return frame[probability_column(classes[-1])].astype(float)
    p = frame[probability_columns(classes)].to_numpy(dtype=float)
    return pd.Series(p @ np.asarray(classes, dtype=float), index=frame.index)


def cross_sectional_views(frame: pd.DataFrame, classes: Sequence[int], score_only: bool = False,
                          n_quantiles: int = 5) -> dict:
    """The same two classifications for every model, per date (from the forward return and the ranking score):
    'binary'   true = forward return above the date's median, predicted = ranking score above the date's median;
    'quintile' true = per-date quintile of the forward return, predicted = per-date quintile of the ranking score.
    Returns {view: (true classes, predicted classes)} on the rows with a forward return and a score."""
    work = frame[["date", "asset", "forward_return"]].copy()
    work["ranking"] = ranking_score(frame, classes, score_only)
    work = work.dropna(subset=["forward_return", "ranking"])
    return {
        "binary": (median_split_classes(work, "forward_return"), median_split_classes(work, "ranking")),
        "quintile": (cross_sectional_classes(work, "forward_return", n_quantiles),
                     cross_sectional_classes(work, "ranking", n_quantiles)),
    }


def restrict_to_runs(frame: pd.DataFrame, runs: Iterable) -> pd.DataFrame:
    """Rows whose date is inside their run's evaluable window [evaluable_from or valid_from, valid_until]."""
    keep = pd.Series(False, index=frame.index)
    for run in runs:
        rows = frame["run_id"] == run.run_id
        start = run.evaluable_from or run.valid_from
        if start is not None:
            rows &= frame["date"] >= pd.Timestamp(start)
        if run.valid_until is not None:
            rows &= frame["date"] <= pd.Timestamp(run.valid_until)
        keep |= rows
    return frame[keep]


def run_in_force(dates: Sequence, runs: Sequence) -> List[Optional[int]]:
    """For each date, the run whose [valid_from, valid_until] contains it — the most recent valid_from when several
    do (a retraining replaces the previous model from its own date on)."""
    out = []
    for d in pd.to_datetime(list(dates)):
        best = None
        for r in runs:
            if r.valid_from is None or pd.Timestamp(r.valid_from) > d:
                continue
            if r.valid_until is not None and pd.Timestamp(r.valid_until) < d:
                continue
            if best is None or (pd.Timestamp(r.valid_from), r.run_id) > (pd.Timestamp(best.valid_from), best.run_id):
                best = r
        out.append(best.run_id if best is not None else None)
    return out
