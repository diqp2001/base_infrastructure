"""
Local SQLAlchemy repositories of strategies (one row per version) and their experiments.

A strategy is stored as its strategies row (identity, status, universe) plus one strategy_parameter_values row per
parameter (strategy_parameters: the catalog of (section, name)); saving replaces the strategy's value rows, reading
rebuilds its sections and typed definition from them (strategy_parameter_codec).

Unlike most repositories of the code base they raise on failure (after rolling back) instead of returning None:
a strategy or an experiment that was not saved must never look saved.
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.entities.strategy.strategy import DEFINITION_FIELDS, Strategy
from src.domain.entities.strategy.strategy_experiment import StrategyExperiment
from src.domain.ports.strategy.strategy_ports import StrategyExperimentPort, StrategyPort
from src.infrastructure.models.strategy.strategy import (
    StrategyExperimentModel,
    StrategyModel,
    StrategyParameterModel,
    StrategyParameterValueModel,
)
from src.infrastructure.repositories.mappers.strategy import strategy_parameter_codec as codec
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

    # -- parameters ---------------------------------------------------------------------------------------------
    def _parameter_ids(self, keys) -> dict:
        """{(section, name): parameter id}, catalog rows created when missing."""
        wanted = set(keys)
        ids = {}
        sections = {s for s, _ in wanted}
        if sections:
            for row in (self.session.query(StrategyParameterModel)
                        .filter(StrategyParameterModel.section.in_(sorted(sections))).all()):
                if (row.section, row.name) in wanted:
                    ids[(row.section, row.name)] = row.id
        for section, name in sorted(wanted - set(ids)):
            row = StrategyParameterModel(section=section, name=name)
            self.session.add(row)
            self.session.flush()
            ids[(section, name)] = row.id
        return ids

    def _write_parameters(self, strategy_id: int, entity: Strategy) -> None:
        rows = codec.flatten(entity.sections, {f: getattr(entity, f) for f in DEFINITION_FIELDS})
        ids = self._parameter_ids((s, n) for s, n, _ in rows)
        (self.session.query(StrategyParameterValueModel)
         .filter(StrategyParameterValueModel.strategy_id == strategy_id).delete(synchronize_session=False))
        for section, name, value in rows:
            value_type, text, numeric = codec.encode(value)
            self.session.add(StrategyParameterValueModel(strategy_id=strategy_id, parameter_id=ids[(section, name)],
                                                         value=text, value_type=value_type, value_numeric=numeric))

    def _parameters_of(self, strategy_ids) -> dict:
        """{strategy id: (sections, definition)}: one query per 500 strategies."""
        out = {sid: [] for sid in strategy_ids}
        ids = sorted(out)
        for start in range(0, len(ids), 500):
            rows = (self.session.query(StrategyParameterValueModel.strategy_id, StrategyParameterModel.section,
                                       StrategyParameterModel.name, StrategyParameterValueModel.value_type,
                                       StrategyParameterValueModel.value)
                    .join(StrategyParameterModel,
                          StrategyParameterModel.id == StrategyParameterValueModel.parameter_id)
                    .filter(StrategyParameterValueModel.strategy_id.in_(ids[start:start + 500]))
                    .order_by(StrategyParameterValueModel.id).all())
            for sid, section, name, value_type, value in rows:
                out[sid].append((section, name, codec.decode(value_type, value)))
        return {sid: codec.unflatten(rows) for sid, rows in out.items()}

    def _hydrate(self, orms) -> list:
        orms = [o for o in orms if o is not None]
        params = self._parameters_of([o.id for o in orms])
        return [self.mapper.to_domain(o, *params[o.id]) for o in orms]

    def _save(self, entity, orm):
        try:
            self.mapper.copy_to_orm(entity, orm)
            self.session.add(orm)
            self.session.flush()
            self._write_parameters(orm.id, entity)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        entity.id = orm.id
        return entity

    # -- reads --------------------------------------------------------------------------------------------------
    def get_by_id(self, id: int) -> Optional[Strategy]:
        found = self._hydrate([self._row(id)])
        return found[0] if found else None

    def get_all(self) -> List[Strategy]:
        return self._hydrate(self.session.query(StrategyModel).order_by(StrategyModel.id).all())

    def add(self, entity: Strategy) -> Strategy:
        if entity.created_at is None:
            entity.created_at = datetime.utcnow()
        return self._save(entity, StrategyModel())

    def get_version(self, name: str, version: int) -> Optional[Strategy]:
        found = self._hydrate([self.session.query(StrategyModel).filter(
            StrategyModel.name == name, StrategyModel.version == version).one_or_none()])
        return found[0] if found else None

    def get_versions(self, name: str) -> List[Strategy]:
        return self._hydrate(self.session.query(StrategyModel).filter(StrategyModel.name == name)
                             .order_by(StrategyModel.version).all())

    def parameter_values(self, section: str, name: str) -> dict:
        """{strategy id: value} of one parameter across strategies (comparison / filtering)."""
        rows = (self.session.query(StrategyParameterValueModel.strategy_id, StrategyParameterValueModel.value_type,
                                   StrategyParameterValueModel.value)
                .join(StrategyParameterModel, StrategyParameterModel.id == StrategyParameterValueModel.parameter_id)
                .filter(StrategyParameterModel.section == section, StrategyParameterModel.name == name).all())
        return {sid: codec.decode(value_type, value) for sid, value_type, value in rows}

    def latest_version_number(self, name: str) -> int:
        value = (self.session.query(func.max(StrategyModel.version))
                 .filter(StrategyModel.name == name).scalar())
        return int(value or 0)

    def get_by_universe(self, universe_id: int) -> List[Strategy]:
        return self._hydrate(self.session.query(StrategyModel).filter(StrategyModel.universe_id == universe_id)
                             .order_by(StrategyModel.id).all())


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
