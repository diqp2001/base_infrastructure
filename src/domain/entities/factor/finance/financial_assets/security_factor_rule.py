"""
Domain entity for SecurityFactorRule.
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict
from domain.entities.factor.finance.financial_assets.financial_asset_factor_rule import FinancialAssetFactorRule


@dataclass
class SecurityFactorRule(FinancialAssetFactorRule):
    """
    Domain entity representing a security-specific factor rule.
    Extends FinancialAssetFactorRule with security-specific business logic.
    """
    security_type: Optional[str] = None  # e.g., "stock", "bond", "etf", "mutual_fund"
    exchange: Optional[str] = None  # e.g., "NYSE", "NASDAQ", "LSE", "TSE"
    sector: Optional[str] = None  # e.g., "technology", "healthcare", "financials"
    
    def evaluate_security_context(self, security_data: Any, context: Optional[Dict] = None) -> bool:
        """
        Evaluate rule considering security-specific context.
        """
        if not context:
            context = {}
        
        # Add security-specific context
        context['security_type'] = self.security_type
        context['exchange'] = self.exchange
        context['sector'] = self.sector
        
        return super().evaluate_market_context(security_data, context)

    def apply_exchange_transformation(self, value: Any, exchange_context: Optional[Dict] = None) -> Any:
        """
        Apply exchange-specific transformations (e.g., trading hours, currency).
        """
        if not self.is_transformation_rule():
            raise ValueError("Cannot apply transformation on non-transformation rule")
        
        if not exchange_context:
            exchange_context = {}
        
        # Add exchange context
        exchange_context['exchange'] = self.exchange
        exchange_context['security_type'] = self.security_type
        
        return super().apply_market_transformation(value, exchange_context)

    def is_applicable_for_exchange(self, target_exchange: str) -> bool:
        """Check if this rule applies to the specified exchange."""
        return self.exchange == target_exchange if self.exchange else True

    def is_applicable_for_sector(self, target_sector: str) -> bool:
        """Check if this rule applies to the specified sector."""
        return self.sector == target_sector if self.sector else True

    def __str__(self) -> str:
        return f"SecurityFactorRule(id={self.id}, factor_id={self.factor_id}, security_type={self.security_type}, exchange={self.exchange})"