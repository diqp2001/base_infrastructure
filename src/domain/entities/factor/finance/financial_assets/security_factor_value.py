"""
Domain entity for SecurityFactorValue.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional
from domain.entities.factor.finance.financial_assets.financial_asset_factor_value import FinancialAssetFactorValue


@dataclass
class SecurityFactorValue(FinancialAssetFactorValue):
    """
    Domain entity representing a security-specific factor value.
    Extends FinancialAssetFactorValue with security-specific business logic.
    """
    
    
    def __post_init__(self):
        """Validate domain constraints including security-specific ones."""
        super().__post_init__()
        
   