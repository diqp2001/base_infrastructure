"""
Domain entity for ShareFactorValue.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional
from domain.entities.factor.finance.financial_assets.equity_factor_value import EquityFactorValue


@dataclass
class ShareFactorValue(EquityFactorValue):
    """
    Domain entity representing a share-specific factor value.
    Extends EquityFactorValue with share-specific business logic.
    """
    
    
    def __post_init__(self):
        """Validate domain constraints including share-specific ones."""
        super().__post_init__()
        
        
    def __str__(self) -> str:
        return f"ShareFactorValue(factor_id={self.factor_id}, entity_id={self.entity_id}, ticker_symbol={self.ticker_symbol}, share_class={self.share_class}, value={self.value})"