from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session

from src.infrastructure.models.backtest.universe import UniverseModel
from src.domain.entities.backtest.universe import Universe
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.backtest.universe_mapper import UniverseMapper
from src.domain.ports.backtest.universe_port import UniversePort


class UniverseRepository(BaseLocalRepository, UniversePort):

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = UniverseMapper()

    @property
    def model_class(self):
        return UniverseModel

    @property
    def entity_class(self):
        return Universe

    def _to_entity(self, orm_obj) -> Optional[Universe]:
        return self.mapper.to_domain(orm_obj)

    def _to_model(self, entity: Universe) -> UniverseModel:
        return self.mapper.to_orm(entity)

    def get_all(self) -> List[Universe]:
        return [self._to_entity(m) for m in self.session.query(UniverseModel).all()]

    def get_by_id(self, id: int) -> Optional[Universe]:
        return self._to_entity(
            self.session.query(UniverseModel).filter(UniverseModel.id == id).first()
        )

    def get_by_name(self, name: str) -> Optional[Universe]:
        return self._to_entity(
            self.session.query(UniverseModel).filter(UniverseModel.name == name).first()
        )

    def add(self, entity: Universe) -> Optional[Universe]:
        existing = self.get_by_name(entity.name)
        if existing:
            return existing
        orm_obj = self._to_model(entity)
        self.session.add(orm_obj)
        self.session.commit()
        return self._to_entity(orm_obj)

    def update(self, entity: Universe) -> Optional[Universe]:
        orm_obj = self.session.query(UniverseModel).filter(UniverseModel.id == entity.id).first()
        if not orm_obj:
            return None
        orm_obj.name = entity.name
        orm_obj.creation_date = entity.creation_date
        orm_obj.description = entity.description
        self.session.commit()
        return self._to_entity(orm_obj)

    def delete(self, id: int) -> bool:
        orm_obj = self.session.query(UniverseModel).filter(UniverseModel.id == id).first()
        if not orm_obj:
            return False
        self.session.delete(orm_obj)
        self.session.commit()
        return True

    def _create_or_get(self, name: str, **kwargs) -> Optional[Universe]:
        try:
            existing = self.get_by_name(name)
            if existing:
                return existing
            return self.add(Universe(
                id=None,
                name=name,
                creation_date=kwargs.get('creation_date', date.today()),
                description=kwargs.get('description'),
            ))
        except Exception as e:
            print(f"Error in _create_or_get for Universe '{name}': {e}")
            return None
