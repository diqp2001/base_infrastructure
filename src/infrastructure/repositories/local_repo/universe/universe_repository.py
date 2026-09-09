"""
src/infrastructure/repositories/local_repo/universe/universe_repository.py

Local SQLAlchemy repository for Universe.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from src.domain.entities.universe.universe import Universe
from src.domain.ports.universe.universe_port import UniversePort
from src.infrastructure.repositories.mappers.universe.universe_mapper import UniverseMapper
from src.infrastructure.models.universe.universe import UniverseModel


class UniverseRepository(UniversePort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = UniverseMapper()

    @property
    def model_class(self):
        return UniverseModel

    def _to_entity(self, orm) -> Optional[Universe]:
        return self.mapper.to_domain(orm)

    def _to_model(self, entity: Universe) -> UniverseModel:
        return self.mapper.to_orm(entity)

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[Universe]:
        try:
            existing = self.get_by_name(primary_key)
            if existing:
                return existing

            now = datetime.utcnow()
            orm = UniverseModel(
                name=primary_key,
                description=kwargs.get("description"),
                entity_type=kwargs.get("entity_type"),
                currency_id=kwargs.get("currency_id"),
                created_at=now,
                updated_at=now,
            )
            self.session.add(orm)
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error in Universe._create_or_get for '{primary_key}': {e}")
            self.session.rollback()
            return None

    def get_by_id(self, id: int) -> Optional[Universe]:
        orm = self.session.query(UniverseModel).filter(UniverseModel.id == id).one_or_none()
        return self._to_entity(orm)

    def get_by_name(self, name: str) -> Optional[Universe]:
        orm = self.session.query(UniverseModel).filter(UniverseModel.name == name).one_or_none()
        return self._to_entity(orm)

    def get_all(self) -> List[Universe]:
        return [self._to_entity(o) for o in self.session.query(UniverseModel).all()]

    def add(self, entity: Universe) -> Optional[Universe]:
        try:
            orm = self._to_model(entity)
            self.session.add(orm)
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error adding Universe: {e}")
            self.session.rollback()
            return None

    def update(self, entity: Universe) -> Optional[Universe]:
        try:
            orm = self.session.query(UniverseModel).filter(UniverseModel.id == entity.id).one_or_none()
            if not orm:
                return None
            orm.name = entity.name
            orm.description = entity.description
            orm.entity_type = entity.entity_type
            orm.currency_id = entity.currency_id
            orm.updated_at = datetime.utcnow()
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error updating Universe {entity.id}: {e}")
            self.session.rollback()
            return None

    def delete(self, id: int) -> bool:
        try:
            orm = self.session.query(UniverseModel).filter(UniverseModel.id == id).one_or_none()
            if not orm:
                return False
            self.session.delete(orm)
            self.session.commit()
            return True
        except Exception as e:
            print(f"Error deleting Universe {id}: {e}")
            self.session.rollback()
            return False
