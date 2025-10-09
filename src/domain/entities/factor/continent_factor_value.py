"""
Domain entity for ContinentFactorValue.
"""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional
from domain.entities.factor.factor_value import FactorValue


@dataclass
class ContinentFactorValue(FactorValue):
    """
    Domain entity representing a continent-specific factor value.
    Extends base FactorValue with continent-specific business logic.
    """
    continent_code: Optional[str] = None  # e.g., "NA", "EU", "AS", "AF", "SA", "OC", "AN"
    geographic_zone: Optional[str] = None  # e.g., "northern", "southern", "tropical"

    def __post_init__(self):
        """Validate domain constraints including continent-specific ones."""
        super().__post_init__()
        
        if self.continent_code and len(self.continent_code) > 5:
            raise ValueError("continent_code should be a short identifier (max 5 chars)")

    def is_in_hemisphere(self, hemisphere: str) -> bool:
        """Check if this continent factor value is in the specified hemisphere."""
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

    def adjust_for_continent(self, continent_multiplier: Decimal) -> 'ContinentFactorValue':
        """Create a new ContinentFactorValue with continent-specific adjustment."""
        return ContinentFactorValue(
            id=self.id,
            factor_id=self.factor_id,
            entity_id=self.entity_id,
            date=self.date,
            value=self.value * continent_multiplier,
            continent_code=self.continent_code,
            geographic_zone=self.geographic_zone
        )

    def __str__(self) -> str:
        return f"ContinentFactorValue(factor_id={self.factor_id}, entity_id={self.entity_id}, continent_code={self.continent_code}, value={self.value})"