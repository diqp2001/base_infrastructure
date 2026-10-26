"""
SQLAlchemy ORM models of the strategy configuration system.

Tables: strategy_configurations (one row per configuration VERSION), strategy_experiments (one row per run).
Sections, provenance and summary are JSON text; their structure is owned by the domain / project schemas.
"""

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from src.infrastructure.models import ModelBase as Base


class StrategyConfigurationModel(Base):
    __tablename__ = "strategy_configurations"
    __table_args__ = (UniqueConstraint("name", "version", name="uq_strategy_configuration_version"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), nullable=False, index=True)
    version = Column(Integer, nullable=False, default=1)
    parent_id = Column(Integer, ForeignKey("strategy_configurations.id"), nullable=True)
    project_key = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="draft")
    content_hash = Column(String(64), nullable=False, index=True)
    sections = Column(Text, nullable=False)                    # JSON {section: {field: value}}
    created_at = Column(DateTime, nullable=True)
    validated_at = Column(DateTime, nullable=True)
    locked_at = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<StrategyConfigurationModel(id={self.id}, name={self.name!r}, v{self.version}, {self.status})>"


class StrategyExperimentModel(Base):
    __tablename__ = "strategy_experiments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    configuration_id = Column(Integer, ForeignKey("strategy_configurations.id"), nullable=False, index=True)
    configuration_hash = Column(String(64), nullable=False)
    project_key = Column(String(100), nullable=False, index=True)
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
        return f"<StrategyExperimentModel(id={self.id}, configuration={self.configuration_id}, {self.status})>"
