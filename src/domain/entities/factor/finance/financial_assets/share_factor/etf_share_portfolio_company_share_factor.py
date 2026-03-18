"""
src/domain/entities/factor/share_factor.py

ShareFactor domain entity - follows unified factor pattern.
"""

from __future__ import annotations
from typing import Optional

from src.domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor


class ETFSharePortfolioCompanyShareFactor(ShareFactor):
    """Domain entity representing a share-specific factor."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        frequency: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,


        
    ):
        super().__init__(
            name=name,
            group=group,
            subgroup=subgroup,
            frequency=frequency,
            data_type=data_type,
            source=source,
            definition=definition,
            factor_id=factor_id,

        )
      
   