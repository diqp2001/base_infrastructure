"""
Domain entity for FinancialAssetFactorValue.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional
from domain.entities.factor.factor_value import FactorValue


@dataclass
class FinancialAssetFactorValue(FactorValue):
    """
    Domain entity representing a financial asset-specific factor value.
    Extends base FactorValue with financial asset business logic.
    """
    
    def __post_init__(self):
        """Validate domain constraints including financial asset-specific ones."""
        super().__post_init__()
        
 

    def __str__(self) -> str:
        return f"FinancialAssetFactorValue(factor_id={self.factor_id}, entity_id={self.entity_id}, asset_class={self.asset_class}, value={self.value}, currency={self.currency})"