"""
src/domain/entities/factor/security_factor.py

SecurityFactor domain entity - follows unified factor pattern.
"""

from __future__ import annotations
from typing import Optional
from .financial_asset_factor import FinancialAssetFactor


class SecurityFactor(FinancialAssetFactor):
    """Domain entity representing a security-specific factor."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        asset_class: Optional[str] = None,
        currency: Optional[str] = None,
        market: Optional[str] = None,
        security_type: Optional[str] = None,
        isin: Optional[str] = None,
        cusip: Optional[str] = None,
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
        )
        self.security_type = security_type  # e.g., "stock", "bond", "etf", "option"
        self.isin = isin  # International Securities Identification Number
        self.cusip = cusip  # Committee on Uniform Securities Identification Procedures

    def has_international_identifier(self) -> bool:
        """Check if this security has international identification."""
        return self.isin is not None

    def has_us_identifier(self) -> bool:
        """Check if this security has US identification."""
        return self.cusip is not None