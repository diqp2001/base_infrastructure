"""
src/domain/entities/factor/continent_factor.py

ContinentFactor domain entity - follows unified factor pattern.
"""

from __future__ import annotations
from typing import Optional
from .factor import Factor


class ContinentFactor(Factor):
    """Domain entity representing a continent-specific factor."""

    def __init__(
        self,
        name: str,
        group: str,
        subgroup: Optional[str] = None,
        data_type: Optional[str] = None,
        source: Optional[str] = None,
        definition: Optional[str] = None,
        factor_id: Optional[int] = None,
        
        continent_code: Optional[str] = None,
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
        self.continent_code = continent_code  # e.g., "NA", "EU", "AS", "AF", "SA", "OC", "AN"
        self.geographic_zone = geographic_zone  # e.g., "northern", "southern", "tropical"

    def is_in_hemisphere(self, hemisphere: str) -> bool:
        """Check if this continent factor is in the specified hemisphere."""
        hemisphere_mapping = {
            "NA": "northern",  # North America
            "EU": "northern",  # Europe
            "AS": "northern",  # Asia (mostly)
            "AF": "both",      # Africa (crosses equator)
            "SA": "southern",  # South America (mostly)
            "OC": "southern",  # Oceania (mostly)
            "AN": "southern"   # Antarctica
        }
        
        if not self.continent_code:
            return False
        
        continent_hemisphere = hemisphere_mapping.get(self.continent_code, "unknown")
        return hemisphere.lower() == continent_hemisphere or continent_hemisphere == "both"
