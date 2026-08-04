from typing import List, Optional
from sqlalchemy.orm import Session

from src.infrastructure.models.backtest.backtest_factor_backtest import BacktestFactorBacktestModel
from src.domain.entities.backtest.backtest_factor_backtest import BacktestFactorBacktest
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.backtest.backtest_factor_backtest_mapper import BacktestFactorBacktestMapper
from src.domain.ports.backtest.backtest_factor_backtest_port import BacktestFactorBacktestPort


class BacktestFactorBacktestRepository(BaseLocalRepository, BacktestFactorBacktestPort):

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = BacktestFactorBacktestMapper()

    @property
    def model_class(self):
        return BacktestFactorBacktestModel

    @property
    def entity_class(self):
        return BacktestFactorBacktest

    def _to_entity(self, orm_obj) -> Optional[BacktestFactorBacktest]:
        return self.mapper.to_domain(orm_obj)

    def _to_model(self, entity: BacktestFactorBacktest) -> BacktestFactorBacktestModel:
        return self.mapper.to_orm(entity)

    def get_all(self) -> List[BacktestFactorBacktest]:
        return [
            self._to_entity(m)
            for m in self.session.query(BacktestFactorBacktestModel).all()
        ]

    def get_by_id(self, id: int) -> Optional[BacktestFactorBacktest]:
        return self._to_entity(
            self.session.query(BacktestFactorBacktestModel)
            .filter(BacktestFactorBacktestModel.id == id)
            .first()
        )

    def get_by_backtest_id(self, backtest_id: int) -> List[BacktestFactorBacktest]:
        return [
            self._to_entity(m)
            for m in self.session.query(BacktestFactorBacktestModel)
            .filter(BacktestFactorBacktestModel.backtest_id == backtest_id)
            .all()
        ]

    def get_by_backtest_factor_id(self, backtest_factor_id: int) -> List[BacktestFactorBacktest]:
        return [
            self._to_entity(m)
            for m in self.session.query(BacktestFactorBacktestModel)
            .filter(BacktestFactorBacktestModel.backtest_factor_id == backtest_factor_id)
            .all()
        ]

    def add(self, entity: BacktestFactorBacktest) -> Optional[BacktestFactorBacktest]:
        existing = self._create_or_get(entity.backtest_id, entity.backtest_factor_id)
        if existing and existing.id:
            return existing
        orm_obj = self._to_model(entity)
        self.session.add(orm_obj)
        self.session.commit()
        return self._to_entity(orm_obj)

    def delete(self, id: int) -> bool:
        orm_obj = (
            self.session.query(BacktestFactorBacktestModel)
            .filter(BacktestFactorBacktestModel.id == id)
            .first()
        )
        if not orm_obj:
            return False
        self.session.delete(orm_obj)
        self.session.commit()
        return True

    def _create_or_get(self, backtest_id: int, backtest_factor_id: int) -> Optional[BacktestFactorBacktest]:
        try:
            existing = (
                self.session.query(BacktestFactorBacktestModel)
                .filter(
                    BacktestFactorBacktestModel.backtest_id == backtest_id,
                    BacktestFactorBacktestModel.backtest_factor_id == backtest_factor_id,
                )
                .first()
            )
            if existing:
                return self._to_entity(existing)
            orm_obj = BacktestFactorBacktestModel(
                backtest_id=backtest_id,
                backtest_factor_id=backtest_factor_id,
            )
            self.session.add(orm_obj)
            self.session.commit()
            return self._to_entity(orm_obj)
        except Exception as e:
            print(f"Error in _create_or_get for BacktestFactorBacktest: {e}")
            return None
