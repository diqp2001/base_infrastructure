"""
Mapper for converting between FactorValue domain entities and ORM models.
"""

from abc import abstractmethod
from typing import Optional
from src.domain.entities.factor.factor_value import FactorValue as FactorValueEntity
from src.infrastructure.models.factor.factor_value import FactorValueModel as FactorValueModel


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
        """Convert ORM model to domain entity.

        entity is set to None because we do not eagerly load the full Entity
        object from the database; callers who need the rich entity object must
        resolve it separately.  entity_id and entity_type are carried directly
        from the ORM model so that queries remain unambiguous.
        """
        if not orm_model:
            return None

        return FactorValueEntity(
            id=orm_model.id,
            factor_id=orm_model.factor_id,
            entity=None,           # Not loaded from DB – use entity_id / entity_type
            date=orm_model.date,
            value=orm_model.value if orm_model.value is not None else '0',
            entity_type=orm_model.entity_type,
            entity_id=orm_model.entity_id,
        )

    @staticmethod
    def to_orm(domain_entity: FactorValueEntity) -> FactorValueModel:
        """Convert domain entity to ORM model."""
        # Resolve entity_id: prefer entity.id when entity object is available.
        resolved_entity_id = (
            domain_entity.entity.id
            if domain_entity.entity is not None
            else domain_entity.entity_id
        )

        # Resolve entity_type: prefer entity class name when entity is available.
        resolved_entity_type = (
            type(domain_entity.entity).__name__
            if domain_entity.entity is not None
            else domain_entity.entity_type
        )

        model_kwargs = {
            'factor_id': domain_entity.factor_id,
            'entity_id': resolved_entity_id,
            'entity_type': resolved_entity_type,
            'date': domain_entity.date,
            'value': domain_entity.value,
        }

        # Only include id if it's not None to allow auto-increment
        if domain_entity.id is not None:
            model_kwargs['id'] = domain_entity.id

        return FactorValueModel(**model_kwargs)
