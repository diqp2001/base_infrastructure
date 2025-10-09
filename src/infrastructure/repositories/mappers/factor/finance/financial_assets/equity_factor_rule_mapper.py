"""
Mapper for converting between EquityFactorRule domain entities and ORM models.
"""

from typing import Optional
from domain.entities.factor.finance.financial_assets.equity_factor_rule import EquityFactorRule as EquityFactorRuleEntity
from infrastructure.models.factor.finance.financial_assets.equity_factors import EquityFactorRule as EquityFactorRuleModel


class EquityFactorRuleMapper:
    """Mapper for EquityFactorRule domain entity and ORM model conversion."""

    @staticmethod
    def to_domain(orm_model: Optional[EquityFactorRuleModel]) -> Optional[EquityFactorRuleEntity]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None
        
        return EquityFactorRuleEntity(
            id=orm_model.id,
            factor_id=orm_model.factor_id,
            condition=orm_model.condition,
            rule_type=orm_model.rule_type,
            method_ref=orm_model.method_ref,
            # Inherit from SecurityFactorRule
            asset_class="equity",
            market_segment=None,  # Could be extracted from condition if needed
            risk_profile=None,    # Could be extracted from condition if needed
            security_type="equity",
            exchange=None,        # Could be extracted from condition if needed
            sector=None,          # Could be extracted from condition if needed
            # EquityFactorRule specific fields - would need to be extracted from condition or method_ref
            equity_type="common", # Default assumption
            market_cap_category=None,  # Could be extracted from condition if needed
            dividend_policy=None       # Could be extracted from condition if needed
        )

    @staticmethod
    def to_orm(domain_entity: EquityFactorRuleEntity) -> EquityFactorRuleModel:
        """Convert domain entity to ORM model."""
        return EquityFactorRuleModel(
            id=domain_entity.id,
            factor_id=domain_entity.factor_id,
            condition=domain_entity.condition,
            rule_type=domain_entity.rule_type,
            method_ref=domain_entity.method_ref
        )