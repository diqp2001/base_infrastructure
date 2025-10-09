"""
Domain entity for EquityFactorRule.
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict
from domain.entities.factor.finance.financial_assets.security_factor_rule import SecurityFactorRule


@dataclass
class EquityFactorRule(SecurityFactorRule):
    """
    Domain entity representing an equity-specific factor rule.
    Extends SecurityFactorRule with equity-specific business logic.
    """
    equity_type: Optional[str] = None  # e.g., "common", "preferred", "reit"
    market_cap_category: Optional[str] = None  # e.g., "large_cap", "mid_cap", "small_cap", "micro_cap"
    dividend_policy: Optional[str] = None  # e.g., "dividend_paying", "growth", "value"
    
    def evaluate_equity_context(self, equity_data: Any, context: Optional[Dict] = None) -> bool:
        """
        Evaluate rule considering equity-specific context.
        """
        if not context:
            context = {}
        
        # Add equity-specific context
        context['equity_type'] = self.equity_type
        context['market_cap_category'] = self.market_cap_category
        context['dividend_policy'] = self.dividend_policy
        
        return super().evaluate_security_context(equity_data, context)

    def apply_dividend_transformation(self, value: Any, dividend_context: Optional[Dict] = None) -> Any:
        """
        Apply dividend-specific transformations (e.g., ex-dividend adjustments).
        """
        if not self.is_transformation_rule():
            raise ValueError("Cannot apply transformation on non-transformation rule")
        
        if not dividend_context:
            dividend_context = {}
        
        # Add dividend context
        dividend_context['dividend_policy'] = self.dividend_policy
        dividend_context['equity_type'] = self.equity_type
        
        return super().apply_exchange_transformation(value, dividend_context)

    def is_applicable_for_market_cap(self, market_cap_value: float) -> bool:
        """Check if this rule applies based on market cap category."""
        if not self.market_cap_category:
            return True
        
        # Define market cap thresholds (in billions USD)
        if self.market_cap_category == "large_cap":
            return market_cap_value >= 10.0
        elif self.market_cap_category == "mid_cap":
            return 2.0 <= market_cap_value < 10.0
        elif self.market_cap_category == "small_cap":
            return 0.3 <= market_cap_value < 2.0
        elif self.market_cap_category == "micro_cap":
            return market_cap_value < 0.3
        
        return True

    def is_dividend_applicable(self) -> bool:
        """Check if dividend-related rules apply to this equity."""
        return self.dividend_policy == "dividend_paying"

    def __str__(self) -> str:
        return f"EquityFactorRule(id={self.id}, factor_id={self.factor_id}, equity_type={self.equity_type}, market_cap_category={self.market_cap_category})"