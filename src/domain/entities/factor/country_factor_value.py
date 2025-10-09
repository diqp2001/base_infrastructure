"""
Domain entity for CountryFactorValue.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional
from domain.entities.factor.factor_value import FactorValue


@dataclass
class CountryFactorValue(FactorValue):
    """
    Domain entity representing a country-specific factor value.
    Extends base FactorValue with country-specific business logic.
    """
    country_code: Optional[str] = None  # e.g., "US", "CA", "GB", "JP", "DE"
    currency: Optional[str] = None  # e.g., "USD", "CAD", "GBP", "JPY", "EUR"
    inflation_adjusted: Optional[bool] = False
    gdp_relative: Optional[bool] = False

    def __post_init__(self):
        """Validate domain constraints including country-specific ones."""
        super().__post_init__()
        
        if self.country_code and len(self.country_code) != 2:
            raise ValueError("country_code should be a 2-character ISO code")
        if self.currency and len(self.currency) != 3:
            raise ValueError("currency should be a 3-character ISO code")

    def convert_to_currency(self, target_currency: str, exchange_rate: Decimal) -> 'CountryFactorValue':
        """Convert the factor value to a different currency."""
        if not self.currency:
            raise ValueError("Cannot convert currency when original currency is not set")
        
        if self.currency == target_currency:
            return self  # No conversion needed
        
        converted_value = self.value * exchange_rate
        
        return CountryFactorValue(
            id=self.id,
            factor_id=self.factor_id,
            entity_id=self.entity_id,
            date=self.date,
            value=converted_value,
            country_code=self.country_code,
            currency=target_currency,
            inflation_adjusted=self.inflation_adjusted,
            gdp_relative=self.gdp_relative
        )

    def adjust_for_inflation(self, inflation_rate: Decimal) -> 'CountryFactorValue':
        """Adjust the factor value for inflation."""
        if self.inflation_adjusted:
            raise ValueError("Value is already inflation adjusted")
        
        adjusted_value = self.value / (Decimal('1') + inflation_rate)
        
        return CountryFactorValue(
            id=self.id,
            factor_id=self.factor_id,
            entity_id=self.entity_id,
            date=self.date,
            value=adjusted_value,
            country_code=self.country_code,
            currency=self.currency,
            inflation_adjusted=True,
            gdp_relative=self.gdp_relative
        )

    def normalize_to_gdp(self, gdp_value: Decimal) -> 'CountryFactorValue':
        """Normalize the factor value relative to GDP."""
        if gdp_value <= 0:
            raise ValueError("GDP value must be positive")
        
        normalized_value = self.value / gdp_value
        
        return CountryFactorValue(
            id=self.id,
            factor_id=self.factor_id,
            entity_id=self.entity_id,
            date=self.date,
            value=normalized_value,
            country_code=self.country_code,
            currency=self.currency,
            inflation_adjusted=self.inflation_adjusted,
            gdp_relative=True
        )

    def __str__(self) -> str:
        return f"CountryFactorValue(factor_id={self.factor_id}, entity_id={self.entity_id}, country_code={self.country_code}, currency={self.currency}, value={self.value})"