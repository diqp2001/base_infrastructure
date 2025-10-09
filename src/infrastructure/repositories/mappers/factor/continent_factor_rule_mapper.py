"""
Mapper for converting between ContinentFactorRule domain entities and ORM models.
"""

from typing import Optional
from domain.entities.factor.continent_factor_rule import ContinentFactorRule as ContinentFactorRuleEntity
from infrastructure.models.factor.factor_model import FactorRule as FactorRuleModel


class ContinentFactorRuleMapper:
    """Mapper for ContinentFactorRule domain entity and ORM model conversion."""

    @staticmethod
    def to_domain(orm_model: Optional[FactorRuleModel]) -> Optional[ContinentFactorRuleEntity]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None
        
        return ContinentFactorRuleEntity(
            id=orm_model.id,
            factor_id=orm_model.factor_id,
            condition=orm_model.condition,
            rule_type=orm_model.rule_type,
            method_ref=orm_model.method_ref,
            # ContinentFactorRule specific fields - would need to be extracted from condition or method_ref
            continent_specific=None  # Could be extracted from condition if needed
        )

    @staticmethod
    def to_orm(domain_entity: ContinentFactorRuleEntity) -> FactorRuleModel:
        """Convert domain entity to ORM model."""
        return FactorRuleModel(
            id=domain_entity.id,
            factor_id=domain_entity.factor_id,
            condition=domain_entity.condition,
            rule_type=domain_entity.rule_type,
            method_ref=domain_entity.method_ref
        )