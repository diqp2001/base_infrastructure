"""
Strategy returns of every project's stored results, prepared for factor analysis.

Each results source (a project's results folder) holds that project's own report. This module turns it into
return series that can be regressed on factor returns:

* STM and cross-sectional reports stamp a strategy's return at the DECISION (session or bar) although it is
  earned from that close to the next one. Each return is re-stamped at the bar where it is REALISED: the next bar
  of the NYSE grid (the next session for daily strategies). Without this, a daily return would be aligned with the
  previous day's factor returns.
* SPX v2 reports a funded portfolio's equity; its returns are equity(t) / equity(t-1) - 1, already stamped at t.

Return convention (CONVENTIONS): a long-only or SPX portfolio reports total returns (the risk-free rate is
subtracted once in the regression); long-short and position-scaled strategies are self-financing (already excess
returns). The default can be overridden per analysis.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

import pandas as pd

from src.domain.entities.research.factor_models import EXCESS, TOTAL


@dataclass
class StrategyReturns:
    name: str
    returns: pd.Series                     # realised-stamped simple returns, one per bar
    convention: str                        # TOTAL | EXCESS
    bar_minutes: Optional[int]             # None = daily bars
    source: str                            # where the series comes from (report field)
    notes: List[str] = field(default_factory=list)


@dataclass
class ResultSource:
    key: str                               # e.g. 'stm:10m', 'csm:cross_sectional', 'spx_v2', 'experiment:3'
    label: str
    kind: str                              # 'stm' | 'csm' | 'spx' (which report type)
    results_dir: Callable[[], Optional[str]]


def infer_bar_minutes(index: pd.DatetimeIndex) -> Optional[int]:
    """None for one row per session; otherwise the most common intraday spacing in minutes."""
    idx = pd.DatetimeIndex(index)
    if len(idx) < 2 or (idx == idx.normalize()).all():
        return None
    same_day = pd.Series(idx[1:] - idx[:-1])[pd.Series(idx[1:].normalize() == idx[:-1].normalize())]
    if same_day.empty:
        return None
    return int(round(same_day.mode().iloc[0].total_seconds() / 60))


def realised_index(decision_index: pd.DatetimeIndex, bar_minutes: Optional[int]) -> pd.DatetimeIndex:
    """The bar after each decision on the NYSE grid (holidays and early closes respected)."""
    from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_data_coverage import (
        expected_bars,
    )
    idx = pd.DatetimeIndex(decision_index)
    if idx.empty:
        return idx
    grid = expected_bars(idx.min(), idx.max() + pd.Timedelta(days=10), bar_minutes)
    pos = grid.searchsorted(idx, side="right")
    if (pos >= len(grid)).any():
        raise ValueError("the NYSE grid does not extend past the last decision")
    return grid[pos]


def _default_convention(name: str, kind: str) -> str:
    return TOTAL if kind == "spx" or "long only" in name.lower() else EXCESS


def strategies_of(report, kind: str) -> Dict[str, StrategyReturns]:
    """Every strategy of a stored report as realised-stamped returns."""
    out: Dict[str, StrategyReturns] = {}
    if kind == "spx":
        r = pd.Series(report.returns, dtype=float).dropna()
        out["SPX v2 portfolio"] = StrategyReturns(
            "SPX v2 portfolio", r, TOTAL, infer_bar_minutes(r.index), "report.returns (portfolio equity)",
            ["Funded portfolio: total returns of the account value (no deposits / withdrawals during a backtest)."])
        return out
    frame = getattr(report, "raw_returns", None) if kind == "stm" else getattr(report, "returns", None)
    field_name = "raw_returns" if kind == "stm" else "returns"
    if frame is None or frame.empty:
        return out
    bar = infer_bar_minutes(frame.index)
    realised = realised_index(frame.index, bar)
    for name in frame.columns:
        r = pd.Series(frame[name].to_numpy(dtype=float), index=realised).dropna()
        out[str(name)] = StrategyReturns(
            str(name), r, _default_convention(str(name), kind), bar, f"report.{field_name}",
            ["Re-stamped from the decision bar to the bar where the return is realised (next NYSE bar)."])
    return out


def primary_strategy(report, kind: str, strategies: Dict[str, StrategyReturns]) -> Optional[str]:
    name = getattr(report, "model_name", None)
    if name in strategies:
        return name
    return next(iter(strategies), None)


def _config_dir(module: str) -> Callable[[], Optional[str]]:
    def results_dir():
        try:
            return importlib.import_module(module).get_config()["results_dir"]
        except Exception:
            return None
    return results_dir


PM = "src.application.managers.project_managers."
PROJECT_SOURCES: List[ResultSource] = [
    ResultSource("stm:daily", "STM — daily (reference sample)", "stm", _config_dir(PM + "spatio_temporal_momentum_project.config")),
    ResultSource("stm:full", "STM — paper universe", "stm", _config_dir(PM + "spatio_temporal_momentum_project_full.config")),
    ResultSource("stm:10m", "STM — 10-minute bars", "stm", _config_dir(PM + "spatio_temporal_momentum_project_10m.config")),
    ResultSource("csm:cross_sectional", "Cross-sectional momentum — daily", "csm",
                 _config_dir(PM + "cross_sectionnal_project.config")),
    ResultSource("csm:csm_10m", "Cross-sectional momentum — 10-minute bars", "csm",
                 _config_dir(PM + "cross_sectionnal_project_10m.config")),
    ResultSource("spx_v2", "SPX call spread market maker (v2)", "spx",
                 _config_dir(PM + "market_making_SPX_call_spread_project_v2.config")),
]


class ProjectReturnsService:
    """Lists the results sources and loads their strategies' returns (each project's own report store)."""

    def __init__(self, sources: Optional[List[ResultSource]] = None,
                 experiment_sources: Optional[Callable[[], List[ResultSource]]] = None):
        self._sources = list(PROJECT_SOURCES if sources is None else sources)
        self._experiment_sources = experiment_sources

    def sources(self) -> List[ResultSource]:
        extra = []
        if self._experiment_sources is not None:
            try:
                extra = self._experiment_sources()
            except Exception:
                extra = []
        return self._sources + extra

    def source(self, key: str) -> ResultSource:
        for s in self.sources():
            if s.key == key:
                return s
        raise LookupError(f"unknown results source '{key}'")

    @staticmethod
    def load_report(source: ResultSource):
        directory = source.results_dir()
        if not directory:
            return None
        if source.kind == "spx":
            # loaded by name like the project configs: services never import the managers package statically
            store = importlib.import_module(PM + "market_making_SPX_call_spread_project_v2.reporting.spx_report_store")
        else:
            from src.application.services.data.entities.factor.spatio_temporal_momentum import (
                stm_report_store as store,
            )
        if store.report_mtime(directory) is None:
            return None
        return store.load_report(directory)

    def strategies(self, key: str):
        """(source, report or None, {name: StrategyReturns}, primary strategy name)."""
        source = self.source(key)
        report = self.load_report(source)
        if report is None:
            return source, None, {}, None
        strategies = strategies_of(report, source.kind)
        return source, report, strategies, primary_strategy(report, source.kind, strategies)
