"""
src/domain/entities/factor/share_target_factor.py

ShareTargetFactor domain entity - follows unified factor pattern.
"""

from __future__ import annotations
from typing import Optional
from .share_factor import ShareFactor


class ShareTargetFactor(ShareFactor):
    """Domain entity representing a share target variable factor for model training."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        asset_class: Optional[str] = "equity",
        currency: Optional[str] = None,
        market: Optional[str] = None,
        security_type: Optional[str] = "stock",
        isin: Optional[str] = None,
        cusip: Optional[str] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        market_cap_category: Optional[str] = None,
        ticker_symbol: Optional[str] = None,
        share_class: Optional[str] = None,
        exchange: Optional[str] = None,
        target_type: Optional[str] = None,
        forecast_horizon: Optional[int] = None,
        is_scaled: Optional[bool] = None,
        scaling_method: Optional[str] = None,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
            asset_class=asset_class,
            currency=currency,
            market=market,
            security_type=security_type,
            isin=isin,
            cusip=cusip,
            sector=sector,
            industry=industry,
            market_cap_category=market_cap_category,
            ticker_symbol=ticker_symbol,
            share_class=share_class,
            exchange=exchange,
        )
        self.target_type = target_type or "return"  # e.g., "return", "price", "direction", "volatility"
        self.forecast_horizon = forecast_horizon or 1  # Days ahead to predict
        self.is_scaled = is_scaled or False  # Whether target is normalized/scaled
        self.scaling_method = scaling_method  # e.g., "z_score", "min_max", "robust"

    def calculate_future_return(self, current_price: float, future_price: float) -> Optional[float]:
        """Calculate the future return target variable."""
        if current_price <= 0 or future_price <= 0:
            return None
        
        return (future_price / current_price) - 1

    def calculate_price_direction(self, current_price: float, future_price: float) -> Optional[int]:
        """Calculate the price direction target variable (1 for up, 0 for down)."""
        if current_price <= 0 or future_price <= 0:
            return None
        
        return 1 if future_price > current_price else 0

    def is_return_target(self) -> bool:
        """Check if this is a return-based target variable."""
        return self.target_type.lower() == "return"

    def is_classification_target(self) -> bool:
        """Check if this is a classification target (direction, category)."""
        classification_types = ["direction", "category", "binary", "class"]
        return any(t in self.target_type.lower() for t in classification_types)

    def is_short_term_target(self) -> bool:
        """Check if this is a short-term prediction target."""
        return self.forecast_horizon <= 5

    def is_medium_term_target(self) -> bool:
        """Check if this is a medium-term prediction target."""
        return 5 < self.forecast_horizon <= 30

    def is_long_term_target(self) -> bool:
        """Check if this is a long-term prediction target."""
        return self.forecast_horizon > 30