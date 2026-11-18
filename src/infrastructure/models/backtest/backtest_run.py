"""
ORM models of the generic backtest run registry (2026-11-18).

Tables:
    backtest_runs            one row per backtest EXECUTION (identity, config snapshot, code version, window,
                             progress, assumptions, status)
    backtest_run_portfolios  the portfolios a run created (one run -> many portfolios; one portfolio -> one run)
    backtest_run_models      the ML models (ml_models) a run used, with their role
    research_series          dated values of a run's named research series (deciles, P&L legs, ...)
    run_metrics              named metrics of a run, per scope ('engine', 'A/gross', ...)

JSON payloads (config snapshot, universe snapshot, assumptions, data snapshot) are Text, as in strategy_experiments.
"""

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Index, Integer, String, Text,
                        UniqueConstraint)

from src.infrastructure.models import ModelBase as Base


class BacktestRunModel(Base):
    __tablename__ = "backtest_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_uid = Column(String(32), nullable=False, unique=True)
    project_name = Column(String(200), nullable=False, index=True)
    run_name = Column(String(300), nullable=True)
    kind = Column(String(20), nullable=False, default="backtest")
    status = Column(String(20), nullable=False, index=True)
    config_snapshot = Column(Text, nullable=True)
    config_hash = Column(String(64), nullable=True, index=True)
    code_commit = Column(String(64), nullable=True)
    code_branch = Column(String(200), nullable=True)
    code_dirty = Column(Boolean, nullable=True)
    requested_start = Column(DateTime, nullable=True)
    requested_end = Column(DateTime, nullable=True)
    actual_start = Column(DateTime, nullable=True)
    actual_end = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    heartbeat_at = Column(DateTime, nullable=True)
    months_planned = Column(Integer, nullable=True)
    months_completed = Column(Integer, nullable=True)
    bars_processed = Column(Integer, nullable=False, default=0)
    starting_capital = Column(Float, nullable=True)
    gross_leverage = Column(Float, nullable=True)
    universe_description = Column(String(500), nullable=True)
    universe_snapshot = Column(Text, nullable=True)
    price_source = Column(String(50), nullable=True)
    include_dividends = Column(Boolean, nullable=True)
    include_transaction_costs = Column(Boolean, nullable=True)
    assumptions = Column(Text, nullable=True)
    data_snapshot = Column(Text, nullable=True)
    results_dir = Column(String(500), nullable=True)
    host = Column(String(200), nullable=True)
    pid = Column(Integer, nullable=True)
    strategy_experiment_id = Column(Integer, ForeignKey("strategy_experiments.id"), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<BacktestRunModel(id={self.id}, {self.project_name}, {self.status})>"


class BacktestRunPortfolioModel(Base):
    __tablename__ = "backtest_run_portfolios"
    __table_args__ = (UniqueConstraint("portfolio_id", name="uq_backtest_run_portfolio"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("backtest_runs.id"), nullable=False, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    role = Column(String(30), nullable=False, default="main")
    label = Column(String(200), nullable=True)


class BacktestRunModelLinkModel(Base):
    __tablename__ = "backtest_run_models"
    __table_args__ = (UniqueConstraint("run_id", "ml_model_id", "role", name="uq_backtest_run_model"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("backtest_runs.id"), nullable=False, index=True)
    ml_model_id = Column(Integer, ForeignKey("ml_models.id"), nullable=False, index=True)
    role = Column(String(50), nullable=False, default="model")
    model_artifact_id = Column(Integer, ForeignKey("model_artifacts.id"), nullable=True)


class ResearchSeriesModel(Base):
    __tablename__ = "research_series"
    __table_args__ = (Index("ix_research_series_run_name_date", "run_id", "series_name", "date"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("backtest_runs.id"), nullable=False)
    series_name = Column(String(200), nullable=False)
    series_group = Column(String(200), nullable=True)
    date = Column(DateTime, nullable=False)
    value = Column(Float, nullable=True)


class RunMetricModel(Base):
    __tablename__ = "run_metrics"
    __table_args__ = (UniqueConstraint("run_id", "scope", "metric_name", name="uq_run_metric"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("backtest_runs.id"), nullable=False, index=True)
    scope = Column(String(100), nullable=False, default="engine")
    metric_name = Column(String(200), nullable=False)
    value = Column(Float, nullable=True)
