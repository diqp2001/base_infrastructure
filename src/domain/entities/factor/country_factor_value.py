"""
Domain entity for CountryFactorValue.
"""

from __future__ import annotations
from decimal import Decimal
from typing import Optional
from .factor import Factor


class CountryFactor(Factor):
    """
    Domain entity representing a country-specific factor value.
    Extends base FactorValue with country-specific business logic.
    """
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
        geographic_zone: Optional[str] = None,
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
        self.country_code = country_code  # e.g., "NA", "EU", "AS", "AF", "SA", "OC", "AN"
        self.geographic_zone = geographic_zone  # e.g., "northern", "southern", "tropical"



