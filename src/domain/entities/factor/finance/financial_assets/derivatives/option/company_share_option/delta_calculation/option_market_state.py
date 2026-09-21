from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class OptionMarketState:
    """Snapshot of market inputs required by any delta-calculation method.

    All volatility inputs are annualised fractions (e.g. 0.20 = 20%).
    `tau` is time to expiry in years.  `q` is continuous dividend yield.
    `current_hedge_position` is the delta already held (positive = long delta).
    `historical_returns` and `prior_states` are optional sequences that
    RL-based methods may use for context; analytical methods ignore them.
    """

    spot: float
    strike: float
    tau: float
    r: float
    q: float
    implied_vol: float
    realized_vol: float
    current_hedge_position: float
    option_type: str = "call"
    historical_returns: Optional[List[float]] = field(default=None)
    prior_states: Optional[List[OptionMarketState]] = field(default=None)
