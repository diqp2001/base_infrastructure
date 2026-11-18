"""Mappers of the backtest run registry (2026-11-18): domain entities <-> ORM rows (JSON payloads as Text)."""

import json
from typing import Any, Optional

from src.domain.entities.backtest.backtest_run import BacktestRun
from src.domain.entities.backtest.backtest_run_link import BacktestRunModelLink, BacktestRunPortfolio
from src.domain.entities.backtest.research_result import ResearchSeriesValue, RunMetric
from src.infrastructure.models.backtest.backtest_run import (
    BacktestRunModel,
    BacktestRunModelLinkModel,
    BacktestRunPortfolioModel,
    ResearchSeriesModel,
    RunMetricModel,
)

JSON_FIELDS = ("config_snapshot", "universe_snapshot", "assumptions", "data_snapshot")
PLAIN_FIELDS = ("run_uid", "project_name", "run_name", "kind", "status", "config_hash", "code_commit", "code_branch",
                "code_dirty", "requested_start", "requested_end", "actual_start", "actual_end", "started_at",
                "completed_at", "heartbeat_at", "months_planned", "months_completed", "bars_processed",
                "starting_capital", "gross_leverage", "universe_description", "price_source", "include_dividends",
                "include_transaction_costs", "results_dir", "host", "pid", "strategy_experiment_id", "error",
                "created_at")


def _dumps(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, default=str, sort_keys=True)


def _loads(text: Optional[str]) -> Any:
    if not text:
        return {}
    try:
        return json.loads(text)
    except ValueError:
        return {"unparsed": text}


class BacktestRunMapper:

    @staticmethod
    def to_domain(orm: Optional[BacktestRunModel]) -> Optional[BacktestRun]:
        if orm is None:
            return None
        kwargs = {f: getattr(orm, f) for f in PLAIN_FIELDS}
        kwargs.update({f: _loads(getattr(orm, f)) for f in JSON_FIELDS})
        kwargs["bars_processed"] = kwargs.get("bars_processed") or 0
        return BacktestRun(id=orm.id, **kwargs)

    @staticmethod
    def apply(entity: BacktestRun, orm: BacktestRunModel) -> BacktestRunModel:
        for f in PLAIN_FIELDS:
            setattr(orm, f, getattr(entity, f))
        for f in JSON_FIELDS:
            setattr(orm, f, _dumps(getattr(entity, f)))
        return orm

    @classmethod
    def to_orm(cls, entity: BacktestRun) -> BacktestRunModel:
        return cls.apply(entity, BacktestRunModel())


class BacktestRunPortfolioMapper:

    @staticmethod
    def to_domain(orm: Optional[BacktestRunPortfolioModel]) -> Optional[BacktestRunPortfolio]:
        if orm is None:
            return None
        return BacktestRunPortfolio(id=orm.id, run_id=orm.run_id, portfolio_id=orm.portfolio_id, role=orm.role,
                                    label=orm.label)

    @staticmethod
    def to_orm(entity: BacktestRunPortfolio) -> BacktestRunPortfolioModel:
        return BacktestRunPortfolioModel(run_id=entity.run_id, portfolio_id=entity.portfolio_id, role=entity.role,
                                         label=entity.label)


class BacktestRunModelLinkMapper:

    @staticmethod
    def to_domain(orm: Optional[BacktestRunModelLinkModel]) -> Optional[BacktestRunModelLink]:
        if orm is None:
            return None
        return BacktestRunModelLink(id=orm.id, run_id=orm.run_id, ml_model_id=orm.ml_model_id, role=orm.role,
                                    model_artifact_id=orm.model_artifact_id)

    @staticmethod
    def to_orm(entity: BacktestRunModelLink) -> BacktestRunModelLinkModel:
        return BacktestRunModelLinkModel(run_id=entity.run_id, ml_model_id=entity.ml_model_id, role=entity.role,
                                         model_artifact_id=entity.model_artifact_id)


class ResearchSeriesMapper:

    @staticmethod
    def to_domain(orm: Optional[ResearchSeriesModel]) -> Optional[ResearchSeriesValue]:
        if orm is None:
            return None
        return ResearchSeriesValue(id=orm.id, run_id=orm.run_id, series_name=orm.series_name,
                                   series_group=orm.series_group, date=orm.date, value=orm.value)

    @staticmethod
    def to_orm(entity: ResearchSeriesValue) -> ResearchSeriesModel:
        return ResearchSeriesModel(run_id=entity.run_id, series_name=entity.series_name,
                                   series_group=entity.series_group, date=entity.date, value=entity.value)


class RunMetricMapper:

    @staticmethod
    def to_domain(orm: Optional[RunMetricModel]) -> Optional[RunMetric]:
        if orm is None:
            return None
        return RunMetric(id=orm.id, run_id=orm.run_id, metric_name=orm.metric_name, value=orm.value, scope=orm.scope)

    @staticmethod
    def to_orm(entity: RunMetric) -> RunMetricModel:
        return RunMetricModel(run_id=entity.run_id, metric_name=entity.metric_name, value=entity.value,
                              scope=entity.scope)
