"""
Local SQLAlchemy repositories of strategy configurations and experiments.

Unlike most repositories of the code base they raise on failure (after rolling back) instead of returning None:
a configuration or an experiment that was not saved must never look saved.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.entities.strategy.strategy_configuration import StrategyConfiguration
from src.domain.entities.strategy.strategy_experiment import StrategyExperiment
from src.domain.ports.strategy.strategy_ports import StrategyConfigurationPort, StrategyExperimentPort
from src.infrastructure.models.strategy.strategy_configuration import (
    StrategyConfigurationModel,
    StrategyExperimentModel,
)
from src.infrastructure.repositories.mappers.strategy.strategy_mapper import (
    StrategyConfigurationMapper,
    StrategyExperimentMapper,
)


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


class StrategyConfigurationRepository(_Base, StrategyConfigurationPort):
    model_class = StrategyConfigurationModel
    mapper = StrategyConfigurationMapper

    def add(self, entity: StrategyConfiguration) -> StrategyConfiguration:
        if entity.created_at is None:
            entity.created_at = datetime.utcnow()
        return self._save(entity, StrategyConfigurationModel())

    def get_version(self, name: str, version: int) -> Optional[StrategyConfiguration]:
        return self.mapper.to_domain(self.session.query(StrategyConfigurationModel).filter(
            StrategyConfigurationModel.name == name, StrategyConfigurationModel.version == version).one_or_none())

    def get_versions(self, name: str) -> List[StrategyConfiguration]:
        rows = (self.session.query(StrategyConfigurationModel).filter(StrategyConfigurationModel.name == name)
                .order_by(StrategyConfigurationModel.version).all())
        return [self.mapper.to_domain(r) for r in rows]

    def latest_version_number(self, name: str) -> int:
        value = (self.session.query(func.max(StrategyConfigurationModel.version))
                 .filter(StrategyConfigurationModel.name == name).scalar())
        return int(value or 0)


class StrategyExperimentRepository(_Base, StrategyExperimentPort):
    model_class = StrategyExperimentModel
    mapper = StrategyExperimentMapper

    def add(self, entity: StrategyExperiment) -> StrategyExperiment:
        if entity.created_at is None:
            entity.created_at = datetime.utcnow()
        return self._save(entity, StrategyExperimentModel())

    def get_by_configuration(self, configuration_id: int) -> List[StrategyExperiment]:
        rows = (self.session.query(StrategyExperimentModel)
                .filter(StrategyExperimentModel.configuration_id == configuration_id)
                .order_by(StrategyExperimentModel.id).all())
        return [self.mapper.to_domain(r) for r in rows]

    def get_by_status(self, status: str) -> List[StrategyExperiment]:
        rows = (self.session.query(StrategyExperimentModel).filter(StrategyExperimentModel.status == status)
                .order_by(StrategyExperimentModel.id).all())
        return [self.mapper.to_domain(r) for r in rows]
