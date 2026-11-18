"""
Cross-sectional decile portfolios of a model score - reusable research service (any model, any universe).

At a rebalance date T:
  assign_deciles(scores)       rank ascending by (score, symbol) - ties broken by the symbol, deterministic -
                               decile = floor(position x n / N) + 1: D1 = the lowest scores, Dn the highest, sizes
                               differing by at most one
  decile_weights(...)          equal weight inside each decile (other schemes: configuration names reserved)
held T -> T+1 (the next rebalance), then:
  decile_return                sum of weight x the member's return T -> T+1 (a member without both closes is left
                               out and the rest re-weighted - reported in ``missing``)
  turnover                     one-way turnover 1/2 sum |w_new - w_old| (a first formation: 0.5 x the gross)
  cost                         traded notional sum |w_new - w_old| x transaction_cost_bps / 10 000
  long-short                   R(Dn) - R(D1) per period (gross and net of both legs' costs)
Series: cumulative = prod(1 + R) - 1; statistics with stm_metrics at ``periods_per_year`` (12 for monthly);
monotonicity: Spearman correlation between decile and its average return, the monthly rank IC (Spearman between
decile and return of each period, averaged) and the average Dn - D1 spread.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.spatio_temporal_momentum import stm_metrics

EQUAL_WEIGHT = "equal_weight"
WEIGHTINGS = (EQUAL_WEIGHT, "market_cap_weight", "volatility_weight", "model_score_weight")


@dataclass(frozen=True)
class DecileConfig:
    n_deciles: int = 10
    weighting: str = EQUAL_WEIGHT
    transaction_cost_bps: float = 0.0
    periods_per_year: int = 12
    sector_neutral: bool = False            # reserved: ranking inside each sector (not implemented in version 1)

    def __post_init__(self):
        if self.weighting not in WEIGHTINGS:
            raise ValueError(f"weighting must be one of {WEIGHTINGS}")
        if self.weighting != EQUAL_WEIGHT:
            raise NotImplementedError(f"{self.weighting}: only equal_weight is implemented (version 1)")
        if self.sector_neutral:
            raise NotImplementedError("sector-neutral deciles are not implemented (version 1)")
        if self.n_deciles < 2:
            raise ValueError("at least two deciles")


def assign_deciles(scores: Mapping[str, float], n: int = 10) -> pd.DataFrame:
    """One row per scored symbol: score, rank (1 = lowest), percentile (rank / N), decile (1 = lowest)."""
    items = sorted(((float(v), s) for s, v in scores.items() if v is not None and np.isfinite(v)))
    N = len(items)
    rows = []
    for i, (v, s) in enumerate(items):
        rows.append({"symbol": s, "score": v, "rank": i + 1, "percentile": (i + 1) / N,
                     "decile": min(n, int(math.floor(i * n / N)) + 1)})
    return pd.DataFrame(rows, columns=["symbol", "score", "rank", "percentile", "decile"])


def decile_weights(assignment: pd.DataFrame, config: DecileConfig) -> Dict[int, Dict[str, float]]:
    """{decile: {symbol: weight}} - equal weight inside each decile."""
    out: Dict[int, Dict[str, float]] = {}
    for d, group in assignment.groupby("decile"):
        members = sorted(group["symbol"])
        out[int(d)] = {s: 1.0 / len(members) for s in members}
    return out


def turnover(previous: Mapping[str, float], new: Mapping[str, float]) -> float:
    """One-way turnover: half the absolute weight change (a portfolio replaced entirely = 1)."""
    names = set(previous) | set(new)
    return 0.5 * sum(abs(new.get(s, 0.0) - previous.get(s, 0.0)) for s in names)


def portfolio_return(weights: Mapping[str, float], returns: Mapping[str, float]):
    """(return, members without a return) - the members with a return re-weighted to sum to the same total."""
    held = {s: w for s, w in weights.items() if returns.get(s) is not None and np.isfinite(returns[s])}
    missing = sorted(set(weights) - set(held))
    total = sum(held.values())
    if not held or total == 0:
        return float("nan"), missing
    scale = sum(weights.values()) / total
    return float(sum(w * scale * returns[s] for s, w in held.items())), missing


@dataclass
class DecilePeriod:
    """One rebalance and its holding period."""
    rebalance: pd.Timestamp
    end: Optional[pd.Timestamp]
    assignment: pd.DataFrame
    weights: Dict[int, Dict[str, float]]
    returns: Dict[str, float] = field(default_factory=dict)          # member returns rebalance -> end
    gross: Dict[int, float] = field(default_factory=dict)
    net: Dict[int, float] = field(default_factory=dict)
    turnover: Dict[int, float] = field(default_factory=dict)
    missing: Dict[int, List[str]] = field(default_factory=dict)

    @property
    def settled(self) -> bool:
        return self.end is not None and bool(self.gross)


class DecileResearch:
    """Decile portfolios rebalanced period after period (the previous weights carry the turnover)."""

    def __init__(self, config: DecileConfig = DecileConfig()):
        self.config = config
        self.periods: List[DecilePeriod] = []
        self._previous: Dict[int, Dict[str, float]] = {}

    def form(self, rebalance, scores: Mapping[str, float]) -> DecilePeriod:
        assignment = assign_deciles(scores, self.config.n_deciles)
        weights = decile_weights(assignment, self.config)
        period = DecilePeriod(pd.Timestamp(rebalance), None, assignment, weights)
        for d in range(1, self.config.n_deciles + 1):
            period.turnover[d] = turnover(self._previous.get(d, {}), weights.get(d, {}))
        self._previous = weights
        self.periods.append(period)
        return period

    def settle(self, period: DecilePeriod, end, returns: Mapping[str, float]) -> None:
        period.end = pd.Timestamp(end)
        period.returns = dict(returns)
        bps = self.config.transaction_cost_bps / 10_000.0
        for d, w in period.weights.items():
            r, missing = portfolio_return(w, returns)
            period.gross[d] = r
            period.net[d] = r - 2.0 * period.turnover[d] * bps        # traded notional = 2 x one-way turnover
            period.missing[d] = missing

    # -- series --
    def returns_frame(self, kind: str = "gross") -> pd.DataFrame:
        """Holding-period returns, one row per settled period (indexed by its end), columns D1..Dn and LS (Dn - D1)."""
        n = self.config.n_deciles
        rows = {}
        for p in self.periods:
            if not p.settled:
                continue
            values = p.gross if kind == "gross" else p.net
            row = {f"D{d}": values.get(d, float("nan")) for d in range(1, n + 1)}
            row["LS"] = row[f"D{n}"] - row["D1"]
            rows[p.end] = row
        return pd.DataFrame.from_dict(rows, orient="index").sort_index()

    def turnover_frame(self) -> pd.DataFrame:
        n = self.config.n_deciles
        return pd.DataFrame.from_dict({p.rebalance: {f"D{d}": p.turnover.get(d, float("nan"))
                                                     for d in range(1, n + 1)} for p in self.periods},
                                      orient="index").sort_index()


def cumulative(returns: pd.DataFrame) -> pd.DataFrame:
    """prod(1 + R) - 1 per column (a missing period leaves the series unchanged)."""
    return (1.0 + returns.fillna(0.0)).cumprod() - 1.0


def statistics(returns: pd.Series, periods_per_year: int = 12, turnover: Optional[pd.Series] = None) -> Dict[str, float]:
    r = returns.dropna().to_numpy(dtype=float)
    if not len(r):
        return {"periods": 0}
    vol = float(np.std(r, ddof=1) * math.sqrt(periods_per_year)) if len(r) > 1 else float("nan")
    out = {
        "periods": int(len(r)),
        "cumulative_return": float(np.prod(1.0 + r) - 1.0),
        "annualized_return": stm_metrics.annual_return(r, periods_per_year),
        "annualized_volatility": vol,
        "sharpe_ratio": stm_metrics.sharpe_ratio(r, periods_per_year),
        "max_drawdown": stm_metrics.max_drawdown(r),
        "calmar_ratio": stm_metrics.calmar_ratio(r, periods_per_year),
        "win_rate": float((r > 0).mean()),
        "average_return": float(r.mean()),
        "median_return": float(np.median(r)),
        "best_period": float(r.max()),
        "worst_period": float(r.min()),
    }
    if turnover is not None:
        out["average_turnover"] = float(turnover.dropna().mean()) if turnover.notna().any() else float("nan")
    return out


def _spearman(x: Sequence[float], y: Sequence[float]) -> float:
    x, y = pd.Series(list(x), dtype=float), pd.Series(list(y), dtype=float)
    keep = x.notna() & y.notna()
    if keep.sum() < 3:
        return float("nan")
    return float(x[keep].rank().corr(y[keep].rank()))


def monotonicity(returns: pd.DataFrame, n: int = 10) -> Dict[str, float]:
    """Is the score ordered with the next period's return? Spearman(decile, average return), the average per-period
    Spearman (rank IC of the deciles) and the average Dn - D1 spread."""
    cols = [f"D{d}" for d in range(1, n + 1)]
    means = returns[cols].mean()
    per_period = [_spearman(range(1, n + 1), returns.loc[t, cols]) for t in returns.index]
    per_period = [v for v in per_period if np.isfinite(v)]
    return {
        "spearman_decile_vs_average_return": _spearman(range(1, n + 1), means),
        "spearman_decile_vs_median_return": _spearman(range(1, n + 1), returns[cols].median()),
        "average_period_rank_ic": float(np.mean(per_period)) if per_period else float("nan"),
        "average_spread": float(returns["LS"].mean()) if "LS" in returns else float("nan"),
        "average_return_by_decile": {c: float(means[c]) for c in cols},
        "median_return_by_decile": {c: float(returns[c].median()) for c in cols},
    }
