"""
src/domain/entities/factor/financial_asset_factor.py

FinancialAssetFactor domain entity - follows unified factor pattern.
"""

from __future__ import annotations
from typing import Optional
from ...factor import Factor


class FinancialAssetFactor(Factor):
    """Domain entity representing a financial asset-specific factor."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        
        currency: Optional[str] = None,
        market: Optional[str] = None,
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
        self.currency = currency  # e.g., "USD", "EUR", "GBP"
        self.market = market  # e.g., "NYSE", "NASDAQ", "LSE"

    def is_tradable(self) -> bool:
        """Check if this financial asset is tradable (has market info)."""
        return self.market is not None

    def is_currency_denominated(self, target_currency: str) -> bool:
        """Check if this asset is denominated in the target currency."""
        return self.currency == target_currency