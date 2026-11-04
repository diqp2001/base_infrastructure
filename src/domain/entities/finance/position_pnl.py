"""
Per-position average cost and realized / unrealized P&L from the stored fills (P.08.09, GA-C1). Pure: no database.

Average-cost method, fills in execution order (quantity signed: buy > 0, sell < 0):
    a fill in the direction of the position (or opening it) moves the average cost to the weighted average;
    a fill against it realizes (fill price - average cost) x closed quantity x direction x multiplier, the average
    cost unchanged; a fill through zero closes the whole position, then opens the rest at the fill price.
Unrealized = (last price - average cost) x quantity x multiplier, None without a last price. Commissions are summed
apart: ``net`` = realized + unrealized - commission.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

_EPS = 1e-9


@dataclass(frozen=True)
class Fill:
    symbol: str
    quantity: float                       # signed: buy > 0, sell < 0
    price: float
    commission: float = 0.0


@dataclass(frozen=True)
class PositionPnL:
    symbol: str
    quantity: float
    average_cost: Optional[float]         # None when flat
    realized: float
    commission: float
    last_price: Optional[float] = None
    unrealized: Optional[float] = None
    fills: int = 0

    @property
    def net(self) -> Optional[float]:
        if self.unrealized is None:
            return None
        return self.realized + self.unrealized - self.commission


def signed_quantity(side: str, quantity: float) -> float:
    """IBKR execution side (BOT / SLD, or BUY / SELL) and a positive size -> signed quantity."""
    s = str(side or "").upper()
    if s in ("SLD", "SELL", "S"):
        return -abs(float(quantity))
    if s in ("BOT", "BUY", "B"):
        return abs(float(quantity))
    raise ValueError(f"unknown execution side {side!r}")


def position_pnl(symbol: str, fills: Iterable[Fill], last_price: Optional[float] = None,
                 multiplier: float = 1.0) -> PositionPnL:
    quantity = cost = realized = commission = 0.0          # cost = average cost of the open quantity
    count = 0
    for f in fills:
        count += 1
        commission += float(f.commission or 0.0)
        q, p = float(f.quantity), float(f.price)
        if abs(quantity) < _EPS or quantity * q > 0:          # open or add: weighted average
            new = quantity + q
            cost = (cost * quantity + p * q) / new
            quantity = new
            continue
        closed = min(abs(q), abs(quantity))                   # reduce, close or flip
        direction = 1.0 if quantity > 0 else -1.0
        realized += (p - cost) * closed * direction * multiplier
        quantity += q
        if abs(quantity) < _EPS:
            quantity, cost = 0.0, 0.0
        elif quantity * direction < 0:                        # flipped: the rest opens at the fill price
            cost = p
    flat = abs(quantity) < _EPS
    unrealized = None
    if flat:
        unrealized = 0.0
    elif last_price is not None:
        unrealized = (float(last_price) - cost) * quantity * multiplier
    return PositionPnL(symbol, 0.0 if flat else quantity, None if flat else cost, realized, commission,
                       last_price, unrealized, count)


def positions_pnl(fills: Iterable[Fill], last_prices: Optional[Dict[str, float]] = None,
                  multipliers: Optional[Dict[str, float]] = None) -> List[PositionPnL]:
    """One PositionPnL per symbol (fills already in execution order), sorted by symbol."""
    by_symbol: Dict[str, List[Fill]] = {}
    for f in fills:
        by_symbol.setdefault(f.symbol, []).append(f)
    last_prices, multipliers = last_prices or {}, multipliers or {}
    return [position_pnl(s, fs, last_prices.get(s), multipliers.get(s, 1.0)) for s, fs in sorted(by_symbol.items())]
