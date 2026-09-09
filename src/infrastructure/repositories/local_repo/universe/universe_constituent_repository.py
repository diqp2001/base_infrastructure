"""
src/infrastructure/repositories/local_repo/universe/universe_constituent_repository.py

Local SQLAlchemy repository for UniverseConstituent.
"""

from datetime import date, datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from src.domain.entities.universe.universe_constituent import UniverseConstituent
from src.domain.ports.universe.universe_constituent_port import UniverseConstituentPort
from src.infrastructure.repositories.mappers.universe.universe_constituent_mapper import UniverseConstituentMapper
from src.infrastructure.models.universe.universe_constituent import UniverseConstituentModel


class UniverseConstituentRepository(UniverseConstituentPort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = UniverseConstituentMapper()

    @property
    def model_class(self):
        return UniverseConstituentModel

    def _to_entity(self, orm) -> Optional[UniverseConstituent]:
        return self.mapper.to_domain(orm)

    def _to_model(self, entity: UniverseConstituent) -> UniverseConstituentModel:
        return self.mapper.to_orm(entity)

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[UniverseConstituent]:
        """
        primary_key is unused; uniqueness is on (universe_id, entity_id, entity_type, start_date).
        """
        try:
            universe_id = kwargs.get("universe_id")
            entity_id   = kwargs.get("entity_id")
            entity_type = kwargs.get("entity_type")
            start_date  = kwargs.get("start_date")

            existing = (
                self.session.query(UniverseConstituentModel)
                .filter(
                    UniverseConstituentModel.universe_id == universe_id,
                    UniverseConstituentModel.entity_id   == entity_id,
                    UniverseConstituentModel.entity_type == entity_type,
                    UniverseConstituentModel.start_date  == start_date,
                )
                .one_or_none()
            )
            if existing:
                return self._to_entity(existing)

            now = datetime.utcnow()
            orm = UniverseConstituentModel(
                universe_id=universe_id,
                entity_id=entity_id,
                entity_type=entity_type,
                start_date=start_date,
                end_date=kwargs.get("end_date"),
                weight=kwargs.get("weight"),
                created_at=now,
                updated_at=now,
            )
            self.session.add(orm)
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error in UniverseConstituent._create_or_get: {e}")
            self.session.rollback()
            return None

    def get_by_id(self, id: int) -> Optional[UniverseConstituent]:
        orm = (
            self.session.query(UniverseConstituentModel)
            .filter(UniverseConstituentModel.id == id)
            .one_or_none()
        )
        return self._to_entity(orm)

    def get_by_universe(self, universe_id: int) -> List[UniverseConstituent]:
        rows = (
            self.session.query(UniverseConstituentModel)
            .filter(UniverseConstituentModel.universe_id == universe_id)
            .all()
        )
        return [self._to_entity(r) for r in rows]

    def get_active_by_universe(self, universe_id: int, as_of: date) -> List[UniverseConstituent]:
        """Return constituents active on `as_of` date (start_date <= as_of and end_date is None or > as_of)."""
        rows = (
            self.session.query(UniverseConstituentModel)
            .filter(
                UniverseConstituentModel.universe_id == universe_id,
                UniverseConstituentModel.start_date  <= as_of,
                (
                    (UniverseConstituentModel.end_date == None) |
                    (UniverseConstituentModel.end_date > as_of)
                ),
            )
            .all()
        )
        return [self._to_entity(r) for r in rows]

    def get_by_entity(self, entity_id: int, entity_type: str) -> List[UniverseConstituent]:
        rows = (
            self.session.query(UniverseConstituentModel)
            .filter(
                UniverseConstituentModel.entity_id   == entity_id,
                UniverseConstituentModel.entity_type == entity_type,
            )
            .all()
        )
        return [self._to_entity(r) for r in rows]

    def get_all(self) -> List[UniverseConstituent]:
        return [self._to_entity(o) for o in self.session.query(UniverseConstituentModel).all()]

    def add(self, entity: UniverseConstituent) -> Optional[UniverseConstituent]:
        try:
            orm = self._to_model(entity)
            self.session.add(orm)
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error adding UniverseConstituent: {e}")
            self.session.rollback()
            return None

    def update(self, entity: UniverseConstituent) -> Optional[UniverseConstituent]:
        try:
            orm = (
                self.session.query(UniverseConstituentModel)
                .filter(UniverseConstituentModel.id == entity.id)
                .one_or_none()
            )
            if not orm:
                return None
            orm.end_date   = entity.end_date
            orm.weight     = entity.weight
            orm.updated_at = datetime.utcnow()
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error updating UniverseConstituent {entity.id}: {e}")
            self.session.rollback()
            return None

    def delete(self, id: int) -> bool:
        try:
            orm = (
                self.session.query(UniverseConstituentModel)
                .filter(UniverseConstituentModel.id == id)
                .one_or_none()
            )
            if not orm:
                return False
            self.session.delete(orm)
            self.session.commit()
            return True
        except Exception as e:
            print(f"Error deleting UniverseConstituent {id}: {e}")
            self.session.rollback()
            return False
