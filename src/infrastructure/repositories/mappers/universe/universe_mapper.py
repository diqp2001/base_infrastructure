"""
src/infrastructure/repositories/mappers/universe/universe_mapper.py

Mapper between Universe domain entity and UniverseModel ORM model.
"""

from typing import Optional
from src.domain.entities.universe.universe import Universe
from src.infrastructure.models.universe.universe import UniverseModel


class UniverseMapper:

    def to_domain(self, orm: Optional[UniverseModel]) -> Optional[Universe]:
        if not orm:
            return None
        return Universe(
            id=orm.id,
            name=orm.name,
            description=orm.description,
            entity_type=orm.entity_type,
            currency_id=orm.currency_id,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def to_orm(self, entity: Universe) -> UniverseModel:
        return UniverseModel(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            entity_type=entity.entity_type,
            currency_id=entity.currency_id,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @property
    def model_class(self):
        return UniverseModel
