"""
SQLAlchemy ORM models of the strategy domain.

Tables: strategies (one row per strategy VERSION, replaces strategy_configurations since 2026-11-19),
strategy_experiments (one row per run of a locked strategy). Sections, provenance and summary are JSON text; their
structure is owned by the domain / project schemas. Migration of databases holding the former tables:
src/infrastructure/database/strategy_universe_migration.py.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

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
    bar_frequency = Column(String(20), nullable=True)
    bar_size = Column(String(30), nullable=True)
    model_type = Column(String(50), nullable=True)
    training_window = Column(Integer, nullable=True)
    retrain_every_days = Column(Integer, nullable=True)
    prediction_horizon = Column(Integer, nullable=True)
    sections = Column(Text, nullable=False)                    # JSON {section: {field: value}}
    created_at = Column(DateTime, nullable=True)
    validated_at = Column(DateTime, nullable=True)
    locked_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<StrategyModel(id={self.id}, name={self.name!r}, v{self.version}, {self.status})>"


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
