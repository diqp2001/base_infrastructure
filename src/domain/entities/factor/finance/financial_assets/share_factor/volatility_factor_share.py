# domain/entities/factor/finance/financial_assets/share_factor/volatility_factor_share.py

from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
import pandas as pd

from .share_factor import ShareFactor


@dataclass
class ShareVolatilityFactor(ShareFactor):
    """
    Domain entity representing volatility factors for share analysis.
    Handles various types of volatility calculations like daily_vol, monthly_vol, vol_of_vol, realized_vol.
    """
    
    volatility_type: str  # 'daily_vol', 'monthly_vol', 'vol_of_vol', 'realized_vol'
    period: int  # window size for volatility calculation
    annualization_factor: Optional[float] = None  # e.g., sqrt(252) for annualizing
    
    def __post_init__(self):
        super().__post_init__()
        if not self.volatility_type:
            raise ValueError("volatility_type is required for VolatilityFactorShare")
        if not self.period or self.period <= 0:
            raise ValueError("period must be a positive integer")
            
    def get_volatility_description(self) -> str:
        """Get human-readable description of this volatility factor."""
        type_descriptions = {
            'daily_vol': f'{self.period}-day rolling volatility',
            'monthly_vol': f'{self.period}-day rolling monthly volatility', 
            'vol_of_vol': f'Volatility of volatility ({self.period}-day)',
            'realized_vol': f'Realized volatility ({self.period}-day)'
        }
        return type_descriptions.get(self.volatility_type, f'Volatility factor ({self.volatility_type})')