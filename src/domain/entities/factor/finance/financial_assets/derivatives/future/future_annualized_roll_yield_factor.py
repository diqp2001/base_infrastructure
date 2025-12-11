from __future__ import annotations
from typing import Optional
from domain.entities.factor.finance.financial_assets.derivatives.future.future_factor import FutureFactor
import math



class AnnualizedRollYieldFactor(FutureFactor):
    """Annualized roll yield factor for a futures contract."""
    
    def __init__(self, factor_id: Optional[int] = None, **kwargs):
        super().__init__(
            name="Annualized Roll Yield",
            group="Future Factor",
            subgroup="Yield",
            data_type="float",
            source="model",
            definition="Annualized roll yield of the futures contract.",
            factor_id=factor_id,
            **kwargs
        )
    
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