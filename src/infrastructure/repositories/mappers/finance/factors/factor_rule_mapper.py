"""
Mapper for converting between FactorRule domain entities and ORM models.
"""

from typing import Optional
from src.domain.entities.finance.factors.factor_rule import FactorRule as FactorRuleEntity
from src.infrastructure.models.finance.factor_model import FactorRule as FactorRuleModel


class FactorRuleMapper:
    """Mapper for FactorRule domain entity and ORM model conversion."""

    @staticmethod
    def to_domain(orm_model: Optional[FactorRuleModel]) -> Optional[FactorRuleEntity]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None
        
        return FactorRuleEntity(
            id=orm_model.id,
            factor_id=orm_model.factor_id,
            condition=orm_model.condition,
            rule_type=orm_model.rule_type,
            method_ref=orm_model.method_ref
        )

    @staticmethod
    def to_orm(domain_entity: FactorRuleEntity) -> FactorRuleModel:
        """Convert domain entity to ORM model."""
        return FactorRuleModel(
            id=domain_entity.id,
            factor_id=domain_entity.factor_id,
            condition=domain_entity.condition,
            rule_type=domain_entity.rule_type,
            method_ref=domain_entity.method_ref
        )