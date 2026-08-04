from datetime import date
from typing import List, Optional
from sqlalchemy.orm import Session

from src.infrastructure.models.backtest.backtest import BacktestModel
from src.domain.entities.backtest.backtest import Backtest
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.backtest.backtest_mapper import BacktestMapper
from src.domain.ports.backtest.backtest_port import BacktestPort


class BacktestRepository(BaseLocalRepository, BacktestPort):

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = BacktestMapper()

    @property
    def model_class(self):
        return BacktestModel

    @property
    def entity_class(self):
        return Backtest

    def _to_entity(self, orm_obj) -> Optional[Backtest]:
        return self.mapper.to_domain(orm_obj)

    def _to_model(self, entity: Backtest) -> BacktestModel:
        return self.mapper.to_orm(entity)

    def get_all(self) -> List[Backtest]:
        return [self._to_entity(m) for m in self.session.query(BacktestModel).all()]

    def get_by_id(self, id: int) -> Optional[Backtest]:
        return self._to_entity(
            self.session.query(BacktestModel).filter(BacktestModel.id == id).first()
        )

    def get_by_name(self, name: str) -> Optional[Backtest]:
        return self._to_entity(
            self.session.query(BacktestModel).filter(BacktestModel.name == name).first()
        )

    def get_by_model_id(self, model_id: int) -> List[Backtest]:
        return [
            self._to_entity(m)
            for m in self.session.query(BacktestModel)
            .filter(BacktestModel.model_id == model_id)
            .all()
        ]

    def add(self, entity: Backtest) -> Optional[Backtest]:
        orm_obj = self._to_model(entity)
        self.session.add(orm_obj)
        self.session.commit()
        return self._to_entity(orm_obj)

    def update(self, entity: Backtest) -> Optional[Backtest]:
        orm_obj = self.session.query(BacktestModel).filter(BacktestModel.id == entity.id).first()
        if not orm_obj:
            return None
        orm_obj.name = entity.name
        orm_obj.model_id = entity.model_id
        orm_obj.creation_date = entity.creation_date
        self.session.commit()
        return self._to_entity(orm_obj)

    def delete(self, id: int) -> bool:
        orm_obj = self.session.query(BacktestModel).filter(BacktestModel.id == id).first()
        if not orm_obj:
            return False
        self.session.delete(orm_obj)
        self.session.commit()
        return True

    def _create_or_get(self, name: str, model_id: int, **kwargs) -> Optional[Backtest]:
        try:
            existing = self.get_by_name(name)
            if existing:
                return existing
            creation_date = kwargs.get('creation_date', date.today())
            return self.add(Backtest(id=None, name=name, model_id=model_id, creation_date=creation_date))
        except Exception as e:
            print(f"Error in _create_or_get for Backtest '{name}': {e}")
            return None
