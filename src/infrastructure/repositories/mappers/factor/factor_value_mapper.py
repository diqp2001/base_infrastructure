"""
Mapper for converting between FactorValue domain entities and ORM models.
"""

from abc import abstractmethod
from typing import Optional
from src.domain.entities.factor.factor_value import FactorValue as FactorValueEntity
from src.infrastructure.models.factor.factor_value import FactorValue as FactorValueModel


class FactorValueMapper:
    """Mapper for FactorValue domain entity and ORM model conversion."""
    @abstractmethod
    def get_factor_value_model(self):
        return FactorValueModel
    
    @abstractmethod
    def get_factor_value_entity(self):
        return FactorValueEntity
    
    @staticmethod
    def to_domain(orm_model: Optional[FactorValueModel]) -> Optional[FactorValueEntity]:
        """Convert ORM model to domain entity."""
        if not orm_model:
            return None
        
        return FactorValueEntity(
            id=orm_model.id,
            factor_id=orm_model.factor_id,
            entity_id=orm_model.entity_id,
            date=orm_model.date,
            value= orm_model.value if orm_model.value is not None else '0'
        )

    @staticmethod
    def to_orm(domain_entity: FactorValueEntity) -> FactorValueModel:
        """Convert domain entity to ORM model."""
        return FactorValueModel(
            id=domain_entity.id,
            factor_id=domain_entity.factor_id,
            entity_id=domain_entity.entity_id,
            date=domain_entity.date,
            value=domain_entity.value
        )