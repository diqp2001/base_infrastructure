"""
Mappers between the strategy domain (Strategy, StrategyExperiment) and its ORM models (JSON text <-> dicts).
"""

import json
from typing import Optional

from src.domain.entities.strategy.strategy import DEFINITION_FIELDS, Strategy
from src.domain.entities.strategy.strategy_experiment import StrategyExperiment
from src.infrastructure.models.strategy.strategy import StrategyExperimentModel, StrategyModel


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


class StrategyMapper:

    @staticmethod
    def to_domain(orm: Optional[StrategyModel]) -> Optional[Strategy]:
        if orm is None:
            return None
        return Strategy(
            id=orm.id, name=orm.name, strategy_type=orm.strategy_type, sections=_loads(orm.sections),
            description=orm.description or "", version=orm.version, parent_id=orm.parent_id, status=orm.status,
            universe_id=orm.universe_id, created_at=orm.created_at, validated_at=orm.validated_at,
            locked_at=orm.locked_at, **{f: getattr(orm, f) for f in DEFINITION_FIELDS},
        )

    @staticmethod
    def copy_to_orm(entity: Strategy, orm: StrategyModel) -> StrategyModel:
        orm.name = entity.name
        orm.version = entity.version
        orm.parent_id = entity.parent_id
        orm.strategy_type = entity.strategy_type
        orm.description = entity.description
        orm.status = entity.status
        orm.content_hash = entity.content_hash
        orm.universe_id = entity.universe_id
        for f in DEFINITION_FIELDS:
            setattr(orm, f, getattr(entity, f))
        orm.sections = _dumps(entity.sections)
        orm.created_at = entity.created_at
        orm.validated_at = entity.validated_at
        orm.locked_at = entity.locked_at
        return orm


StrategyConfigurationMapper = StrategyMapper      # former name


class StrategyExperimentMapper:

    FIELDS = ("strategy_id", "strategy_hash", "strategy_type", "kind", "status", "results_dir", "log_path",
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
