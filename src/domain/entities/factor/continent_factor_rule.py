"""
Domain entity for ContinentFactorRule.
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict
from domain.entities.factor.factor_rule import FactorRule


@dataclass
class ContinentFactorRule(FactorRule):
    """
    Domain entity representing a continent-specific factor rule.
    Extends base FactorRule with continent-specific business logic.
    """
    continent_specific: Optional[str] = None  # e.g., "geographic_zone", "time_zone_adjustment"

    def evaluate_continent_context(self, continent_data: Any, context: Optional[Dict] = None) -> bool:
        """
        Evaluate rule considering continent-specific context.
        """
        if not context:
            context = {}
        
        # Add continent-specific evaluation logic here
        # For now, delegate to base evaluation
        return super().evaluate(continent_data, context)

    def apply_continent_transformation(self, value: Any, continent_context: Optional[Dict] = None) -> Any:
        """
        Apply continent-specific transformations to factor values.
        """
        if not self.is_transformation_rule():
            raise ValueError("Cannot apply transformation on non-transformation rule")
        
        if not continent_context:
            continent_context = {}
        
        # Apply continent-specific transformations
        # For now, delegate to base transformation
        return super().apply_transformation(value, continent_context)

    def __str__(self) -> str:
        return f"ContinentFactorRule(id={self.id}, factor_id={self.factor_id}, continent_specific={self.continent_specific})"