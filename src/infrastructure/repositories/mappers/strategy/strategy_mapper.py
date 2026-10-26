"""
Mappers between the strategy configuration domain and its ORM models (JSON text <-> dicts).
"""

import json
from typing import Optional

from src.domain.entities.strategy.strategy_configuration import StrategyConfiguration
from src.domain.entities.strategy.strategy_experiment import StrategyExperiment
from src.infrastructure.models.strategy.strategy_configuration import (
    StrategyConfigurationModel,
    StrategyExperimentModel,
)


def _dumps(value) -> str:
    return json.dumps(value, sort_keys=True, default=str)


def _loads(text: Optional[str]) -> dict:
    if not text:
        return {}
    try:
        value = json.loads(text)
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


class StrategyConfigurationMapper:

    @staticmethod
    def to_domain(orm: Optional[StrategyConfigurationModel]) -> Optional[StrategyConfiguration]:
        if orm is None:
            return None
        return StrategyConfiguration(
            id=orm.id, name=orm.name, project_key=orm.project_key, sections=_loads(orm.sections),
            description=orm.description or "", version=orm.version, parent_id=orm.parent_id, status=orm.status,
            created_at=orm.created_at, validated_at=orm.validated_at, locked_at=orm.locked_at,
        )

    @staticmethod
    def copy_to_orm(entity: StrategyConfiguration, orm: StrategyConfigurationModel) -> StrategyConfigurationModel:
        orm.name = entity.name
        orm.version = entity.version
        orm.parent_id = entity.parent_id
        orm.project_key = entity.project_key
        orm.description = entity.description
        orm.status = entity.status
        orm.content_hash = entity.content_hash
        orm.sections = _dumps(entity.sections)
        orm.created_at = entity.created_at
        orm.validated_at = entity.validated_at
        orm.locked_at = entity.locked_at
        return orm


class StrategyExperimentMapper:

    FIELDS = ("configuration_id", "configuration_hash", "project_key", "kind", "status", "results_dir", "log_path",
              "pid", "host", "created_at", "started_at", "finished_at", "heartbeat_at", "error")

    @staticmethod
    def to_domain(orm: Optional[StrategyExperimentModel]) -> Optional[StrategyExperiment]:
        if orm is None:
            return None
        return StrategyExperiment(
            id=orm.id, provenance=_loads(orm.provenance), summary=_loads(orm.summary),
            **{f: getattr(orm, f) for f in StrategyExperimentMapper.FIELDS},
        )

    @staticmethod
    def copy_to_orm(entity: StrategyExperiment, orm: StrategyExperimentModel) -> StrategyExperimentModel:
        for f in StrategyExperimentMapper.FIELDS:
            setattr(orm, f, getattr(entity, f))
        orm.provenance = _dumps(entity.provenance)
        orm.summary = _dumps(entity.summary)
        return orm
