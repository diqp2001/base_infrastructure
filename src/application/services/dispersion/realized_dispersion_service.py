"""
The 6-month realized payoff history of the dispersion structure (a layer next to the live screen, which it does not
change): for one ETF, every trading day of the window opens the screen's ATM ETF call and ATM constituent calls
(replicate(): the screen's basket) and holds them to the screen's expiry; realized_payoff has the formulas.

Holdings / membership. A holdings snapshot dated on or before the observation date is used when one exists
(point in time: the screen archives each day's holdings). Before the first snapshot, the earliest snapshot is
back-cast: its share counts per ETF share, valued at the observation date's closes - the membership is then today's,
not the historical one (survivorship), and every such observation is flagged point_in_time=False.

Prices: PriceHistoryPort (split-adjusted daily closes); a missing close makes the observation incomplete.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from src.domain.entities.finance.dispersion.etf_holdings import ConstituentWeights
from src.domain.entities.finance.dispersion.option_data import Underlying
from src.domain.entities.finance.dispersion.realized_payoff import (
    HoldingsSnapshot, Observation, RollingStats, cumulative_series, months_before, replication_series, observe, rolling_stats,
    shares_from_weights,
)
from src.domain.entities.finance.dispersion.screen_config import DispersionScreenConfig
from src.domain.ports.finance.dispersion.price_history_port import PriceHistoryPort

logger = logging.getLogger(__name__)
WINDOW_MONTHS = 6


@dataclass
class EtfHistory:
    etf: str
    as_of: date
    observations: List[Observation] = field(default_factory=list)
    stats: Optional[RollingStats] = None
    series: List[Tuple[date, float, float]] = field(default_factory=list)
    replication_series: List[Tuple[date, float, float, float]] = field(default_factory=list)
    membership: str = ""                       # how the holdings were obtained (point in time / back-cast)
    reasons: List[str] = field(default_factory=list)   # why no history (e.g. a constituent not resolvable)


class RealizedDispersionService:

    def __init__(self, prices: PriceHistoryPort, resolve: Callable[[Sequence[str], date], Dict[str, Optional[Underlying]]],
                 config: DispersionScreenConfig, months: int = WINDOW_MONTHS):
        self.prices = prices
        self.resolve = resolve               # the screening service's cached resolution
        self.config = config
        self.months = months
        self._closes: Dict[str, Dict[date, float]] = {}

    def history_start(self, as_of: date) -> date:
        """First day of price history needed: the window start, minus a week for a back-cast snapshot's own date."""
        return months_before(as_of, self.months) - timedelta(days=7)

    def _closes_of(self, u: Underlying, start: date, as_of: date) -> Dict[date, float]:
        if u.symbol not in self._closes:
            self._closes[u.symbol] = self.prices.daily_closes(u, start, as_of)
        return self._closes[u.symbol]

    def history(self, ticker: str, snapshots: Sequence[ConstituentWeights], as_of: date,
                progress: Callable[[str], None] = lambda m: None) -> EtfHistory:
        """snapshots: the ETF's holdings files (ConstituentWeights), any dates; as_of: the last completed session."""
        out = EtfHistory(ticker, as_of)
        snapshots = sorted((s for s in snapshots if s.ok and s.as_of <= as_of), key=lambda s: s.as_of)
        if not snapshots:
            out.reasons.append("no holdings snapshot on or before the date")
            return out
        symbols = sorted({s for snap in snapshots for s in snap.weights})
        resolved = {}
        for symbol in [ticker] + symbols:                  # stops at the first one: no history without every price
            resolved[symbol] = self.resolve([symbol], as_of)[symbol]
            if resolved[symbol] is None:
                out.reasons.append(f"{symbol}: not a US-listed share at the broker")
                return out
        start = self.history_start(as_of)
        in_force = [s.as_of for s in snapshots if s.as_of <= months_before(as_of, self.months)]
        if in_force:                    # the snapshot in force at the window start is valued at its own date's closes
            start = min(start, in_force[-1] - timedelta(days=7))
        etf_closes = self._closes_of(resolved[ticker], start, as_of)
        if not etf_closes:
            out.reasons.append("no ETF price history")
            return out
        closes = {s: self._closes_of(resolved[s], start, as_of) for s in symbols}
        held = self._snapshots(snapshots, etf_closes, closes)
        if not held:
            out.reasons.append("no close at any holdings snapshot date: shares per ETF share unknown")
            return out
        first = held[0]
        window_start = months_before(as_of, self.months)
        out.membership = (f"holdings of {first.as_of} back-cast before that date (that day's membership and share "
                          f"counts, not the historical ones)" if window_start < first.as_of else "point in time")
        for day in sorted(d for d in etf_closes if window_start < d <= as_of):
            snapshot = next((s for s in reversed(held) if s.as_of <= day), None)
            if snapshot is None:                                       # before every snapshot: back-cast the first
                snapshot = HoldingsSnapshot(first.as_of, first.shares, point_in_time=False)
            out.observations.append(observe(day, etf_closes, {s: closes[s] for s in snapshot.shares}, snapshot,
                                            self.config, as_of))
        out.stats = rolling_stats(out.observations, as_of, self.months)
        out.series = cumulative_series(out.observations, as_of, self.months)
        out.replication_series = replication_series(out.observations, as_of, self.months)
        progress(f"{ticker}: {out.stats.n} completed observations, {out.stats.n_open} open, "
                 f"{out.stats.n_incomplete} incomplete")
        return out

    @staticmethod
    def _snapshots(snapshots: Sequence[ConstituentWeights], etf_closes: Dict[date, float],
                   closes: Dict[str, Dict[date, float]]) -> List[HoldingsSnapshot]:
        """Each holdings file as share counts per ETF share, from its own date's closes (or the last close
        before it, at most a week): never a later price."""
        out = []
        for snap in snapshots:
            day = next((d for d in sorted(etf_closes, reverse=True) if snap.as_of - timedelta(days=7) <= d <= snap.as_of),
                       None)
            if day is None or any(day not in closes[s] for s in snap.weights):
                continue
            out.append(HoldingsSnapshot(snap.as_of, shares_from_weights(snap.weights, etf_closes[day],
                                                                        {s: closes[s][day] for s in snap.weights}),
                                        point_in_time=True))
        return out
