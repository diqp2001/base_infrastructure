"""
Mapper for converting between ContinentFactorValue domain entities and ORM models.
"""

from typing import Optional
from decimal import Decimal
from domain.entities.factor.continent_factor_value import ContinentFactorValue as ContinentFactorValueEntity
from infrastructure.models.factor.factor_model import FactorValue as FactorValueModel


class ContinentFactorValueMapper:
    """Mapper for ContinentFactorValue domain entity and ORM model conversion."""

    @staticmethod
    def to_domain(orm_model: Optional[FactorValueModel]) -> Optional[ContinentFactorValueEntity]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None
        
        return ContinentFactorValueEntity(
            id=orm_model.id,
            factor_id=orm_model.factor_id,
            entity_id=orm_model.entity_id,
            date=orm_model.date,
            value=Decimal(str(orm_model.value)) if orm_model.value is not None else Decimal('0'),
            # ContinentFactorValue specific fields - would typically come from other sources or entity data
            continent_code=None,   # Would be determined from the entity or factor metadata
            geographic_zone=None   # Would be determined from the continent_code or entity
        )

    @staticmethod
    def to_orm(domain_entity: ContinentFactorValueEntity) -> FactorValueModel:
        """Convert domain entity to ORM model."""
        return FactorValueModel(
            id=domain_entity.id,
            factor_id=domain_entity.factor_id,
            entity_id=domain_entity.entity_id,
            date=domain_entity.date,
            value=domain_entity.value
        )