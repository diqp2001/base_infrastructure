"""
P.11 read-only paper validation (pure): would the screened trade still fill at the screened prices?

No order is sent anywhere (owner, 2026-11-06: P.11 read-only; the paper account belongs to the STM trader). Some
minutes after the screen every leg is quoted again; a leg "would fill" when its executable side is at least as good
as the screened price: the short ETF call's bid >= the screened bid, a long call's ask <= the screened ask. Slippage
is in dollars against us (positive = worse than screened), so the re-quoted net premium = screened net - slippage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

LIVE = 1


@dataclass(frozen=True)
class LegToCheck:
    symbol: str
    side: str                        # "sell" (the ETF call) | "buy" (a constituent call)
    contracts: float
    multiplier: float
    screened_price: float            # the bid sold / the ask bought at the screen


@dataclass
class LegCheck:
    leg: LegToCheck
    bid: Optional[float]
    ask: Optional[float]
    market_data_type: Optional[int]
    problem: Optional[str] = None    # no two-sided quote / not live

    @property
    def executable_price(self) -> Optional[float]:
        return self.bid if self.leg.side == "sell" else self.ask

    @property
    def would_fill(self) -> bool:
        p = self.executable_price
        if self.problem or p is None:
            return False
        return p >= self.leg.screened_price if self.leg.side == "sell" else p <= self.leg.screened_price

    @property
    def slippage(self) -> Optional[float]:
        """Dollars against us vs the screened price (positive = worse)."""
        p = self.executable_price
        if self.problem or p is None:
            return None
        per_share = self.leg.screened_price - p if self.leg.side == "sell" else p - self.leg.screened_price
        return per_share * self.leg.contracts * self.leg.multiplier


@dataclass
class FillCheck:
    legs: List[LegCheck] = field(default_factory=list)

    @property
    def quoted(self) -> List[LegCheck]:
        return [c for c in self.legs if c.problem is None]

    @property
    def complete(self) -> bool:
        return bool(self.legs) and len(self.quoted) == len(self.legs)

    @property
    def legs_filled(self) -> int:
        return sum(1 for c in self.legs if c.would_fill)

    @property
    def all_fill(self) -> bool:
        return self.complete and self.legs_filled == len(self.legs)

    @property
    def slippage(self) -> Optional[float]:
        """Total slippage; None when a leg has no usable quote (never a partial total presented as complete)."""
        return sum(c.slippage for c in self.legs) if self.complete else None


def check_leg(leg: LegToCheck, bid: Optional[float], ask: Optional[float], market_data_type: Optional[int],
              require_live: bool = True) -> LegCheck:
    problem = None
    if bid is None or ask is None or bid <= 0 or ask <= 0 or ask < bid:
        problem = f"no two-sided quote (bid {bid}, ask {ask})"
    elif require_live and market_data_type != LIVE:
        problem = f"quote not live (market data type {market_data_type})"
    return LegCheck(leg, bid, ask, market_data_type, problem)


def fill_check(checks: Sequence[LegCheck]) -> FillCheck:
    return FillCheck(list(checks))
