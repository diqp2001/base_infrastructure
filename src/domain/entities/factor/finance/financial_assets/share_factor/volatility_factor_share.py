# domain/entities/factor/finance/financial_assets/share_factor/volatility_factor_share.py

from __future__ import annotations
from typing import Optional
from domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor


class ShareVolatilityFactor(ShareFactor):
    """
    Domain entity representing volatility factors for share analysis.
    Handles various types of volatility calculations like daily_vol, monthly_vol, vol_of_vol, realized_vol.
    """

    def __init__(
        self,
        name: str,
        volatility_type: str,  # 'daily_vol', 'monthly_vol', 'vol_of_vol', 'realized_vol'
        period: int,  # window size for volatility calculation
        group: str = "Volatility",
        subgroup: Optional[str] = "Realized",
        data_type: str = "numeric",
        source: Optional[str] = "Internal",
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        annualization_factor: Optional[float] = None,  # e.g., sqrt(252) for annualizing
    ):
        definition = definition or f"{volatility_type} volatility factor (period: {period})"
        super().__init__(name=name, group=group, subgroup=subgroup, data_type=data_type, source=source, definition=definition, factor_id=factor_id)
        self.volatility_type = volatility_type
        self.period = period
        self.annualization_factor = annualization_factor
        
        if not self.volatility_type:
            raise ValueError("volatility_type is required for ShareVolatilityFactor")
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

    def __str__(self):
        return f"ShareVolatilityFactor(name={self.name}, volatility_type={self.volatility_type}, period={self.period})"