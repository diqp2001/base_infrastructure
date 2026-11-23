"""
Probability quintiles — does a class probability RANK the realised future performance? (pure pandas, no I/O)

For one class probability P(class k), at each prediction date T separately (cross-sectional, never across dates):
  1. the stocks with a probability and a forward return at T;
  2. ranked by P(class k) (ties in asset-id order) and cut into n equal-count groups, the rule of
     research/statistics.quantile_portfolios: Q1 = lowest probability .. Qn = highest;
  3. each group's realised forward return T -> T + horizon: mean (the equal-weight group return), median, count and
     the hit rate (share of the group whose TRUE class is k).
Over time: the per-date group returns form one series per quintile; the cumulative return compounds them on
NON-OVERLAPPING dates (every ``horizon``-th evaluation date, so a ``horizon``-bar return is never compounded twice);
the correlation matrix of the quintile series uses research/statistics.correlation_matrix (pairwise, Pearson).

A probability quintile is neither the true class (the realised return class) nor the predicted class (argmax).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from src.application.services.research.statistics import correlation_matrix

MIN_CORRELATION_OBS = 3


@dataclass
class ProbabilityQuintileAnalysis:
    target_class: int                         # k of P(class k)
    n_quantiles: int
    horizon: int
    assignments: pd.DataFrame                 # date, asset, probability, quintile (1..n), forward_return, true_class
    mean_returns: pd.DataFrame                # date x Q1..Qn (equal-weight group return), plus 'Qn - Q1'
    median_returns: pd.DataFrame              # date x Q1..Qn
    counts: pd.DataFrame                      # date x Q1..Qn
    hit_rates: pd.DataFrame                   # date x Q1..Qn: share of the group whose true class is k
    cumulative: pd.DataFrame                  # compounded on non-overlapping dates, Q1..Qn and 'Qn - Q1'
    correlation: pd.DataFrame                 # Qi x Qj of the per-date group returns
    correlation_counts: pd.DataFrame
    summary: pd.DataFrame                     # per quintile: observations, dates, mean / median return, hit rate ...
    monotonicity: Optional[float]             # Spearman rank correlation of quintile number vs mean return
    notes: List[str] = field(default_factory=list)

    @property
    def labels(self) -> List[str]:
        return [f"Q{i + 1}" for i in range(self.n_quantiles)]


def assign_probability_quintiles(frame: pd.DataFrame, probability: str, n_quantiles: int = 5) -> pd.Series:
    """quintile 1..n of ``probability`` per date (NaN where the probability or the forward return is missing, or
    the date has fewer than n usable stocks). Uses only the rows of each date."""
    out = pd.Series(np.nan, index=frame.index)
    usable = frame[probability].notna() & frame["forward_return"].notna() \
        & np.isfinite(frame[probability].astype(float)) & np.isfinite(frame["forward_return"].astype(float))
    for _, g in frame[usable].sort_values(["date", "asset"], kind="mergesort").groupby("date", sort=False):
        if len(g) < n_quantiles:
            continue
        bucket = pd.qcut(g[probability].rank(method="first"), n_quantiles, labels=False)
        out.loc[bucket.index] = bucket.astype(float) + 1
    return out


def _non_overlapping(index: pd.DatetimeIndex, horizon: int) -> pd.DatetimeIndex:
    return index[::max(int(horizon), 1)]


def compound(returns: pd.DataFrame, horizon: int = 1) -> pd.DataFrame:
    """Cumulative return of each column: prod(1 + r) - 1 over the non-overlapping dates (NaN periods skipped)."""
    r = returns.loc[_non_overlapping(returns.index, horizon)]
    return (1.0 + r.fillna(0.0)).cumprod() - 1.0


def analyse_probability(frame: pd.DataFrame, target_class: int, n_quantiles: int = 5, horizon: int = 1
                        ) -> ProbabilityQuintileAnalysis:
    """``frame``: the observation table (date, asset, forward_return, true_class, p_<k>)."""
    col = f"p_{target_class}"
    labels = [f"Q{i + 1}" for i in range(n_quantiles)]
    spread = f"Q{n_quantiles} - Q1"
    work = frame[["date", "asset", col, "forward_return", "true_class"]].copy()
    work = work.rename(columns={col: "probability"})
    work["quintile"] = assign_probability_quintiles(frame.rename(columns={col: "probability"}), "probability",
                                                    n_quantiles)
    assigned = work.dropna(subset=["quintile"])
    notes = []
    if assigned.empty:
        empty = pd.DataFrame(columns=labels)
        return ProbabilityQuintileAnalysis(target_class, n_quantiles, horizon, work, empty, empty, empty, empty,
                                           empty, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), None,
                                           ["no date with enough stocks having a probability and a forward return"])
    g = assigned.groupby(["date", "quintile"])

    def wide(series: pd.Series) -> pd.DataFrame:
        w = series.unstack("quintile").reindex(columns=[float(i + 1) for i in range(n_quantiles)])
        w.columns = labels
        return w.sort_index()

    means = wide(g["forward_return"].mean())
    medians = wide(g["forward_return"].median())
    counts = wide(g["forward_return"].size()).fillna(0).astype(int)
    hits = wide(g["true_class"].apply(lambda s: float((s.dropna() == target_class).mean()) if s.notna().any()
                                      else np.nan))
    means_spread = means.copy()
    means_spread[spread] = means[labels[-1]] - means[labels[0]]
    coef, ncount, _ = correlation_matrix(means[labels], min_obs=MIN_CORRELATION_OBS)
    per_q = assigned.groupby("quintile")
    summary = pd.DataFrame({
        "observations": per_q.size().reindex([float(i + 1) for i in range(n_quantiles)]).to_numpy(),
        "dates": [int(means[q].notna().sum()) for q in labels],
        "mean_probability": per_q["probability"].mean().reindex([float(i + 1) for i in range(n_quantiles)]).to_numpy(),
        "mean_forward_return": [float(means[q].mean()) for q in labels],          # mean of the per-date returns
        "median_forward_return": per_q["forward_return"].median().reindex(       # over all the group's stocks
            [float(i + 1) for i in range(n_quantiles)]).to_numpy(),
        "return_std": [float(means[q].std(ddof=1)) if means[q].notna().sum() > 1 else np.nan for q in labels],
        "t_stat": [_t_stat(means[q]) for q in labels],
        "hit_rate": [float(hits[q].mean()) for q in labels],
        "cumulative_return": [float(compound(means[[q]], horizon)[q].iloc[-1]) for q in labels],
    }, index=labels)
    mean_by_q = summary["mean_forward_return"].to_numpy()
    mono = None
    if np.isfinite(mean_by_q).sum() >= 3:
        from scipy.stats import spearmanr
        ok = np.isfinite(mean_by_q)
        mono = float(spearmanr(np.arange(1, n_quantiles + 1)[ok], mean_by_q[ok]).correlation)
    if horizon > 1:
        notes.append(f"forward returns cover {horizon} bars and overlap from one date to the next: the cumulative "
                     f"returns compound every {horizon}-th date only")
    return ProbabilityQuintileAnalysis(
        target_class=target_class, n_quantiles=n_quantiles, horizon=horizon, assignments=work,
        mean_returns=means_spread, median_returns=medians, counts=counts, hit_rates=hits,
        cumulative=compound(means_spread, horizon), correlation=coef, correlation_counts=ncount, summary=summary,
        monotonicity=mono, notes=notes)


def _t_stat(series: pd.Series) -> float:
    s = series.dropna()
    if len(s) < 3 or s.std(ddof=1) == 0:
        return np.nan
    return float(s.mean() / (s.std(ddof=1) / np.sqrt(len(s))))


def analyse_all(frame: pd.DataFrame, classes: Sequence[int], n_quantiles: int = 5, horizon: int = 1
                ) -> Dict[int, ProbabilityQuintileAnalysis]:
    return {int(k): analyse_probability(frame, int(k), n_quantiles, horizon) for k in classes}
