# domain/entities/factor/finance/financial_assets/share_factor/target_factor_share.py

from __future__ import annotations
from typing import Optional
from domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor


class ShareTargetFactor(ShareFactor):
    """
    Domain entity representing target variable factors for share analysis.
    Handles target returns for model training (both scaled and non-scaled).
    """

    def __init__(
        self,
        name: str,
        target_type: str,  # 'target_returns', 'target_returns_nonscaled'
        forecast_horizon: int,  # number of periods ahead to predict (e.g., 1 for 1-day ahead)
        group: str = "Target",
        subgroup: Optional[str] = "Returns",
        data_type: str = "numeric",
        source: Optional[str] = "Internal",
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        is_scaled: bool = True,  # whether target is normalized/scaled
    ):
        definition = definition or f"{target_type} factor (horizon: {forecast_horizon})"
        super().__init__(name=name, group=group, subgroup=subgroup, data_type=data_type, source=source, definition=definition, factor_id=factor_id)
        self.target_type = target_type
        self.forecast_horizon = forecast_horizon
        self.is_scaled = is_scaled
        
        if not self.target_type:
            raise ValueError("target_type is required for ShareTargetFactor")
        if not self.forecast_horizon or self.forecast_horizon <= 0:
            raise ValueError("forecast_horizon must be a positive integer")
            
    def get_target_description(self) -> str:
        """Get human-readable description of this target factor."""
        scaling = "scaled" if self.is_scaled else "non-scaled"
        return f"{self.forecast_horizon}-day forward returns ({scaling})"

    def __str__(self):
        return f"ShareTargetFactor(name={self.name}, target_type={self.target_type}, forecast_horizon={self.forecast_horizon})"