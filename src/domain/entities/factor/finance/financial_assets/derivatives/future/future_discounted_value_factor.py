from __future__ import annotations
from typing import Optional
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_factor import FutureFactor
import math


class FutureDiscountedValueFactor(FutureFactor):
    """Discounted present value factor for a futures contract."""
    
    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(
           
            factor_id=factor_id,
            **kwargs
        )
    
    def calculate(
        self,
        future_price: float,
        r: float,
        T: float
    ) -> Optional[float]:
        """PV = F * exp(-r * T)"""
        if future_price <= 0 or T < 0:
            return None
        return future_price * math.exp(-r * T)