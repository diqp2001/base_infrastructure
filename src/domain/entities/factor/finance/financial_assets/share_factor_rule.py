"""
Domain entity for ShareFactorRule.
"""

from dataclasses import dataclass
from typing import Optional, Any, Dict
from domain.entities.factor.finance.financial_assets.equity_factor_rule import EquityFactorRule


@dataclass
class ShareFactorRule(EquityFactorRule):
    """
    Domain entity representing a share-specific factor rule.
    Extends EquityFactorRule with share-specific business logic.
    """
    share_class: Optional[str] = None  # e.g., "A", "B", "C" for different voting rights
    voting_rights: Optional[str] = None  # e.g., "voting", "non_voting", "super_voting"
    listing_status: Optional[str] = None  # e.g., "primary", "secondary", "otc"
    
    def evaluate_share_context(self, share_data: Any, context: Optional[Dict] = None) -> bool:
        """
        Evaluate rule considering share-specific context.
        """
        if not context:
            context = {}
        
        # Add share-specific context
        context['share_class'] = self.share_class
        context['voting_rights'] = self.voting_rights
        context['listing_status'] = self.listing_status
        
        return super().evaluate_equity_context(share_data, context)

    def apply_voting_transformation(self, value: Any, voting_context: Optional[Dict] = None) -> Any:
        """
        Apply voting rights-specific transformations.
        """
        if not self.is_transformation_rule():
            raise ValueError("Cannot apply transformation on non-transformation rule")
        
        if not voting_context:
            voting_context = {}
        
        # Add voting context
        voting_context['voting_rights'] = self.voting_rights
        voting_context['share_class'] = self.share_class
        
        return super().apply_dividend_transformation(value, voting_context)

    def is_applicable_for_share_class(self, target_class: str) -> bool:
        """Check if this rule applies to the specified share class."""
        return self.share_class == target_class if self.share_class else True

    def has_voting_rights(self) -> bool:
        """Check if shares have voting rights."""
        return self.voting_rights != "non_voting" if self.voting_rights else True

    def is_primary_listing(self) -> bool:
        """Check if this is a primary listing."""
        return self.listing_status == "primary" if self.listing_status else True

    def get_voting_multiplier(self) -> int:
        """Get voting power multiplier based on voting rights."""
        if self.voting_rights == "super_voting":
            return 10  # Super voting shares typically have 10x voting power
        elif self.voting_rights == "voting":
            return 1
        else:  # non_voting
            return 0

    def __str__(self) -> str:
        return f"ShareFactorRule(id={self.id}, factor_id={self.factor_id}, share_class={self.share_class}, voting_rights={self.voting_rights})"