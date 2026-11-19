"""
SQLAlchemy ORM models of the strategy domain.

Tables (2026-11-19):
  strategies                  one row per strategy VERSION: identity, status, content hash, universe (replaces
                              strategy_configurations)
  strategy_parameters         one row per distinct parameter: (section, name) - name = the parameter's path inside
                              its section ('stm.model/params/hidden_dim'); section 'definition' holds the shared
                              typed fields (bar_frequency, bar_size, model_type, training_window, ...)
  strategy_parameter_values   one row per (strategy, parameter): the value as text, its type, a numeric copy
  strategy_experiments        one row per run of a locked strategy
Codec: src/infrastructure/repositories/mappers/strategy/strategy_parameter_codec.py. Migration of databases holding
the former shapes: src/infrastructure/database/strategy_universe_migration.py.
"""

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint

from src.infrastructure.models import ModelBase as Base


class StrategyModel(Base):
    __tablename__ = "strategies"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_strategy_version"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    parent_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    strategy_type = Column(String(100), nullable=False, index=True)       # ProjectRegistry key
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    content_hash = Column(String(64), nullable=False, index=True)
    universe_id = Column(Integer, ForeignKey("universes.id"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=True)
    validated_at = Column(DateTime, nullable=True)
    locked_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<StrategyModel(id={self.id}, name={self.name!r}, v{self.version}, {self.status})>"


class StrategyParameterModel(Base):
    __tablename__ = "strategy_parameters"
    __table_args__ = (UniqueConstraint("section", "name", name="uq_strategy_parameter"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    section = Column(String(50), nullable=False, index=True)
    name = Column(String(400), nullable=False)
    description = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<StrategyParameterModel(id={self.id}, {self.section}.{self.name})>"


class StrategyParameterValueModel(Base):
    __tablename__ = "strategy_parameter_values"
    __table_args__ = (UniqueConstraint("strategy_id", "parameter_id", name="uq_strategy_parameter_value"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False, index=True)
    parameter_id = Column(Integer, ForeignKey("strategy_parameters.id"), nullable=False, index=True)
    value = Column(Text, nullable=True)                        # the value as text (JSON for lists / dicts)
    value_type = Column(String(10), nullable=False)            # null | bool | int | float | str | json
    value_numeric = Column(Float, nullable=True)               # int / float values, for filtering in SQL

    def __repr__(self) -> str:
        return f"<StrategyParameterValueModel(strategy={self.strategy_id}, parameter={self.parameter_id})>"


class StrategyExperimentModel(Base):
    __tablename__ = "strategy_experiments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False, index=True)
    strategy_hash = Column(String(64), nullable=False)
    strategy_type = Column(String(100), nullable=False, index=True)
    kind = Column(String(20), nullable=False, default="backtest")
    status = Column(String(20), nullable=False, default="queued", index=True)
    results_dir = Column(String(500), nullable=True)
    log_path = Column(String(500), nullable=True)
    pid = Column(Integer, nullable=True)
    host = Column(String(200), nullable=True)
    created_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    heartbeat_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=True)
    provenance = Column(Text, nullable=True)                   # JSON: artifacts, universe snapshot, data coverage
    summary = Column(Text, nullable=True)                      # JSON: headline metrics of the report

    def __repr__(self) -> str:
        return f"<StrategyExperimentModel(id={self.id}, strategy={self.strategy_id}, {self.status})>"
