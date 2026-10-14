from __future__ import annotations
import math
from decimal import Decimal
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_factor import BondFutureFactor


class BondFutureDiscountedValueFactor(BondFutureFactor):
    """Discounted value factor for a bond future.

    Dependencies: future_price (close from BondFutureFactor).
    r defaults to 0.053 (approximate SOFR); T defaults to 0.25 (quarterly cycle).
    Replace r/T with dynamic factor dependencies when a rate factor is available.
    """

    def __init__(self, name: str = "Discounted Value", factor_id: Optional[int] = None, **kwargs):
        kwargs.setdefault('subgroup', 'daily')
        super().__init__(name=name, factor_id=factor_id, **kwargs)

    @property
    def calculate_dependencies(self) -> list:
        return ["future_price", "risk_free_rate", "time_to_maturity"]

    def calculate(self, dependencies: dict) -> Optional[Decimal]:
        # rate and maturity are inputs: no hard-coded fallback (missing input -> no value)
        future, r, T = (dependencies.get(k) for k in ("future_price", "risk_free_rate", "time_to_maturity"))
        if future is None or r is None or T is None:
            return None
        result = self.calculate_discounted_value(float(future), r=float(r), T=float(T))
        return Decimal(str(result)) if result is not None else None

    def calculate_discounted_value(
        self,
        future_price: float,
        r: float,
        T: float,
    ) -> Optional[float]:
        """PV = F * exp(-r * T)"""
        if future_price <= 0 or T < 0:
            return None
        return future_price * math.exp(-r * T)
