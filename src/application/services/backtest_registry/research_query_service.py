"""
ResearchQueryService - read side of the research / backtest registry (2026-11-18), used by the API and the pages.

Everything is read through repositories (never the ORM from Flask). Series sent to a page are daily at most and
downsampled to ``max_points``: a 10-minute run's detail stays in the database for the engine.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from src.application.services.backtest_registry.model_registry_service import ModelRegistryService
from src.application.services.backtest_registry.research_result_service import ResearchResultService, daily_curve
from src.domain.entities.backtest.research_result import ENGINE_SCOPE
from src.domain.entities.backtest.run_comparison import compare_runs

HEADLINE = ("cumulative_return", "sharpe_ratio", "max_drawdown")
COMPARED_METRICS = ("cumulative_return", "annualized_return", "annualized_volatility", "sharpe_ratio",
                    "max_drawdown", "calmar_ratio", "win_rate", "total_trading_days")
MAX_POINTS = 1500


def downsample(series: pd.Series, max_points: int = MAX_POINTS) -> pd.Series:
    if len(series) <= max_points:
        return series
    step = -(-len(series) // max_points)
    picked = series.iloc[::step]
    return picked if picked.index[-1] == series.index[-1] else pd.concat([picked, series.iloc[-1:]])


def _points(series: pd.Series) -> List[Dict[str, Any]]:
    return [{"date": d.date().isoformat() if hasattr(d, "date") else str(d),
             "value": None if pd.isna(v) else float(v)} for d, v in series.items()]


class ResearchQueryService:

    def __init__(self, factory):
        self.factory = factory
        self.runs = factory.backtest_run_local_repo
        self.run_portfolios = factory.backtest_run_portfolio_local_repo
        self.run_models = factory.backtest_run_model_link_local_repo
        self.series_repo = factory.research_series_local_repo
        self.metric_repo = factory.run_metric_local_repo
        self.results = ResearchResultService(factory)
        self.models = ModelRegistryService(factory)

    @property
    def books(self):
        """Every backtest's book, drilled down (BacktestBookService)."""
        from src.application.services.backtest_registry.backtest_book_service import BacktestBookService
        from src.infrastructure.repositories.local_repo.backtest.backtest_book_repository import BacktestBookReader
        return BacktestBookService(BacktestBookReader(self.factory.session), runs=self.runs,
                                   run_portfolios=self.run_portfolios,
                                   experiments=self.factory.strategy_experiment_local_repo,
                                   strategies=self.factory.strategy_local_repo)

    # -- runs ---------------------------------------------------------------------------------------------------
    def list_runs(self, project: Optional[str] = None, model_id: Optional[int] = None, status: Optional[str] = None,
                  universe: Optional[str] = None, created_from: Optional[datetime] = None,
                  created_to: Optional[datetime] = None, limit: int = 200) -> List[Dict[str, Any]]:
        runs = self.runs.find(project_name=project, status=status, limit=limit)
        if model_id is not None:
            allowed = {link.run_id for link in self.run_models.get_by_model(model_id)}
            runs = [r for r in runs if r.id in allowed]
        if universe:
            runs = [r for r in runs if universe.lower() in (r.universe_description or "").lower()]
        if created_from is not None:
            runs = [r for r in runs if r.created_at and r.created_at >= created_from]
        if created_to is not None:
            runs = [r for r in runs if r.created_at and r.created_at <= created_to]
        ids = [r.id for r in runs]
        metrics = {}
        for m in self.metric_repo.get_by_runs(ids, scope=ENGINE_SCOPE):
            metrics.setdefault(m.run_id, {})[m.metric_name] = m.value
        models = self._model_names(ids)
        return [{**r.to_dict(), "models": models.get(r.id, []),
                 **{k: metrics.get(r.id, {}).get(k) for k in HEADLINE}} for r in runs]

    def _model_names(self, run_ids: List[int]) -> Dict[int, List[Dict[str, Any]]]:
        out: Dict[int, List[Dict[str, Any]]] = {}
        cache: Dict[int, Any] = {}
        for run_id, links in self.run_models.models_by_run(run_ids).items():
            for link in links:
                if link.ml_model_id not in cache:
                    cache[link.ml_model_id] = self.factory.ml_model_local_repo.get_by_id(link.ml_model_id)
                m = cache[link.ml_model_id]
                cfg = (m.configuration if m is not None and isinstance(m.configuration, dict) else {}) or {}
                out.setdefault(run_id, []).append({
                    "id": link.ml_model_id, "name": m.name if m else None, "role": link.role,
                    "version": cfg.get("version"), "algorithm": cfg.get("algorithm") or (m.model_type if m else None),
                    "features": cfg.get("features"), "hyperparameters": cfg.get("hyperparameters")})
        return out

    def run(self, run_id: int) -> Optional[Dict[str, Any]]:
        r = self.runs.get_by_id(run_id)
        if r is None:
            return None
        from src.infrastructure.repositories.local_repo.backtest.research_result_repository import (
            PortfolioValueReader,
        )
        links = self.run_portfolios.get_by_run(run_id)
        names = PortfolioValueReader(self.factory.session).portfolio_names([p.portfolio_id for p in links])
        return {**r.to_dict(), "config_snapshot": r.config_snapshot,
                "portfolios": [{**p.to_dict(), "name": names.get(p.portfolio_id)} for p in links],
                "models": self._model_names([run_id]).get(run_id, []),
                "series": [{**s, "first": str(s["first"])[:10], "last": str(s["last"])[:10]}
                           for s in self.series_repo.series_names(run_id)],
                "metric_scopes": sorted({m.scope for m in self.metric_repo.get_by_run(run_id)})}

    def equity(self, run_id: int, max_points: int = MAX_POINTS) -> Dict[str, Any]:
        out = {"run_id": run_id, "portfolios": []}
        names = {}
        try:
            from src.infrastructure.repositories.local_repo.backtest.research_result_repository import (
                PortfolioValueReader,
            )
            reader = PortfolioValueReader(self.factory.session)
            links = [p for p in self.run_portfolios.get_by_run(run_id) if p.role in ("main", "benchmark", "variant",
                                                                                     "sleeve")]
            names = reader.portfolio_names([p.portfolio_id for p in links])
            for p in links:
                curve = downsample(daily_curve(reader.value_series(p.portfolio_id)), max_points)
                out["portfolios"].append({"portfolio_id": p.portfolio_id, "role": p.role, "label": p.label,
                                          "name": names.get(p.portfolio_id), "points": _points(curve)})
        except Exception as e:
            out["error"] = str(e)
        return out

    def metrics(self, run_id: int) -> Dict[str, Dict[str, Optional[float]]]:
        out: Dict[str, Dict[str, Optional[float]]] = {}
        for m in self.metric_repo.get_by_run(run_id):
            out.setdefault(m.scope, {})[m.metric_name] = m.value
        return out

    def series(self, run_id: int, names: Optional[List[str]] = None, group: Optional[str] = None,
               max_points: int = MAX_POINTS) -> Dict[str, Any]:
        rows = self.series_repo.get_by_run(run_id, series_names=names, series_group=group)
        by_name: Dict[str, List] = {}
        groups: Dict[str, Optional[str]] = {}
        for v in rows:
            by_name.setdefault(v.series_name, []).append((v.date, v.value))
            groups[v.series_name] = v.series_group
        out = []
        for name, pts in by_name.items():
            s = pd.Series([v for _, v in pts], index=pd.DatetimeIndex([d for d, _ in pts])).sort_index()
            out.append({"name": name, "group": groups[name], "points": _points(downsample(s, max_points))})
        return {"run_id": run_id, "series": out}

    # -- comparison ---------------------------------------------------------------------------------------------
    def compare(self, run_ids: List[int], max_points: int = MAX_POINTS) -> Dict[str, Any]:
        runs = [self.runs.get_by_id(i) for i in run_ids]
        missing = [i for i, r in zip(run_ids, runs) if r is None]
        if missing:
            raise LookupError(f"unknown run(s): {missing}")
        models = self._model_names(run_ids)
        comparison = compare_runs(runs, models_by_run=models)
        metric_rows = {}
        for m in self.metric_repo.get_by_runs(run_ids, scope=ENGINE_SCOPE):
            metric_rows.setdefault(m.metric_name, {})[str(m.run_id)] = m.value
        names = sorted(set(COMPARED_METRICS) | set(metric_rows),
                       key=lambda n: (COMPARED_METRICS.index(n) if n in COMPARED_METRICS else 99, n))
        curves = []
        for r in runs:
            eq = self.equity(r.id, max_points)
            main = next((p for p in eq["portfolios"] if p["role"] == "main"), None)
            pts = main["points"] if main else []
            base = next((p["value"] for p in pts if p["value"]), None)
            curves.append({"run_id": r.id, "label": f"Run {r.id} - {r.project_name}", "status": r.status,
                           "points": [{"date": p["date"], "value": (p["value"] / base) if base and p["value"]
                                       is not None else None} for p in pts]})
        return {**comparison.to_dict(),
                "runs": [{**r.to_dict(), "models": models.get(r.id, [])} for r in runs],
                "metrics": [{"name": n, "by_run": {str(i): metric_rows.get(n, {}).get(str(i)) for i in run_ids}}
                            for n in names],
                "equity": curves,
                "note": "Equity curves are rebased to 1 at each run's first value. Viewable is not the same as "
                        "comparable: read the warnings first."}

    # -- models -------------------------------------------------------------------------------------------------
    def list_models(self) -> List[Dict[str, Any]]:
        return self.models.list_models()

    def model(self, model_id: int) -> Optional[Dict[str, Any]]:
        return self.models.describe(model_id)

    def model_runs(self, model_id: int) -> List[Dict[str, Any]]:
        return self.models.runs_of_model(model_id)

    def model_artifacts(self, model_id: int) -> List[Dict[str, Any]]:
        return self.models.artifacts_of_model(model_id)

    def projects(self) -> List[str]:
        return sorted({r.project_name for r in self.runs.find(limit=5000)})
