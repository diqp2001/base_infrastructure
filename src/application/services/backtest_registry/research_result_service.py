"""
ResearchResultService - what a run publishes beyond the engine's book (2026-11-18).

    publish_series(run_id, "A/gross/D10", series, group="A/gross")     any named, dated series
    publish_frame(run_id, frame, group="A/gross", prefix="A/gross/")   one series per column of a dated frame
    publish_metrics(run_id, {"sharpe_ratio": 0.8}, scope="A/gross")    any named metric
    engine_metrics(run_id, metrics_fn)                                  from the engine's portfolio value curve

Republishing replaces the run's points of the same series names (a project may publish after every month).
Engine metrics come from the existing Misbuffet ``calculate_performance_metrics`` (passed in by the runner as
``metrics_fn``: the registry never imports misbuffet) on the main portfolio's daily PortfolioValueFactor values;
nothing here is a second performance engine.
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import Dict, List, Mapping, Optional

import pandas as pd

from src.domain.entities.backtest.research_result import ENGINE_SCOPE, ResearchSeriesValue, RunMetric


def _to_datetime(value) -> datetime:
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        ts = ts.tz_convert(None)
    return ts.to_pydatetime()


def daily_curve(points: List[tuple]) -> pd.Series:
    """(timestamp, value) points -> one value per calendar day (the last of the day)."""
    if not points:
        return pd.Series(dtype=float)
    s = pd.Series([v for _, v in points], index=pd.DatetimeIndex([_to_datetime(t) for t, _ in points]))
    s = s.sort_index()
    return s.groupby(s.index.normalize()).last()


class ResearchResultService:

    def __init__(self, factory):
        self.factory = factory
        self.series = factory.research_series_local_repo
        self.metrics = factory.run_metric_local_repo
        self.run_portfolios = factory.backtest_run_portfolio_local_repo

    # -- research series ----------------------------------------------------------------------------------------
    def publish_series(self, run_id: int, name: str, series, group: Optional[str] = None) -> int:
        s = series if isinstance(series, pd.Series) else pd.Series(series)
        values = [ResearchSeriesValue(run_id=run_id, series_name=name, series_group=group, date=_to_datetime(d),
                                      value=None if v is None or (isinstance(v, float) and math.isnan(v))
                                      else float(v))
                  for d, v in s.items()]
        return self.series.replace(run_id, values, series_names=[name])

    def publish_frame(self, run_id: int, frame: pd.DataFrame, group: Optional[str] = None,
                      prefix: str = "") -> int:
        values, names = [], []
        for column in frame.columns:
            name = f"{prefix}{column}"
            names.append(name)
            for d, v in frame[column].items():
                values.append(ResearchSeriesValue(
                    run_id=run_id, series_name=name, series_group=group, date=_to_datetime(d),
                    value=None if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)))
        return self.series.replace(run_id, values, series_names=names)

    # -- metrics ------------------------------------------------------------------------------------------------
    def publish_metrics(self, run_id: int, metrics: Mapping[str, object], scope: str = ENGINE_SCOPE) -> int:
        rows = []
        for name, value in metrics.items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue                                  # numbers only; text belongs in the run's assumptions
            rows.append(RunMetric(run_id=run_id, metric_name=str(name), value=float(value), scope=scope))
        return self.metrics.replace(run_id, rows)

    # -- engine -------------------------------------------------------------------------------------------------
    def main_portfolio_ids(self, run_id: int) -> List[int]:
        return [p.portfolio_id for p in self.run_portfolios.get_by_run(run_id) if p.role == "main"]

    def equity_curve(self, run_id: int, portfolio_id: Optional[int] = None) -> pd.Series:
        from src.infrastructure.repositories.local_repo.backtest.research_result_repository import (
            PortfolioValueReader,
        )
        ids = [portfolio_id] if portfolio_id is not None else self.main_portfolio_ids(run_id)
        if not ids:
            return pd.Series(dtype=float)
        reader = PortfolioValueReader(self.factory.session)
        return daily_curve(reader.value_series(ids[0]))

    def engine_metrics(self, run_id: int, metrics_fn, starting_capital: Optional[float] = None) -> Dict[str, float]:
        """Generic performance of the run's main book, stored under scope 'engine'."""
        curve = self.equity_curve(run_id)
        if len(curve) < 2:
            return {}
        initial = float(starting_capital) if starting_capital else float(curve.iloc[0])
        returns = curve.pct_change().dropna()
        returns = returns[returns.map(math.isfinite)]
        metrics = metrics_fn(list(returns.values), initial, float(curve.iloc[-1]))
        if "error" in metrics and len(metrics) <= 2:
            return {}
        metrics = {k: v for k, v in metrics.items() if k != "error"}
        metrics["cumulative_return"] = metrics.get("total_return")
        metrics["annualized_volatility"] = metrics.get("volatility")
        metrics["calmar_ratio"] = (metrics["annualized_return"] / abs(metrics["max_drawdown"])
                                   if metrics.get("max_drawdown") else None)
        metrics["final_value"] = float(curve.iloc[-1])
        self.publish_metrics(run_id, metrics, scope=ENGINE_SCOPE)
        return metrics
