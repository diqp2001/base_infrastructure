# domain/entities/factor/finance/financial_assets/share_factor/target_factor_share.py

from dataclasses import dataclass
from typing import Optional
from decimal import Decimal
import pandas as pd

from .share_factor import ShareFactor


@dataclass
class TargetFactorShare(ShareFactor):
    """
    Domain entity representing target variable factors for share analysis.
    Handles target returns for model training (both scaled and non-scaled).
    """
    
    target_type: str  # 'target_returns', 'target_returns_nonscaled'
    forecast_horizon: int  # number of periods ahead to predict (e.g., 1 for 1-day ahead)
    is_scaled: bool = True  # whether target is normalized/scaled
    
    def __post_init__(self):
        super().__post_init__()
        if not self.target_type:
            raise ValueError("target_type is required for TargetFactorShare")
        if not self.forecast_horizon or self.forecast_horizon <= 0:
            raise ValueError("forecast_horizon must be a positive integer")
            
    def get_target_description(self) -> str:
        """Get human-readable description of this target factor."""
        scaling = "scaled" if self.is_scaled else "non-scaled"
        return f"{self.forecast_horizon}-day forward returns ({scaling})"