"""
Local repositories of a backtest run's research results (2026-11-18): named series and metrics, plus a read of the
engine's portfolio value curve (the PortfolioValueFactor values of a run's portfolios) for the comparison layer.
"""

import math
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.domain.entities.backtest.research_result import ResearchSeriesValue, RunMetric
from src.domain.ports.backtest.research_result_port import ResearchSeriesPort, RunMetricPort
from src.infrastructure.models.backtest.backtest_run import ResearchSeriesModel, RunMetricModel
from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.mappers.backtest.backtest_run_mapper import ResearchSeriesMapper, RunMetricMapper

PORTFOLIO_VALUE_FACTOR_TYPE = "portfolio_value_factor"
PORTFOLIO_ENTITY_TYPE = "PortfolioModel"


def _clean(value) -> Optional[float]:
    if value is None:
        return None
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


class ResearchSeriesRepository(BaseLocalRepository, ResearchSeriesPort):

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = ResearchSeriesMapper()

    @property
    def model_class(self):
        return ResearchSeriesModel

    @property
    def entity_class(self):
        return ResearchSeriesValue

    def _to_entity(self, orm_obj):
        return self.mapper.to_domain(orm_obj)

    def _to_model(self, entity):
        return self.mapper.to_orm(entity)

    def _create_or_get(self, *args, **kwargs):
        raise NotImplementedError("research series are written with replace()")

    def replace(self, run_id: int, values: List[ResearchSeriesValue],
                series_names: Optional[List[str]] = None) -> int:
        names = sorted(set(series_names or [v.series_name for v in values]))
        if names:
            (self.session.query(ResearchSeriesModel)
             .filter(ResearchSeriesModel.run_id == run_id, ResearchSeriesModel.series_name.in_(names))
             .delete(synchronize_session=False))
        rows = []
        for v in values:
            if v.run_id != run_id:
                raise ValueError(f"series value of run {v.run_id} written under run {run_id}")
            v.value = _clean(v.value)
            rows.append(self._to_model(v))
        self.session.add_all(rows)
        self.session.commit()
        return len(rows)

    def get_by_run(self, run_id: int, series_names: Optional[List[str]] = None,
                   series_group: Optional[str] = None) -> List[ResearchSeriesValue]:
        q = self.session.query(ResearchSeriesModel).filter(ResearchSeriesModel.run_id == run_id)
        if series_names:
            q = q.filter(ResearchSeriesModel.series_name.in_(list(series_names)))
        if series_group:
            q = q.filter(ResearchSeriesModel.series_group == series_group)
        return [self._to_entity(m) for m in q.order_by(ResearchSeriesModel.series_name, ResearchSeriesModel.date)]

    def series_names(self, run_id: int) -> List[Dict[str, object]]:
        rows = (self.session.query(ResearchSeriesModel.series_name, ResearchSeriesModel.series_group,
                                   func.count(ResearchSeriesModel.id), func.min(ResearchSeriesModel.date),
                                   func.max(ResearchSeriesModel.date))
                .filter(ResearchSeriesModel.run_id == run_id)
                .group_by(ResearchSeriesModel.series_name, ResearchSeriesModel.series_group)
                .order_by(ResearchSeriesModel.series_group, ResearchSeriesModel.series_name).all())
        return [{"name": n, "group": g, "points": int(c), "first": f, "last": last} for n, g, c, f, last in rows]


class RunMetricRepository(BaseLocalRepository, RunMetricPort):

    def __init__(self, session: Session, factory=None):
        super().__init__(session)
        self.factory = factory
        self.mapper = RunMetricMapper()

    @property
    def model_class(self):
        return RunMetricModel

    @property
    def entity_class(self):
        return RunMetric

    def _to_entity(self, orm_obj):
        return self.mapper.to_domain(orm_obj)

    def _to_model(self, entity):
        return self.mapper.to_orm(entity)

    def _create_or_get(self, *args, **kwargs):
        raise NotImplementedError("run metrics are written with replace()")

    def replace(self, run_id: int, metrics: List[RunMetric]) -> int:
        for m in metrics:
            if m.run_id != run_id:
                raise ValueError(f"metric of run {m.run_id} written under run {run_id}")
            row = (self.session.query(RunMetricModel)
                   .filter(RunMetricModel.run_id == run_id, RunMetricModel.scope == m.scope,
                           RunMetricModel.metric_name == m.metric_name).one_or_none())
            if row is None:
                m.value = _clean(m.value)
                self.session.add(self._to_model(m))
            else:
                row.value = _clean(m.value)
        self.session.commit()
        return len(metrics)

    def get_by_run(self, run_id: int, scope: Optional[str] = None) -> List[RunMetric]:
        return self.get_by_runs([run_id], scope)

    def get_by_runs(self, run_ids: List[int], scope: Optional[str] = None) -> List[RunMetric]:
        if not run_ids:
            return []
        q = self.session.query(RunMetricModel).filter(RunMetricModel.run_id.in_(list(run_ids)))
        if scope:
            q = q.filter(RunMetricModel.scope == scope)
        return [self._to_entity(m) for m in q.order_by(RunMetricModel.run_id, RunMetricModel.scope,
                                                       RunMetricModel.metric_name)]


class PortfolioValueReader:
    """The engine's daily book value of a portfolio: its PortfolioValueFactor values (read only)."""

    def __init__(self, session: Session):
        self.session = session

    def value_series(self, portfolio_id: int, start: Optional[datetime] = None,
                     end: Optional[datetime] = None) -> List[tuple]:
        from src.infrastructure.models.factor.factor import FactorModel
        from src.infrastructure.models.factor.factor_value import FactorValueModel
        q = (self.session.query(FactorValueModel.date, FactorValueModel.value)
             .join(FactorModel, FactorModel.id == FactorValueModel.factor_id)
             .filter(FactorModel.factor_type == PORTFOLIO_VALUE_FACTOR_TYPE,
                     FactorValueModel.entity_type == PORTFOLIO_ENTITY_TYPE,
                     FactorValueModel.entity_id == portfolio_id))
        if start is not None:
            q = q.filter(FactorValueModel.date >= start)
        if end is not None:
            q = q.filter(FactorValueModel.date <= end)
        out = []
        for date, value in q.order_by(FactorValueModel.date).all():
            try:
                v = float(Decimal(str(value)))
            except (InvalidOperation, ValueError):
                continue
            if math.isfinite(v):
                out.append((date, v))
        return out

    def portfolio_names(self, portfolio_ids: List[int]) -> Dict[int, str]:
        from src.infrastructure.models.finance.portfolio.portfolio import PortfolioModel
        if not portfolio_ids:
            return {}
        return {pid: name for pid, name in self.session.query(PortfolioModel.id, PortfolioModel.name)
                .filter(PortfolioModel.id.in_(list(portfolio_ids))).all()}
