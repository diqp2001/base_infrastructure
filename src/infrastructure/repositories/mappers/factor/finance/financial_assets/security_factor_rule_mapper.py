"""
Mapper for converting between SecurityFactorRule domain entities and ORM models.
"""

from typing import Optional
from domain.entities.factor.finance.financial_assets.security_factor_rule import SecurityFactorRule as SecurityFactorRuleEntity
from infrastructure.models.factor.finance.financial_assets.security_factors import SecurityFactorRule as SecurityFactorRuleModel


class SecurityFactorRuleMapper:
    """Mapper for SecurityFactorRule domain entity and ORM model conversion."""

    @staticmethod
    def to_domain(orm_model: Optional[SecurityFactorRuleModel]) -> Optional[SecurityFactorRuleEntity]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None
        
        return SecurityFactorRuleEntity(
            id=orm_model.id,
            factor_id=orm_model.factor_id,
            condition=orm_model.condition,
            rule_type=orm_model.rule_type,
            method_ref=orm_model.method_ref,
            # Inherit from FinancialAssetFactorRule
            asset_class="security",
            market_segment=None,  # Could be extracted from condition if needed
            risk_profile=None,    # Could be extracted from condition if needed
            # SecurityFactorRule specific fields - would need to be extracted from condition or method_ref
            security_type="security",  # Default
            exchange=None,             # Could be extracted from condition if needed
            sector=None                # Could be extracted from condition if needed
        )

    @staticmethod
    def to_orm(domain_entity: SecurityFactorRuleEntity) -> SecurityFactorRuleModel:
        """Convert domain entity to ORM model."""
        return SecurityFactorRuleModel(
            id=domain_entity.id,
            factor_id=domain_entity.factor_id,
            condition=domain_entity.condition,
            rule_type=domain_entity.rule_type,
            method_ref=domain_entity.method_ref
        )