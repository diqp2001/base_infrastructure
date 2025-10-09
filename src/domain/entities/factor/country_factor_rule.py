"""
Domain entity for CountryFactorRule.
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict
from domain.entities.factor.factor_rule import FactorRule


@dataclass
class CountryFactorRule(FactorRule):
    """
    Domain entity representing a country-specific factor rule.
    Extends base FactorRule with country-specific business logic.
    """
    country_code: Optional[str] = None  # e.g., "US", "CA", "GB", "JP", "DE"
    currency_impact: Optional[str] = None  # e.g., "USD", "EUR", "JPY"
    regulatory_region: Optional[str] = None  # e.g., "SEC", "ESMA", "FSA"

    def __post_init__(self):
        """Validate domain constraints including country-specific ones."""
        super().__post_init__()
        
        if self.country_code and len(self.country_code) != 2:
            raise ValueError("country_code should be a 2-character ISO code")

    def evaluate_country_context(self, country_data: Any, context: Optional[Dict] = None) -> bool:
        """
        Evaluate rule considering country-specific context.
        """
        if not context:
            context = {}
        
        # Add country-specific context to evaluation
        context['country_code'] = self.country_code
        context['currency_impact'] = self.currency_impact
        context['regulatory_region'] = self.regulatory_region
        
        return super().evaluate(country_data, context)

    def apply_regulatory_transformation(self, value: Any, regulatory_context: Optional[Dict] = None) -> Any:
        """
        Apply country-specific regulatory transformations to factor values.
        """
        if not self.is_transformation_rule():
            raise ValueError("Cannot apply transformation on non-transformation rule")
        
        if not regulatory_context:
            regulatory_context = {}
        
        # Add regulatory context
        regulatory_context['regulatory_region'] = self.regulatory_region
        regulatory_context['country_code'] = self.country_code
        
        return super().apply_transformation(value, regulatory_context)

    def is_applicable_for_country(self, target_country_code: str) -> bool:
        """Check if this rule is applicable for the specified country."""
        return self.country_code == target_country_code if self.country_code else True

    def __str__(self) -> str:
        return f"CountryFactorRule(id={self.id}, factor_id={self.factor_id}, country_code={self.country_code})"