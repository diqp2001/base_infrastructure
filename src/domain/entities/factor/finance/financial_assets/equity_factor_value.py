"""
Domain entity for EquityFactorValue.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional
from domain.entities.factor.finance.financial_assets.security_factor_value import SecurityFactorValue


@dataclass
class EquityFactorValue(SecurityFactorValue):
    """
    Domain entity representing an equity-specific factor value.
    Extends SecurityFactorValue with equity-specific business logic.
    """
    
    
    def __post_init__(self):
        """Validate domain constraints including equity-specific ones."""
        super().__post_init__()
       
    def __str__(self) -> str:
        return f"EquityFactorValue(factor_id={self.factor_id}, entity_id={self.entity_id}, ticker_symbol={self.ticker_symbol})"