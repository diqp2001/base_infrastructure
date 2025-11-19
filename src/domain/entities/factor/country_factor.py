"""
src/domain/entities/factor/country_factor.py

CountryFactor domain entity - follows unified factor pattern.
"""

from __future__ import annotations
from typing import Optional
from .factor import Factor


class CountryFactor(Factor):
    """Domain entity representing a country-specific factor."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        
        country_code: Optional[str] = None,
        currency: Optional[str] = None,
        is_developed: Optional[bool] = None,
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,
        )
        self.country_code = country_code  # e.g., "US", "CA", "GB", "JP", "DE"
        self.currency = currency  # e.g., "USD", "CAD", "GBP", "JPY", "EUR"
        self.is_developed = is_developed

    def validate_country_code(self) -> bool:
        """Validate that country_code follows ISO 3166-1 alpha-2 standard."""
        return self.country_code is not None and len(self.country_code) == 2

    def validate_currency(self) -> bool:
        """Validate that currency follows ISO 4217 standard."""
        return self.currency is not None and len(self.currency) == 3
