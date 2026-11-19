"""
Point-in-time membership of an index ETF (the fund and its constituents) as domain Universe / UniverseConstituent
rows, and the constituents' weights on a given day.

Built from the members on a base date plus dated changes (additions / removals effective before the open of that
day), so a historical trade only uses the constituents in force on its own date: never today's list.
The ETF itself is a constituent of the universe too (entity_type 'ETFShare', never removed): it is the short leg.

Weights, price-weighted index (DJIA / DIA): every member counts for the same number of shares, so a member's weight is
its ACTUAL share price over the sum of the members' actual prices. Closes are split-adjusted (PriceHistoryPort), so a
member that split later is scaled back to its traded price with ``splits`` (symbol, effective day, ratio): before the
effective day the actual price is the adjusted close x ratio. A missing split shows as a jump in
``replication_ratio`` (the ETF close over the sum of the actual prices), which the backtest reports per trade.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from src.domain.entities.universe.investment_universe import InvestmentUniverse
from src.domain.entities.universe.universe_constituent import UniverseConstituent

ETF_ENTITY_TYPE = "ETFShare"
SHARE_ENTITY_TYPE = "CompanyShare"


@dataclass(frozen=True)
class MembershipChange:
    effective: date                      # before the open of this day
    added: Tuple[str, ...] = ()
    removed: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Split:
    symbol: str
    effective: date                      # first day traded at the split price
    ratio: float                         # new shares per old share (3-for-1 -> 3.0)


class IndexMembership:
    """The universe of an index ETF and its constituents over time."""

    def __init__(self, etf: str, base_date: date, base_members: Sequence[str],
                 changes: Sequence[MembershipChange] = (), splits: Sequence[Split] = (),
                 universe_name: Optional[str] = None):
        self.etf = etf
        self.base_date = base_date
        self.splits = list(splits)
        self.universe = InvestmentUniverse(name=universe_name or f"{etf} point-in-time constituents", id=1,
                                 description=f"{etf} and its constituents from {base_date} (dated changes applied)",
                                 entity_type=SHARE_ENTITY_TYPE)
        self.symbols: List[str] = [etf]
        self.constituents: List[UniverseConstituent] = []
        self._open: Dict[str, UniverseConstituent] = {}
        self._add(etf, base_date, ETF_ENTITY_TYPE)
        for s in base_members:
            self._add(s, base_date, SHARE_ENTITY_TYPE)
        for change in sorted(changes, key=lambda c: c.effective):
            if change.effective <= base_date:
                raise ValueError(f"change {change.effective} is not after the base date {base_date}")
            for s in change.removed:
                row = self._open.pop(s, None)
                if row is None:
                    raise ValueError(f"{change.effective}: {s} is removed but is not a member")
                row.end_date = change.effective - timedelta(days=1)
            for s in change.added:
                if s in self._open:
                    raise ValueError(f"{change.effective}: {s} is added but is already a member")
                self._add(s, change.effective, SHARE_ENTITY_TYPE)

    def _add(self, symbol: str, start: date, entity_type: str) -> None:
        if symbol not in self.symbols:
            self.symbols.append(symbol)
        row = UniverseConstituent(universe_id=self.universe.id, entity_id=self.entity_id(symbol),
                                  entity_type=entity_type, start_date=start, id=len(self.constituents) + 1)
        self.constituents.append(row)
        self._open[symbol] = row

    def entity_id(self, symbol: str) -> int:
        return self.symbols.index(symbol) + 1

    def symbol_of(self, entity_id: int) -> str:
        return self.symbols[entity_id - 1]

    # -- point in time --
    def members_at(self, day: date) -> List[str]:
        """The constituents (not the ETF) in force on ``day``, in the order they entered."""
        if day < self.base_date:
            raise ValueError(f"{day} is before the membership's base date {self.base_date}")
        return [self.symbol_of(r.entity_id) for r in self.constituents
                if r.entity_type == SHARE_ENTITY_TYPE and r.start_date <= day
                and (r.end_date is None or day <= r.end_date)]

    def all_constituents(self) -> List[str]:
        """Every symbol that was a constituent at some point (price history needed for all of them)."""
        return [s for s in self.symbols if s != self.etf]

    def split_factor(self, symbol: str, day: date) -> float:
        """Adjusted close -> traded price on ``day``: the product of the ratios of later splits."""
        factor = 1.0
        for sp in self.splits:
            if sp.symbol == symbol and day < sp.effective:
                factor *= sp.ratio
        return factor

    def actual_price(self, symbol: str, day: date, adjusted_close: float) -> float:
        return adjusted_close * self.split_factor(symbol, day)

    def price_weights(self, day: date, adjusted_closes: Mapping[str, float]) -> Dict[str, float]:
        """{member: weight} on ``day`` (price-weighted, summing to 1); ValueError when a member has no close."""
        members = self.members_at(day)
        missing = [s for s in members if not adjusted_closes.get(s)]
        if missing:
            raise ValueError(f"{day}: no close for {missing}")
        actual = {s: self.actual_price(s, day, adjusted_closes[s]) for s in members}
        total = sum(actual.values())
        return {s: p / total for s, p in actual.items()}

    def replication_ratio(self, day: date, adjusted_closes: Mapping[str, float]) -> Optional[float]:
        """ETF close / sum of the members' actual prices (smooth between membership changes; a jump = a split or a
        corporate action the configuration misses)."""
        members = self.members_at(day)
        etf = adjusted_closes.get(self.etf)
        if not etf or any(not adjusted_closes.get(s) for s in members):
            return None
        return etf / sum(self.actual_price(s, day, adjusted_closes[s]) for s in members)
