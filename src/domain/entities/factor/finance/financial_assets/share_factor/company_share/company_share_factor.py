"""
src/domain/entities/factor/finance/financial_assets/share_factor/company_share/company_share_factor.py

CompanyShare Factor domain entity - follows unified factor pattern and mirrors IndexFactor structure.
"""

from __future__ import annotations
from typing import Optional
from ..share_factor import ShareFactor


class CompanyShareFactor(ShareFactor):
    """Domain entity representing a company share-specific factor."""

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