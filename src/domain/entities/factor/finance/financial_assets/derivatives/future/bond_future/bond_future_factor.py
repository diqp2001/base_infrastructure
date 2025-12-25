from __future__ import annotations
from typing import Optional
import math
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_factor import FutureFactor


class BondFutureFactor(FutureFactor):
    """Base factor for bond futures."""
    
    def __init__(self, name: str, subgroup: Optional[str] = None, factor_id: Optional[int] = None, **kwargs):
        super().__init__(
            name=name,
            group="Bond Future Factor",
            subgroup=subgroup,
            data_type="float",
            source="model",
            definition=f"Bond future factor: {name}",
            factor_id=factor_id,
            **kwargs
        )


class BondFutureForwardPriceFactor(BondFutureFactor):
    """Forward price factor for a bond future."""
    
    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(name="Forward Price", subgroup="Price", factor_id=factor_id, **kwargs)
    
    def calculate_forward_price(
        self,
        spot_price: float,
        r: float,
        T: float,
        carry_cost: float = 0.0,
        coupon_yield: float = 0.0
    ) -> Optional[float]:
        """Forward price: F = S * exp((r + carry_cost - coupon_yield) * T)"""
        if spot_price <= 0 or T <= 0:
            return None
        return spot_price * math.exp((r + carry_cost - coupon_yield) * T)


class BondFutureDiscountedValueFactor(BondFutureFactor):
    """Discounted value factor for a bond future."""
    
    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(name="Discounted Value", subgroup="Price", factor_id=factor_id, **kwargs)
    
    def calculate_discounted_value(
        self,
        future_price: float,
        r: float,
        T: float
    ) -> Optional[float]:
        """PV = F * exp(-r * T)"""
        if future_price <= 0 or T < 0:
            return None
        return future_price * math.exp(-r * T)


class BondFutureAnnualizedRollYieldFactor(BondFutureFactor):
    """Annualized roll yield factor for a bond future."""
    
    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(name="Annualized Roll Yield", subgroup="Yield", factor_id=factor_id, **kwargs)
    
    def calculate_roll_yield(
        self,
        spot_price: float,
        future_price: float,
        T: float
    ) -> Optional[float]:
        """Annualized roll yield = (F/S - 1) / T"""
        if spot_price <= 0 or future_price <= 0 or T <= 0:
            return None
        return (future_price / spot_price - 1) / T
