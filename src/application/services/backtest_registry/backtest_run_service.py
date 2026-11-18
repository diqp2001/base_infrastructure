"""
BacktestRunService - identity and lifecycle of backtest runs (generic research / backtest registry, 2026-11-18).

    run = service.register("stm_monthly_deciles", config, describe={...})    PENDING, config snapshot, git commit
    service.start(run)                                                        RUNNING
    tracker = service.tracker(run)       tracker.bar(t) per engine bar        actual window, months done, heartbeat
    service.register_portfolio_tree(run, main_portfolio_id)                   the run's portfolios
    service.link_model(run, ml_model_id, role) / link_artifacts(run, ids)     the models it used
    service.finish(run, error=None, cancelled=False)                          COMPLETED | PARTIAL | FAILED | CANCELLED

The final status comes from what the engine PROCESSED (BacktestRun.finish), not from the process exiting.
``recover()`` closes runs whose worker is gone (crash, reboot, killed): PARTIAL when some months were processed,
else FAILED.
"""

from __future__ import annotations

import logging
import os
import socket
import time
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List, Optional

from src.application.services.backtest_registry import run_identity
from src.domain.entities.backtest.backtest_run import RUNNING, BacktestRun

logger = logging.getLogger(__name__)

STALE_AFTER = timedelta(minutes=10)          # no heartbeat for this long and the worker process is gone
FLUSH_SECONDS = 30.0                          # progress written at most every 30 s (and at the end)


def describe_from_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run attributes every project's config can supply (a project's runner may add or override them)."""
    universe = config.get("universe")
    if isinstance(universe, dict):
        listed = {getattr(k, "__name__", str(k)): list(v) if isinstance(v, (list, tuple)) else v
                  for k, v in universe.items()}
        n = sum(len(v) for v in listed.values() if isinstance(v, list))
        description = ", ".join(f"{k}: {len(v)} names" if isinstance(v, list) else f"{k}: {v}"
                                for k, v in listed.items())
        snapshot = {"members": listed, "size": n}
    else:
        description, snapshot = (str(universe) if universe else None), {}
    portfolio = config.get("Portfolio") or {}
    return {
        "universe_description": description,
        "universe_snapshot": snapshot,
        "starting_capital": config.get("initial_capital") or portfolio.get("initial_cash"),
        "price_source": config.get("price_source"),
    }


class RunProgressTracker:
    """Per-bar progress of one run: the actual window, months covered, heartbeat; written at most every
    ``flush_seconds`` so a 10-minute backtest does not write a row per bar."""

    def __init__(self, service: "BacktestRunService", run: BacktestRun, flush_seconds: float = FLUSH_SECONDS,
                 monotonic: Callable[[], float] = time.monotonic):
        self.service, self.run = service, run
        self.flush_seconds, self._monotonic = flush_seconds, monotonic
        self._last_flush = monotonic()

    def bar(self, bar_time: Optional[datetime]) -> None:
        if bar_time is None:
            return
        if getattr(bar_time, "tzinfo", None) is not None:
            bar_time = bar_time.replace(tzinfo=None)
        self.run.record_bar(bar_time, at=self.service.clock())
        if self._monotonic() - self._last_flush >= self.flush_seconds:
            self.flush()

    def flush(self) -> None:
        self._last_flush = self._monotonic()
        try:
            self.run = self.service.save(self.run)
        except Exception as e:                       # progress must never stop a backtest
            logger.warning(f"backtest run {self.run.id}: progress not saved: {e}")


class BacktestRunService:

    def __init__(self, factory, clock: Callable[[], datetime] = datetime.now,
                 git: Optional[Callable[[], run_identity.GitState]] = None,
                 branch: Optional[Callable[[], Optional[str]]] = None):
        self.factory = factory
        self.runs = factory.backtest_run_local_repo
        self.portfolios = factory.backtest_run_portfolio_local_repo
        self.models = factory.backtest_run_model_link_local_repo
        self.clock = clock
        self._git = git or run_identity.git_state
        self._branch = branch or run_identity.git_branch

    # -- lifecycle ----------------------------------------------------------------------------------------------
    def register(self, project_name: str, config: Dict[str, Any], run_name: Optional[str] = None,
                 requested_start: Optional[datetime] = None, requested_end: Optional[datetime] = None,
                 describe: Optional[Dict[str, Any]] = None, kind: str = "backtest") -> BacktestRun:
        git = self._git()
        snapshot = run_identity._redact(run_identity._jsonable(config))
        attrs = describe_from_config(config)
        attrs.update({k: v for k, v in (describe or {}).items() if v is not None})
        run = BacktestRun(
            project_name=project_name, run_name=run_name, kind=kind,
            config_snapshot=snapshot, config_hash=run_identity.config_hash(config),
            code_commit=git.commit, code_dirty=git.dirty, code_branch=self._branch(),
            requested_start=requested_start, requested_end=requested_end,
            strategy_experiment_id=config.get("strategy_experiment_id"),
            results_dir=config.get("results_dir"), created_at=self.clock(),
            data_snapshot={"git_changed_files": list(git.changed_files)[:50],
                           "database": os.getenv("DB_NAME") or "base_infra",
                           **(attrs.pop("data_snapshot", None) or {})},
            **attrs)
        return self.runs.add(run)

    def start(self, run: BacktestRun, pid: Optional[int] = None, host: Optional[str] = None) -> BacktestRun:
        run.start(self.clock(), pid=pid or os.getpid(), host=host or socket.gethostname())
        return self.save(run)

    def tracker(self, run: BacktestRun, flush_seconds: float = FLUSH_SECONDS) -> RunProgressTracker:
        return RunProgressTracker(self, run, flush_seconds)

    def save(self, run: BacktestRun) -> BacktestRun:
        return self.runs.update(run) or run

    def finish(self, run: BacktestRun, error: Optional[str] = None, cancelled: bool = False) -> BacktestRun:
        fresh = self.runs.get_by_id(run.id) if run.id is not None else None
        if fresh is not None and fresh.is_finished:
            return fresh
        run.finish(self.clock(), error=error, cancelled=cancelled)
        return self.save(run)

    def recover(self, now: Optional[datetime] = None,
                alive: Optional[Callable[[Optional[int]], bool]] = None) -> List[BacktestRun]:
        """RUNNING runs whose worker is gone are closed: PARTIAL if some months were processed, else FAILED."""
        alive = alive or run_identity.pid_alive
        now = now or self.clock()
        closed = []
        for run in self.runs.find(status=RUNNING, limit=1000):
            beat = run.heartbeat_at or run.started_at
            same_host = run.host in (None, socket.gethostname())
            if beat is not None and now - beat < STALE_AFTER:
                continue
            if same_host and alive(run.pid):
                continue
            run.finish(now, error=f"worker gone (pid {run.pid} on {run.host}); last heartbeat {beat}")
            closed.append(self.save(run))
        return closed

    # -- associations -------------------------------------------------------------------------------------------
    def register_portfolio(self, run: BacktestRun, portfolio_id: int, role: str = "main",
                           label: Optional[str] = None):
        return self.portfolios._create_or_get(run.id, int(portfolio_id), role=role, label=label)

    def register_portfolio_tree(self, run: BacktestRun, main_portfolio_id: int,
                                label: Optional[str] = None) -> List[int]:
        """The main portfolio and every sub-portfolio it holds (cash, shares, options ...)."""
        self.register_portfolio(run, main_portfolio_id, role="main", label=label)
        subs = self.portfolios.sub_portfolio_ids(int(main_portfolio_id))
        for pid in subs:
            self.register_portfolio(run, pid, role="sub")
        return [int(main_portfolio_id)] + subs

    def link_model(self, run: BacktestRun, ml_model_id: int, role: str = "model",
                   model_artifact_id: Optional[int] = None):
        return self.models._create_or_get(run.id, int(ml_model_id), role=role, model_artifact_id=model_artifact_id)

    def link_artifacts(self, run: BacktestRun, artifact_ids: Iterable[int], role: str = "model") -> List[int]:
        """Models of the artifacts a run used (artifact -> training -> model); the newest artifact per model."""
        artifacts = self.factory.model_artifact_local_repo
        trainings = self.factory.model_training_local_repo
        latest: Dict[int, int] = {}
        for artifact_id in artifact_ids:
            artifact = artifacts.get_by_id(int(artifact_id))
            training = trainings.get_by_id(artifact.model_training_id) if artifact is not None else None
            if training is None:
                continue
            latest[training.model_id] = max(latest.get(training.model_id, 0), int(artifact_id))
        for model_id, artifact_id in latest.items():
            self.link_model(run, model_id, role=role, model_artifact_id=artifact_id)
        return list(latest)
