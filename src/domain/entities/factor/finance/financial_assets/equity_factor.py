"""
src/domain/entities/factor/equity_factor.py

EquityFactor domain entity - follows unified factor pattern.
"""

from __future__ import annotations
from typing import Optional
from .security_factor import SecurityFactor


class EquityFactor(SecurityFactor):
    """Domain entity representing an equity-specific factor."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        market_cap_category: Optional[str] = None,
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
        self.sector = sector  # e.g., "Technology", "Healthcare", "Finance"
        self.industry = industry  # e.g., "Software", "Pharmaceuticals", "Banks"
        self.market_cap_category = market_cap_category  # e.g., "large_cap", "mid_cap", "small_cap"

    def is_large_cap(self) -> bool:
        """Check if this is a large cap equity."""
        return self.market_cap_category == "large_cap"

    def is_in_sector(self, target_sector: str) -> bool:
        """Check if this equity is in the target sector."""
        return self.sector == target_sector