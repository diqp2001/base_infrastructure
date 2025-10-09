"""
Mapper for converting between ShareFactorRule domain entities and ORM models.
"""

from typing import Optional
from domain.entities.factor.finance.financial_assets.share_factor_rule import ShareFactorRule as ShareFactorRuleEntity
from infrastructure.models.factor.finance.financial_assets.share_factors import ShareFactorRule as ShareFactorRuleModel


class ShareFactorRuleMapper:
    """Mapper for ShareFactorRule domain entity and ORM model conversion."""

    @staticmethod
    def to_domain(orm_model: Optional[ShareFactorRuleModel]) -> Optional[ShareFactorRuleEntity]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None
        
        return ShareFactorRuleEntity(
            id=orm_model.id,
            factor_id=orm_model.factor_id,
            condition=orm_model.condition,
            rule_type=orm_model.rule_type,
            method_ref=orm_model.method_ref,
            # Inherit from EquityFactorRule
            asset_class="equity",
            market_segment=None,  # Could be extracted from condition if needed
            risk_profile=None,    # Could be extracted from condition if needed
            security_type="stock",
            exchange=None,        # Could be extracted from condition if needed
            sector=None,          # Could be extracted from condition if needed
            equity_type="common", # Default assumption for shares
            market_cap_category=None,  # Could be extracted from condition if needed
            dividend_policy=None,      # Could be extracted from condition if needed
            # ShareFactorRule specific fields - would need to be extracted from condition or method_ref
            share_class=None,
            voting_rights=None,
            listing_status=None
        )

    @staticmethod
    def to_orm(domain_entity: ShareFactorRuleEntity) -> ShareFactorRuleModel:
        """Convert domain entity to ORM model."""
        return ShareFactorRuleModel(
            id=domain_entity.id,
            factor_id=domain_entity.factor_id,
            condition=domain_entity.condition,
            rule_type=domain_entity.rule_type,
            method_ref=domain_entity.method_ref
        )