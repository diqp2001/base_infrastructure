"""
TargetPortfolio — the portfolio a strategy wants to hold.

    Factor values -> TradingStrategy (StrategySignals) -> portfolio construction -> TargetPortfolio
    TargetPortfolio -> rebalancing (P4) -> trade instructions -> execution

A TargetPortfolio is an immutable value object: an as-of time, the strategy it comes from and one
TargetPortfolioPosition per asset (its target weight, a fraction of portfolio value, signed: < 0 is short).
It is NOT a Position or a PortfolioHolding: those are what the account holds; this is what the strategy wants.
Nothing here knows about quantities held, prices, orders or brokers; it is never persisted (in memory only).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple


@dataclass(frozen=True)
class TargetPortfolioPosition:
    """One asset of a TargetPortfolio.

    ``symbol`` identifies the financial asset (the key the strategy signals use); ``financial_asset_id`` and
    ``asset_type`` give the stored entity when known. ``target_weight`` is the signed fraction of portfolio value
    (0.0 = hold nothing of it). ``target_quantity`` is optional: set only by constructions that size in units."""
    symbol: str
    target_weight: float
    asset_type: Optional[str] = None
    financial_asset_id: Optional[int] = None
    target_quantity: Optional[float] = None

    def __post_init__(self):
        if not self.symbol:
            raise ValueError("a target position needs a symbol")
        if not math.isfinite(float(self.target_weight)):
            raise ValueError(f"{self.symbol}: target weight {self.target_weight!r} is not finite")
        object.__setattr__(self, "target_weight", float(self.target_weight))
        if self.target_quantity is not None and not math.isfinite(float(self.target_quantity)):
            raise ValueError(f"{self.symbol}: target quantity {self.target_quantity!r} is not finite")

    @property
    def side(self) -> int:
        """+1 long, -1 short, 0 flat."""
        return (self.target_weight > 0) - (self.target_weight < 0)


@dataclass(frozen=True)
class TargetPortfolio:
    """What the strategy wants to hold at ``as_of``: positions sorted by symbol, one per asset."""
    as_of: Optional[datetime]
    positions: Tuple[TargetPortfolioPosition, ...] = ()
    strategy_name: Optional[str] = None
    construction: Optional[str] = None          # name of the construction method that built it
    context: Mapping[str, Any] = field(default_factory=dict)
    note: str = ""

    def __post_init__(self):
        positions = tuple(sorted(self.positions, key=lambda p: p.symbol))
        symbols = [p.symbol for p in positions]
        duplicates = sorted({s for s in symbols if symbols.count(s) > 1})
        if duplicates:
            raise ValueError(f"several target positions for {duplicates}")
        object.__setattr__(self, "positions", positions)

    @classmethod
    def from_weights(cls, weights: Mapping[str, float], as_of: Optional[datetime] = None,
                     asset_type: Optional[str] = None, asset_ids: Optional[Mapping[str, int]] = None,
                     **kwargs) -> "TargetPortfolio":
        ids = asset_ids or {}
        return cls(as_of=as_of, positions=tuple(
            TargetPortfolioPosition(symbol=s, target_weight=w, asset_type=asset_type, financial_asset_id=ids.get(s))
            for s, w in weights.items()), **kwargs)

    def __len__(self) -> int:
        return len(self.positions)

    def __iter__(self) -> Iterable[TargetPortfolioPosition]:
        return iter(self.positions)

    def get(self, symbol: str) -> Optional[TargetPortfolioPosition]:
        return next((p for p in self.positions if p.symbol == symbol), None)

    def symbols(self) -> List[str]:
        return [p.symbol for p in self.positions]

    def weights(self) -> Dict[str, float]:
        return {p.symbol: p.target_weight for p in self.positions}

    def longs(self) -> List[TargetPortfolioPosition]:
        return [p for p in self.positions if p.target_weight > 0]

    def shorts(self) -> List[TargetPortfolioPosition]:
        return [p for p in self.positions if p.target_weight < 0]

    @property
    def gross_exposure(self) -> float:
        return sum(abs(p.target_weight) for p in self.positions)

    @property
    def net_exposure(self) -> float:
        return sum(p.target_weight for p in self.positions)
