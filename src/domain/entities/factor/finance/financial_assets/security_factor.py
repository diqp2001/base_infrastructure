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

    def has_international_identifier(self) -> bool:
        """Check if this security has international identification."""
        return self.isin is not None

    def has_us_identifier(self) -> bool:
        """Check if this security has US identification."""
        return self.cusip is not None