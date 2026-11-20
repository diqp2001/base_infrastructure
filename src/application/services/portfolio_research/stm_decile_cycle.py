"""
STMDecileTradingCycle - monthly cross-sectional deciles of the spatio-temporal momentum (STM) model, one engine step
at a time (the decile counterpart of STMTradingCycle). The Misbuffet algorithm calls ``step(t)`` every bar and sends
the returned weights to set_holdings.

Period bars: the model's rows are PERIOD-END closes - by default the month end (the last trading day of each month),
its target the next period's return (STMConfiguration.prediction_horizon = 1 row = 1 period) - the existing STM
target, configured. ``period`` is a pandas period alias ('D' every trading day, 'W' weeks, 'M' months) and
``every`` the number of periods between two rebalances (default: every month, as before).

At a step, with the daily closes KNOWN at t only (KnownClosesReader: a close dated D is known from D+1 00:00):
  when a period has completed since the last rebalance (``every`` periods), every close of the latest completed
  period is known and its last trading day T is the rebalance:
    1. the open month of every variant is settled: member returns from the previous T's close to this T's close;
    2. the members in force at T (membership.members_at) and their month-end close panel up to T;
    3. each model VARIANT (e.g. 'A' price features, 'B' + fundamentals) retrains / scores the members
       (STMConstituentScorer: the existing STM pipeline; closes up to T only) -> deciles (DecileResearch);
    4. the engine trades the ``traded`` variant's Dn - D1: +gross/2 split equally over Dn, -gross/2 over D1, every
       other held share to 0.
Every variant sees the same members, dates, target, deciles and weighting: a clean ablation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Callable, Dict, List, Mapping, Optional

import pandas as pd

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_constituent_scorer import (
    STMConstituentScorer,
)
from src.application.services.portfolio_research.decile_portfolios import DecileConfig, DecilePeriod, DecileResearch


PERIODS = {"days": "D", "weeks": "W", "months": "M"}           # Frequency unit -> pandas period alias
PERIODS_PER_YEAR = {"D": 252, "W": 52, "M": 12}


def period_end_panel(daily: pd.DataFrame, through: pd.Timestamp, period: str = "M") -> pd.DataFrame:
    """The close of each period's last trading day (rows: those dates), closes dated <= ``through`` only."""
    d = daily.loc[:through].dropna(how="all")
    if d.empty:
        return d
    last_days = d.index.to_series().groupby(d.index.to_period(period)).max()
    return d.loc[pd.DatetimeIndex(last_days.values)]


def month_end_panel(daily: pd.DataFrame, through: pd.Timestamp) -> pd.DataFrame:
    """The close of each month's last trading day (rows: those dates), closes dated <= ``through`` only."""
    return period_end_panel(daily, through, "M")


@dataclass
class DecileStepResult:
    time: pd.Timestamp
    rebalance: Optional[pd.Timestamp] = None
    weights: Dict[str, float] = field(default_factory=dict)     # the traded variant's Dn - D1 targets
    formed: Dict[str, DecilePeriod] = field(default_factory=dict)
    note: str = ""


@dataclass
class PredictionRecord:
    rebalance: pd.Timestamp
    variant: str
    symbol: str
    score: float
    rank: int
    percentile: float
    decile: int
    model_trained_at: Optional[pd.Timestamp]
    model_assets: int
    next_return: Optional[float] = None


class STMDecileTradingCycle:

    def __init__(self, membership, reader, variants: Mapping[str, STMConstituentScorer],
                 decile_config: DecileConfig, start: date, end: date, traded: str,
                 long_short_gross: float = 1.0, log: Optional[Callable[[str], None]] = None,
                 period: str = "M", every: int = 1):
        if traded not in variants:
            raise ValueError(f"the traded variant {traded!r} is not one of {list(variants)}")
        if period not in PERIODS_PER_YEAR:
            raise ValueError(f"period must be one of {sorted(PERIODS_PER_YEAR)}, got {period!r}")
        if int(every) < 1:
            raise ValueError(f"every must be >= 1 period, got {every!r}")
        self.period, self.every = period, int(every)
        self.membership = membership
        self.reader = reader
        self.variants = dict(variants)
        self.config = decile_config
        self.research = {name: DecileResearch(decile_config) for name in self.variants}
        self.start, self.end = start, end
        self.traded = traded
        self.long_short_gross = float(long_short_gross)
        self.log = log or (lambda m: None)
        self.predictions: List[PredictionRecord] = []
        self.skipped: Dict[pd.Timestamp, str] = {}
        self._last: Optional[pd.Timestamp] = None            # last rebalance date
        self._open: Dict[str, DecilePeriod] = {}

    # -- the step --
    def step(self, now) -> DecileStepResult:
        now = pd.Timestamp(now)
        result = DecileStepResult(time=now)
        daily = self.reader.closes(now)
        if daily.empty:
            result.note = "no close known yet"
            return result
        # the latest COMPLETED period (before now's period) with a known close; T = its last trading day
        completed = daily.index[daily.index.to_period(self.period) < now.to_period(self.period)]
        if len(completed) == 0:
            result.note = "no close of a completed period known"
            return result
        T = completed.max()
        if self._last is not None and T <= self._last:
            result.note = "rebalanced already this period"
            return result
        if (self._last is not None
                and T.to_period(self.period).ordinal - self._last.to_period(self.period).ordinal < self.every):
            result.note = f"next rebalance after {self.every} periods"
            return result
        if not (self.start <= T.date() <= self.end):
            result.note = f"{T.date()} outside the backtest window"
            return result
        self._settle(daily, T)
        self._last = T
        result.rebalance = T
        members = self.membership.members_at(T.date())
        panel = period_end_panel(daily[[s for s in members if s in daily.columns]], T, self.period)
        if T not in panel.index:
            result.note = f"{T.date()}: no period-end close panel"
            return result
        for name, scorer in self.variants.items():
            scores = scorer.score(panel, members, T)
            if len(scores.scores) < self.config.n_deciles:
                self.skipped[T] = f"{name}: {len(scores.scores)} scored members < {self.config.n_deciles} deciles"
                self.log(f"[STM-DECILE] {T.date()} {self.skipped[T]} ({scores.unscored})")
                continue
            period = self.research[name].form(T, scores.scores)
            self._open[name] = period
            result.formed[name] = period
            for row in period.assignment.itertuples(index=False):
                self.predictions.append(PredictionRecord(T, name, row.symbol, row.score, int(row.rank),
                                                         float(row.percentile), int(row.decile),
                                                         scores.trained_at, len(scores.model_assets)))
            self.log(f"[STM-DECILE] {T.date()} {name}: {len(scores.scores)} scored, "
                     f"{'retrained' if scores.retrained else 'model of ' + str(scores.trained_at.date())}")
        traded = result.formed.get(self.traded)
        if traded is not None:
            result.weights = self.long_short_weights(traded)
        result.note = result.note or f"rebalanced at {T.date()}"
        return result

    def long_short_weights(self, period: DecilePeriod) -> Dict[str, float]:
        """+gross/2 over the top decile, -gross/2 over the bottom one, equal weights."""
        n = self.config.n_deciles
        half = self.long_short_gross / 2.0
        top, bottom = period.weights.get(n, {}), period.weights.get(1, {})
        out = {s: half * w for s, w in top.items()}
        for s, w in bottom.items():
            out[s] = out.get(s, 0.0) - half * w
        return out

    def _settle(self, daily: pd.DataFrame, T: pd.Timestamp) -> None:
        if not self._open or self._last is None:
            return
        start = self._last
        for name, period in list(self._open.items()):
            symbols = sorted({s for w in period.weights.values() for s in w})
            returns = {}
            for s in symbols:
                col = daily.get(s)
                p0 = col.get(start) if col is not None else None
                p1 = col.loc[:T].dropna().iloc[-1] if col is not None and col.loc[:T].notna().any() else None
                returns[s] = (float(p1) / float(p0) - 1.0) if p0 and p1 and pd.notna(p0) else None
            self.research[name].settle(period, T, returns)
            for rec in self.predictions:
                if rec.variant == name and rec.rebalance == start:
                    rec.next_return = returns.get(rec.symbol)
        self._open = {}
