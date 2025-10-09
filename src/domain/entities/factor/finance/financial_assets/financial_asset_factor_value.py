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
    asset_class: Optional[str] = None  # e.g., "equity", "bond", "commodity", "currency"
    market_value: Optional[Decimal] = None
    currency: Optional[str] = None
    is_adjusted: Optional[bool] = False  # e.g., split-adjusted, dividend-adjusted

    def __post_init__(self):
        """Validate domain constraints including financial asset-specific ones."""
        super().__post_init__()
        
        if self.market_value is not None and not isinstance(self.market_value, Decimal):
            self.market_value = Decimal(str(self.market_value))
        
        if self.currency and len(self.currency) != 3:
            raise ValueError("currency should be a 3-character ISO code")

    def calculate_return(self, previous_value: 'FinancialAssetFactorValue') -> Decimal:
        """Calculate return compared to a previous value."""
        if previous_value.value == 0:
            raise ValueError("Cannot calculate return with zero previous value")
        
        return (self.value - previous_value.value) / previous_value.value

    def apply_market_adjustment(self, adjustment_factor: Decimal) -> 'FinancialAssetFactorValue':
        """Apply market-specific adjustments (e.g., for splits, dividends)."""
        return FinancialAssetFactorValue(
            id=self.id,
            factor_id=self.factor_id,
            entity_id=self.entity_id,
            date=self.date,
            value=self.value * adjustment_factor,
            asset_class=self.asset_class,
            market_value=self.market_value * adjustment_factor if self.market_value else None,
            currency=self.currency,
            is_adjusted=True
        )

    def convert_currency(self, target_currency: str, exchange_rate: Decimal) -> 'FinancialAssetFactorValue':
        """Convert to a different currency."""
        if not self.currency:
            raise ValueError("Cannot convert currency when original currency is not set")
        
        if self.currency == target_currency:
            return self
        
        converted_value = self.value * exchange_rate
        converted_market_value = self.market_value * exchange_rate if self.market_value else None
        
        return FinancialAssetFactorValue(
            id=self.id,
            factor_id=self.factor_id,
            entity_id=self.entity_id,
            date=self.date,
            value=converted_value,
            asset_class=self.asset_class,
            market_value=converted_market_value,
            currency=target_currency,
            is_adjusted=self.is_adjusted
        )

    def __str__(self) -> str:
        return f"FinancialAssetFactorValue(factor_id={self.factor_id}, entity_id={self.entity_id}, asset_class={self.asset_class}, value={self.value}, currency={self.currency})"