from __future__ import annotations
import math
from decimal import Decimal
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_factor import BondFutureFactor
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.carry_inputs import FutureCarryInputs


class BondFutureForwardPriceFactor(FutureCarryInputs, BondFutureFactor):
    """Forward price factor for a bond future.

    Inputs (FutureCarryInputs): the future's last closed close, the settlement currency's yield
    (CurrencyYieldFactor -> dated SOFR / CORRA future) and the years to the future's expiry.
    """

    def __init__(self, name: str = "Forward Price", factor_id: Optional[int] = None, **kwargs):
        kwargs.setdefault('subgroup', 'daily')
        kwargs.setdefault('frequency', '1d')
        kwargs.setdefault('data_type', 'numeric')
        kwargs.setdefault('source', 'calculated')
        super().__init__(name=name, factor_id=factor_id, **kwargs)

    def calculate(self, dependencies: dict) -> Optional[Decimal]:
        """F = close * exp(r T): close, r and T from FutureCarryInputs (resolution service)."""
        inputs = self.carry_inputs(dependencies or {})
        if inputs is None:
            return None
        price, r, T = inputs
        result = self.calculate_forward_price(price, r=r, T=T)
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
