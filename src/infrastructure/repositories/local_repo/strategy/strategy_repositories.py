"""
Local SQLAlchemy repositories of strategies (one row per version) and their experiments.

Unlike most repositories of the code base they raise on failure (after rolling back) instead of returning None:
a strategy or an experiment that was not saved must never look saved.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.entities.strategy.strategy import Strategy
from src.domain.entities.strategy.strategy_experiment import StrategyExperiment
from src.domain.ports.strategy.strategy_ports import StrategyExperimentPort, StrategyPort
from src.infrastructure.models.strategy.strategy import StrategyExperimentModel, StrategyModel
from src.infrastructure.repositories.mappers.strategy.strategy_mapper import StrategyExperimentMapper, StrategyMapper


class _Base:
    model_class = None
    mapper = None

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory

    def _row(self, id: int):
        return self.session.query(self.model_class).filter(self.model_class.id == id).one_or_none()

    def _save(self, entity, orm):
        try:
            self.mapper.copy_to_orm(entity, orm)
            self.session.add(orm)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        entity.id = orm.id
        return entity

    def get_by_id(self, id: int):
        return self.mapper.to_domain(self._row(id))

    def get_all(self) -> list:
        return [self.mapper.to_domain(r) for r in self.session.query(self.model_class)
                .order_by(self.model_class.id).all()]

    def update(self, entity):
        orm = self._row(entity.id) if entity.id is not None else None
        if orm is None:
            raise LookupError(f"{type(entity).__name__} {entity.id} does not exist")
        return self._save(entity, orm)


class StrategyRepository(_Base, StrategyPort):
    model_class = StrategyModel
    mapper = StrategyMapper

    def add(self, entity: Strategy) -> Strategy:
        if entity.created_at is None:
            entity.created_at = datetime.utcnow()
        return self._save(entity, StrategyModel())

    def get_version(self, name: str, version: int) -> Optional[Strategy]:
        return self.mapper.to_domain(self.session.query(StrategyModel).filter(
            StrategyModel.name == name, StrategyModel.version == version).one_or_none())

    def get_versions(self, name: str) -> List[Strategy]:
        rows = (self.session.query(StrategyModel).filter(StrategyModel.name == name)
                .order_by(StrategyModel.version).all())
        return [self.mapper.to_domain(r) for r in rows]

    def latest_version_number(self, name: str) -> int:
        value = (self.session.query(func.max(StrategyModel.version))
                 .filter(StrategyModel.name == name).scalar())
        return int(value or 0)

    def get_by_universe(self, universe_id: int) -> List[Strategy]:
        rows = (self.session.query(StrategyModel).filter(StrategyModel.universe_id == universe_id)
                .order_by(StrategyModel.id).all())
        return [self.mapper.to_domain(r) for r in rows]


StrategyConfigurationRepository = StrategyRepository      # former name


class StrategyExperimentRepository(_Base, StrategyExperimentPort):
    model_class = StrategyExperimentModel
    mapper = StrategyExperimentMapper

    def add(self, entity: StrategyExperiment) -> StrategyExperiment:
        if entity.created_at is None:
            entity.created_at = datetime.utcnow()
        return self._save(entity, StrategyExperimentModel())

    def get_by_strategy(self, strategy_id: int) -> List[StrategyExperiment]:
        rows = (self.session.query(StrategyExperimentModel)
                .filter(StrategyExperimentModel.strategy_id == strategy_id)
                .order_by(StrategyExperimentModel.id).all())
        return [self.mapper.to_domain(r) for r in rows]

    def get_by_status(self, status: str) -> List[StrategyExperiment]:
        rows = (self.session.query(StrategyExperimentModel).filter(StrategyExperimentModel.status == status)
                .order_by(StrategyExperimentModel.id).all())
        return [self.mapper.to_domain(r) for r in rows]

    get_by_configuration = get_by_strategy                   # former name
