from __future__ import annotations
from typing import Optional
from domain.entities.factor.finance.financial_assets.derivatives.future.future_factor import FutureFactor
import math


class FutureForwardPriceFactor(FutureFactor):
    """Forward price factor for a futures contract."""
    
    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(
            name="Forward Price",
            group="Future Factor",
            subgroup="Price",
            data_type="float",
            source="model",
            definition="Theoretical forward/futures price using cost-of-carry.",
            factor_id=factor_id,
            **kwargs
        )
    
    def calculate_forward_price(
        self,
        spot_price: float,
        r: float,
        T: float,
        cost_of_carry: float = 0.0,
        dividend_yield: float = 0.0
    ) -> Optional[float]:
        """F = S * exp((r - q + c) * T)"""
        if spot_price <= 0 or T <= 0:
            return None
        return spot_price * math.exp((r - dividend_yield + cost_of_carry) * T)