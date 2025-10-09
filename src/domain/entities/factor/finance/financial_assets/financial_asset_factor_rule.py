"""
Domain entity for FinancialAssetFactorRule.
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict
from domain.entities.factor.factor_rule import FactorRule


@dataclass
class FinancialAssetFactorRule(FactorRule):
    """
    Domain entity representing a financial asset-specific factor rule.
    Extends base FactorRule with financial asset business logic.
    """
    asset_class: Optional[str] = None  # e.g., "equity", "bond", "commodity", "currency"
    market_segment: Optional[str] = None  # e.g., "large_cap", "small_cap", "emerging", "developed"
    risk_profile: Optional[str] = None  # e.g., "low", "medium", "high"

    def evaluate_market_context(self, asset_data: Any, context: Optional[Dict] = None) -> bool:
        """
        Evaluate rule considering financial market context.
        """
        if not context:
            context = {}
        
        # Add financial asset-specific context
        context['asset_class'] = self.asset_class
        context['market_segment'] = self.market_segment
        context['risk_profile'] = self.risk_profile
        
        return super().evaluate(asset_data, context)

    def apply_market_transformation(self, value: Any, market_context: Optional[Dict] = None) -> Any:
        """
        Apply financial market-specific transformations to factor values.
        """
        if not self.is_transformation_rule():
            raise ValueError("Cannot apply transformation on non-transformation rule")
        
        if not market_context:
            market_context = {}
        
        # Add market context
        market_context['asset_class'] = self.asset_class
        market_context['market_segment'] = self.market_segment
        
        return super().apply_transformation(value, market_context)

    def is_applicable_for_risk_profile(self, target_risk: str) -> bool:
        """Check if this rule applies to the specified risk profile."""
        return self.risk_profile == target_risk if self.risk_profile else True

    def __str__(self) -> str:
        return f"FinancialAssetFactorRule(id={self.id}, factor_id={self.factor_id}, asset_class={self.asset_class})"