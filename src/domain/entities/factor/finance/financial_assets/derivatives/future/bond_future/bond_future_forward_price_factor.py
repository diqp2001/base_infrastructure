from __future__ import annotations
import math
from decimal import Decimal
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_factor import BondFutureFactor


class BondFutureForwardPriceFactor(BondFutureFactor):
    """Forward price factor for a bond future.

    Dependencies: spot_price (close from BondFutureFactor).
    r defaults to 0.053 (approximate SOFR); T defaults to 0.25 (quarterly cycle).
    Replace r/T with dynamic factor dependencies when a rate factor is available.
    """

    def __init__(self, name: str = "Forward Price", factor_id: Optional[int] = None, **kwargs):
        kwargs.setdefault('subgroup', 'daily')
        super().__init__(name=name, factor_id=factor_id, **kwargs)

    @property
    def calculate_dependencies(self) -> list:
        return ["spot_price", "risk_free_rate", "time_to_maturity"]

    def calculate(self, dependencies: dict) -> Optional[Decimal]:
        # rate and maturity are inputs: no hard-coded fallback (missing input -> no value)
        spot, r, T = (dependencies.get(k) for k in ("spot_price", "risk_free_rate", "time_to_maturity"))
        if spot is None or r is None or T is None:
            return None
        result = self.calculate_forward_price(float(spot), r=float(r), T=float(T))
        return Decimal(str(result)) if result is not None else None

    def calculate_forward_price(
        self,
        spot_price: float,
        r: float,
        T: float,
        carry_cost: float = 0.0,
        coupon_yield: float = 0.0,
    ) -> Optional[float]:
        """Forward price: F = S * exp((r + carry_cost - coupon_yield) * T)"""
        if spot_price <= 0 or T <= 0:
            return None
        return spot_price * math.exp((r + carry_cost - coupon_yield) * T)
