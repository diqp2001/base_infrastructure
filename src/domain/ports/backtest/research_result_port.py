"""Ports of the generic research results of a backtest run (2026-11-18): named series and metrics."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional

from src.domain.entities.backtest.research_result import ResearchSeriesValue, RunMetric


class ResearchSeriesPort(ABC):

    @abstractmethod
    def replace(self, run_id: int, values: List[ResearchSeriesValue],
                series_names: Optional[List[str]] = None) -> int:
        """Store ``values``; the run's existing points of the same series names are replaced (a project
        republishing after every month never duplicates). Returns the number of points stored."""

    @abstractmethod
    def get_by_run(self, run_id: int, series_names: Optional[List[str]] = None,
                   series_group: Optional[str] = None) -> List[ResearchSeriesValue]: ...

    @abstractmethod
    def series_names(self, run_id: int) -> List[Dict[str, object]]:
        """[{name, group, points, first, last}] of the run's series."""


class RunMetricPort(ABC):

    @abstractmethod
    def replace(self, run_id: int, metrics: List[RunMetric]) -> int:
        """Store ``metrics``; an existing (scope, name) of the run is overwritten."""

    @abstractmethod
    def get_by_run(self, run_id: int, scope: Optional[str] = None) -> List[RunMetric]: ...

    @abstractmethod
    def get_by_runs(self, run_ids: List[int], scope: Optional[str] = None) -> List[RunMetric]: ...
