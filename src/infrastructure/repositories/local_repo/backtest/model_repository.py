from typing import List, Optional
from sqlalchemy.orm import Session

from src.infrastructure.models.backtest.model import ModelModel
from src.domain.entities.backtest.model import Model
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.backtest.model_mapper import ModelMapper
from src.domain.ports.backtest.model_port import ModelPort


class ModelRepository(BaseLocalRepository, ModelPort):

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = ModelMapper()

    @property
    def model_class(self):
        return ModelModel

    @property
    def entity_class(self):
        return Model

    def _to_entity(self, orm_obj) -> Optional[Model]:
        return self.mapper.to_domain(orm_obj)

    def _to_model(self, entity: Model) -> ModelModel:
        return self.mapper.to_orm(entity)

    def get_all(self) -> List[Model]:
        return [self._to_entity(m) for m in self.session.query(ModelModel).all()]

    def get_by_id(self, id: int) -> Optional[Model]:
        return self._to_entity(
            self.session.query(ModelModel).filter(ModelModel.id == id).first()
        )

    def get_by_name(self, name: str) -> Optional[Model]:
        return self._to_entity(
            self.session.query(ModelModel).filter(ModelModel.name == name).first()
        )

    def add(self, entity: Model) -> Optional[Model]:
        existing = self.get_by_name(entity.name)
        if existing:
            return existing
        orm_obj = self._to_model(entity)
        self.session.add(orm_obj)
        self.session.commit()
        return self._to_entity(orm_obj)

    def update(self, entity: Model) -> Optional[Model]:
        orm_obj = self.session.query(ModelModel).filter(ModelModel.id == entity.id).first()
        if not orm_obj:
            return None
        orm_obj.name = entity.name
        self.session.commit()
        return self._to_entity(orm_obj)

    def delete(self, id: int) -> bool:
        orm_obj = self.session.query(ModelModel).filter(ModelModel.id == id).first()
        if not orm_obj:
            return False
        self.session.delete(orm_obj)
        self.session.commit()
        return True

    def _create_or_get(self, name: str) -> Optional[Model]:
        try:
            existing = self.get_by_name(name)
            if existing:
                return existing
            return self.add(Model(id=None, name=name))
        except Exception as e:
            print(f"Error in _create_or_get for Model '{name}': {e}")
            return None
