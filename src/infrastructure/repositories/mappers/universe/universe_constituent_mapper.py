"""
src/infrastructure/repositories/mappers/universe/universe_constituent_mapper.py

Mapper between UniverseConstituent domain entity and UniverseConstituentModel ORM model.
"""

from typing import Optional
from src.domain.entities.universe.universe_constituent import UniverseConstituent
from src.infrastructure.models.universe.universe_constituent import UniverseConstituentModel


class UniverseConstituentMapper:

    def to_domain(self, orm: Optional[UniverseConstituentModel]) -> Optional[UniverseConstituent]:
        if not orm:
            return None
        return UniverseConstituent(
            id=orm.id,
            universe_id=orm.universe_id,
            entity_id=orm.entity_id,
            entity_type=orm.entity_type,
            start_date=orm.start_date,
            end_date=orm.end_date,
            weight=orm.weight,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def to_orm(self, entity: UniverseConstituent) -> UniverseConstituentModel:
        return UniverseConstituentModel(
            id=entity.id,
            universe_id=entity.universe_id,
            entity_id=entity.entity_id,
            entity_type=entity.entity_type,
            start_date=entity.start_date,
            end_date=entity.end_date,
            weight=entity.weight,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @property
    def model_class(self):
        return UniverseConstituentModel
