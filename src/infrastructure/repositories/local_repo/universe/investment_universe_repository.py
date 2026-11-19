"""
src/infrastructure/repositories/local_repo/universe/investment_universe_repository.py

Local SQLAlchemy repository of InvestmentUniverse (child type of Universe: rows in universes + investment_universes).
Same behaviour as before the Universe hierarchy (2026-11-19): lookups by name, ``_create_or_get``, failures logged
and returned as None. Its point-in-time members are UniverseConstituent rows (UniverseConstituentRepository).
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from src.domain.entities.universe.investment_universe import InvestmentUniverse
from src.domain.entities.universe.universe import Universe
from src.domain.ports.universe.universe_port import UniversePort
from src.infrastructure.models.universe.universe import InvestmentUniverseModel
from src.infrastructure.repositories.mappers.universe.universe_mapper import InvestmentUniverseMapper


class InvestmentUniverseRepository(UniversePort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = InvestmentUniverseMapper()

    @property
    def model_class(self):
        return InvestmentUniverseModel

    @property
    def entity_class(self):
        return InvestmentUniverse

    def _to_entity(self, orm) -> Optional[InvestmentUniverse]:
        return self.mapper.to_domain(orm)

    def _to_model(self, entity: Universe) -> InvestmentUniverseModel:
        return self.mapper.to_orm(entity)

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[InvestmentUniverse]:
        try:
            existing = self.get_by_name(primary_key)
            if existing:
                return existing
            now = datetime.utcnow()
            orm = InvestmentUniverseModel(
                name=primary_key,
                description=kwargs.get("description"),
                entity_type=kwargs.get("entity_type"),
                currency_id=kwargs.get("currency_id"),
                version=kwargs.get("version", 1),
                created_at=now,
                updated_at=now,
            )
            self.session.add(orm)
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error in InvestmentUniverse._create_or_get for '{primary_key}': {e}")
            self.session.rollback()
            return None

    def get_by_id(self, id: int) -> Optional[InvestmentUniverse]:
        orm = self.session.query(InvestmentUniverseModel).filter(InvestmentUniverseModel.id == id).one_or_none()
        return self._to_entity(orm)

    def get_by_name(self, name: str) -> Optional[InvestmentUniverse]:
        orm = (self.session.query(InvestmentUniverseModel).filter(InvestmentUniverseModel.name == name)
               .order_by(InvestmentUniverseModel.version.desc()).first())
        return self._to_entity(orm)

    def get_all(self) -> List[InvestmentUniverse]:
        return [self._to_entity(o) for o in
                self.session.query(InvestmentUniverseModel).order_by(InvestmentUniverseModel.id).all()]

    def add(self, entity: Universe) -> Optional[InvestmentUniverse]:
        try:
            orm = self._to_model(entity)
            now = datetime.utcnow()
            orm.created_at = orm.created_at or now
            orm.updated_at = orm.updated_at or now
            self.session.add(orm)
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error adding InvestmentUniverse: {e}")
            self.session.rollback()
            return None

    def update(self, entity: Universe) -> Optional[InvestmentUniverse]:
        try:
            orm = (self.session.query(InvestmentUniverseModel)
                   .filter(InvestmentUniverseModel.id == entity.id).one_or_none())
            if not orm:
                return None
            created_at = orm.created_at
            self.mapper.copy_to_orm(entity, orm)
            orm.created_at = created_at
            orm.updated_at = datetime.utcnow()
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error updating InvestmentUniverse {entity.id}: {e}")
            self.session.rollback()
            return None

    def delete(self, id: int) -> bool:
        try:
            orm = self.session.query(InvestmentUniverseModel).filter(InvestmentUniverseModel.id == id).one_or_none()
            if not orm:
                return False
            self.session.delete(orm)
            self.session.commit()
            return True
        except Exception as e:
            print(f"Error deleting InvestmentUniverse {id}: {e}")
            self.session.rollback()
            return False
