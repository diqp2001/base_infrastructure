"""
StrategyExperiment — one run of a locked Strategy version (a backtest today).

It records what the run used and produced, so a result can always be traced back and reproduced: its own window
(backtest_start / backtest_end / initial_capital - a strategy runs over any window, many backtests per strategy),
the strategy id and its content hash at launch, the job that ran it (process, host, heartbeat, log), the
results folder (one per experiment, never shared), and ``provenance`` (model artifacts, universe membership
used per decision, data coverage of the preload) and ``summary`` (headline metrics of the report).

Status lifecycle: queued -> running -> succeeded | failed | interrupted (the worker process disappeared).
``kind`` distinguishes backtest from paper / live results; only 'backtest' can be launched today.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from src.domain.entities.entity import Entity

BACKTEST, PAPER, LIVE = "backtest", "paper", "live"
KINDS = (BACKTEST, PAPER, LIVE)
QUEUED, RUNNING, SUCCEEDED, FAILED, INTERRUPTED = "queued", "running", "succeeded", "failed", "interrupted"
STATUSES = (QUEUED, RUNNING, SUCCEEDED, FAILED, INTERRUPTED)
FINISHED = (SUCCEEDED, FAILED, INTERRUPTED)


class StrategyExperiment(Entity):

    def __init__(self, strategy_id: int, strategy_hash: str, strategy_type: str, id: Optional[int] = None,
                 kind: str = BACKTEST, status: str = QUEUED, results_dir: Optional[str] = None,
                 log_path: Optional[str] = None, pid: Optional[int] = None, host: Optional[str] = None,
                 created_at: Optional[datetime] = None, started_at: Optional[datetime] = None,
                 finished_at: Optional[datetime] = None, heartbeat_at: Optional[datetime] = None,
                 error: Optional[str] = None, provenance: Optional[Dict[str, Any]] = None,
                 summary: Optional[Dict[str, Any]] = None, backtest_start: Optional[datetime] = None,
                 backtest_end: Optional[datetime] = None, initial_capital: Optional[float] = None):
        super().__init__(id)
        if kind not in KINDS:
            raise ValueError(f"unknown experiment kind '{kind}'")
        if status not in STATUSES:
            raise ValueError(f"unknown experiment status '{status}'")
        self.strategy_id = strategy_id
        self.strategy_hash = strategy_hash
        self.strategy_type = strategy_type
        self.kind = kind
        self.status = status
        self.results_dir = results_dir
        self.log_path = log_path
        self.pid = pid
        self.host = host
        self.created_at = created_at
        self.started_at = started_at
        self.finished_at = finished_at
        self.heartbeat_at = heartbeat_at
        self.error = error
        if backtest_start is not None and backtest_end is not None and backtest_end <= backtest_start:
            raise ValueError(f"backtest end {backtest_end} must be after its start {backtest_start}")
        if initial_capital is not None and initial_capital <= 0:
            raise ValueError("the starting capital must be positive")
        # the window of THIS backtest (None: recorded before windows existed - the strategy's own dates applied)
        self.backtest_start = backtest_start
        self.backtest_end = backtest_end
        self.initial_capital = initial_capital
        self.provenance: Dict[str, Any] = dict(provenance or {})
        self.summary: Dict[str, Any] = dict(summary or {})

    # former StrategyConfiguration names (read-only aliases)
    @property
    def configuration_id(self) -> int:
        return self.strategy_id

    @property
    def configuration_hash(self) -> str:
        return self.strategy_hash

    @property
    def project_key(self) -> str:
        return self.strategy_type

    @property
    def is_finished(self) -> bool:
        return self.status in FINISHED

    def start(self, pid: int, host: str, at: datetime) -> None:
        if self.status != QUEUED:
            raise ValueError(f"experiment {self.id} cannot start from status '{self.status}'")
        self.status, self.pid, self.host, self.started_at, self.heartbeat_at = RUNNING, pid, host, at, at

    def beat(self, at: datetime) -> None:
        self.heartbeat_at = at

    def succeed(self, at: datetime, summary: Optional[Dict[str, Any]] = None,
                provenance: Optional[Dict[str, Any]] = None) -> None:
        self._finish(SUCCEEDED, at)
        self.summary.update(summary or {})
        self.provenance.update(provenance or {})

    def fail(self, at: datetime, error: str) -> None:
        self._finish(FAILED, at)
        self.error = error

    def interrupt(self, at: datetime, reason: str) -> None:
        self._finish(INTERRUPTED, at)
        self.error = reason

    def _finish(self, status: str, at: datetime) -> None:
        if self.is_finished:
            raise ValueError(f"experiment {self.id} is already {self.status}")
        self.status, self.finished_at = status, at

    def to_dict(self) -> Dict[str, Any]:
        return {k: getattr(self, k) for k in (
            "id", "strategy_id", "strategy_hash", "strategy_type", "kind", "status", "results_dir",
            "log_path", "pid", "host", "created_at", "started_at", "finished_at", "heartbeat_at", "error",
            "backtest_start", "backtest_end", "initial_capital", "provenance", "summary")}

    def __repr__(self) -> str:
        return f"<StrategyExperiment(id={self.id}, strategy={self.strategy_id}, {self.kind}, {self.status})>"
