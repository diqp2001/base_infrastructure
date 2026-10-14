from __future__ import annotations
from decimal import Decimal
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_factor import BondFutureFactor


class BondFutureAnnualizedRollYieldFactor(BondFutureFactor):
    """Annualized roll yield factor for a bond future.

    Dependencies: start_price (front-month close), end_price (deferred-month close).
    T defaults to 0.25 (quarterly SOFR contract cycle).
    """

    def __init__(self, name: str = "Annualized Roll Yield", factor_id: Optional[int] = None, **kwargs):
        kwargs.setdefault('subgroup', 'daily')
        kwargs.setdefault('group', 'return')
        super().__init__(name=name, factor_id=factor_id, **kwargs)

    @property
    def calculate_dependencies(self) -> list:
        return ["start_price", "end_price", "time_to_maturity"]

    def calculate(self, dependencies: dict) -> Optional[Decimal]:
        # maturity is an input: no hard-coded fallback (missing input -> no value)
        spot, future, T = (dependencies.get(k) for k in ("start_price", "end_price", "time_to_maturity"))
        if spot is None or future is None or T is None:
            return None
        result = self.calculate_roll_yield(float(spot), float(future), T=float(T))
        return Decimal(str(result)) if result is not None else None

    def calculate_roll_yield(
        self,
        spot_price: float,
        future_price: float,
        T: float,
    ) -> Optional[float]:
        """Annualized roll yield = (F/S - 1) / T"""
        if spot_price <= 0 or future_price <= 0 or T <= 0:
            return None
        return (future_price / spot_price - 1) / T
