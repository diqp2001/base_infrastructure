"""
Generic research results of a BacktestRun (2026-11-18): what a project publishes beyond the engine's book.

ResearchSeriesValue  one dated value of a named series, e.g. 'A/gross/D10', 'A/gross/D10-D1', 'original_pnl'.
                     ``series_group`` gathers related series for display ('A/gross' = the deciles of model A).
RunMetric            one named metric, e.g. sharpe_ratio, decile_monotonicity. ``scope`` separates the engine's
                     metrics (computed from the portfolio value curve) from each project's research metrics
                     ('engine', 'A/gross', 'B/net', 'comparison').

No project has to publish the same names: the registry stores whatever a project names.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from src.domain.entities.entity import Entity

ENGINE_SCOPE = "engine"


class ResearchSeriesValue(Entity):

    def __init__(self, run_id: int, series_name: str, date: datetime, value: Optional[float],
                 series_group: Optional[str] = None, id: Optional[int] = None):
        super().__init__(id)
        if not series_name:
            raise ValueError("a research series needs a name")
        self.run_id = run_id
        self.series_name = series_name
        self.series_group = series_group
        self.date = date
        self.value = value

    def __repr__(self) -> str:
        return f"<ResearchSeriesValue(run={self.run_id}, {self.series_name}, {self.date}, {self.value})>"


class RunMetric(Entity):

    def __init__(self, run_id: int, metric_name: str, value: Optional[float], scope: str = ENGINE_SCOPE,
                 id: Optional[int] = None):
        super().__init__(id)
        if not metric_name:
            raise ValueError("a run metric needs a name")
        self.run_id = run_id
        self.metric_name = metric_name
        self.value = value
        self.scope = scope

    def __repr__(self) -> str:
        return f"<RunMetric(run={self.run_id}, {self.scope}/{self.metric_name}={self.value})>"
