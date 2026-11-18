"""
BacktestRun - one execution of a backtest (generic research / backtest registry, 2026-11-18).

A run is an EXECUTION: it owns its identity (``run_uid``), the configuration snapshot it ran with, the code version,
the universe it traded, its market-data / cost assumptions, the window it was asked for and the window it actually
processed. Models are reusable research artifacts (``ml_models``); a run uses zero or more of them
(BacktestRunModel). The universe is a property of the RUN, never of the model.

Lifecycle:
    PENDING -> RUNNING -> COMPLETED | PARTIAL | FAILED | CANCELLED

A run is COMPLETED only when the last bar it processed reaches the requested end (within ``END_TOLERANCE_DAYS``,
weekends and holidays). A process that exits early is PARTIAL with months_completed < months_planned, never
COMPLETED: the engine returning normally is not evidence that the window was covered.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Dict, Optional

from src.domain.entities.entity import Entity

PENDING, RUNNING, COMPLETED, PARTIAL, FAILED, CANCELLED = (
    "PENDING", "RUNNING", "COMPLETED", "PARTIAL", "FAILED", "CANCELLED")
STATUSES = (PENDING, RUNNING, COMPLETED, PARTIAL, FAILED, CANCELLED)
FINISHED = (COMPLETED, PARTIAL, FAILED, CANCELLED)
END_TOLERANCE_DAYS = 4          # last bar on the Thursday before a Monday-holiday end still covers the window


def _as_date(value) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.fromisoformat(str(value)[:19]).date()


def months_between(start, end) -> int:
    """Calendar months from start to end, counting a partly covered month: 2021-01-04 .. 2022-12-09 = 23."""
    s, e = _as_date(start), _as_date(end)
    if s is None or e is None or e < s:
        return 0
    return (e.year - s.year) * 12 + (e.month - s.month)


class BacktestRun(Entity):

    def __init__(self, project_name: str, id: Optional[int] = None, run_uid: Optional[str] = None,
                 run_name: Optional[str] = None, kind: str = "backtest", status: str = PENDING,
                 config_snapshot: Optional[Dict[str, Any]] = None, config_hash: Optional[str] = None,
                 code_commit: Optional[str] = None, code_branch: Optional[str] = None,
                 code_dirty: Optional[bool] = None,
                 requested_start: Optional[datetime] = None, requested_end: Optional[datetime] = None,
                 actual_start: Optional[datetime] = None, actual_end: Optional[datetime] = None,
                 started_at: Optional[datetime] = None, completed_at: Optional[datetime] = None,
                 heartbeat_at: Optional[datetime] = None,
                 months_planned: Optional[int] = None, months_completed: Optional[int] = None,
                 bars_processed: int = 0,
                 starting_capital: Optional[float] = None, gross_leverage: Optional[float] = None,
                 universe_description: Optional[str] = None, universe_snapshot: Optional[Dict[str, Any]] = None,
                 price_source: Optional[str] = None, include_dividends: Optional[bool] = None,
                 include_transaction_costs: Optional[bool] = None,
                 assumptions: Optional[Dict[str, Any]] = None, data_snapshot: Optional[Dict[str, Any]] = None,
                 results_dir: Optional[str] = None, host: Optional[str] = None, pid: Optional[int] = None,
                 strategy_experiment_id: Optional[int] = None, error: Optional[str] = None,
                 created_at: Optional[datetime] = None):
        super().__init__(id)
        if status not in STATUSES:
            raise ValueError(f"unknown backtest run status {status!r}")
        self.project_name = project_name
        self.run_uid = run_uid or uuid.uuid4().hex
        self.run_name = run_name
        self.kind = kind
        self.status = status
        self.config_snapshot = config_snapshot or {}
        self.config_hash = config_hash
        self.code_commit, self.code_branch, self.code_dirty = code_commit, code_branch, code_dirty
        self.requested_start, self.requested_end = requested_start, requested_end
        self.actual_start, self.actual_end = actual_start, actual_end
        self.started_at, self.completed_at, self.heartbeat_at = started_at, completed_at, heartbeat_at
        self.months_planned = months_planned if months_planned is not None else (
            months_between(requested_start, requested_end) if requested_start and requested_end else None)
        self.months_completed = months_completed
        self.bars_processed = bars_processed
        self.starting_capital, self.gross_leverage = starting_capital, gross_leverage
        self.universe_description, self.universe_snapshot = universe_description, universe_snapshot or {}
        self.price_source = price_source
        self.include_dividends, self.include_transaction_costs = include_dividends, include_transaction_costs
        self.assumptions = assumptions or {}
        self.data_snapshot = data_snapshot or {}
        self.results_dir, self.host, self.pid = results_dir, host, pid
        self.strategy_experiment_id = strategy_experiment_id
        self.error = error
        self.created_at = created_at

    # -- lifecycle --------------------------------------------------------------------------------------------
    @property
    def is_finished(self) -> bool:
        return self.status in FINISHED

    def start(self, at: datetime, pid: Optional[int] = None, host: Optional[str] = None) -> None:
        if self.status != PENDING:
            raise ValueError(f"run {self.id} cannot start from {self.status}")
        self.status, self.started_at, self.heartbeat_at = RUNNING, at, at
        self.pid, self.host = pid, host
        self.months_completed = 0

    def record_bar(self, bar_time: datetime, at: Optional[datetime] = None) -> None:
        """One processed engine bar: the actual window and the months covered so far."""
        if self.actual_start is None or bar_time < self.actual_start:
            self.actual_start = bar_time
        if self.actual_end is None or bar_time > self.actual_end:
            self.actual_end = bar_time
        self.bars_processed += 1
        self.months_completed = self.coverage_months()
        if at is not None:
            self.heartbeat_at = at

    def coverage_months(self) -> int:
        """Months of the requested window covered by the processed bars (requested start .. last processed bar),
        capped at months_planned; at the requested end it equals months_planned."""
        if self.actual_end is None:
            return 0
        start = self.requested_start or self.actual_start
        if self.reached_end():
            return int(self.months_planned or months_between(start, self.actual_end))
        done = months_between(start, self.actual_end)
        return min(done, int(self.months_planned)) if self.months_planned is not None else done

    def reached_end(self) -> bool:
        if self.requested_end is None:
            return self.actual_end is not None
        if self.actual_end is None:
            return False
        return (_as_date(self.requested_end) - _as_date(self.actual_end)).days <= END_TOLERANCE_DAYS

    def finish(self, at: datetime, error: Optional[str] = None, cancelled: bool = False) -> str:
        """Final status from what was processed, never from the process exit alone."""
        if self.is_finished:
            raise ValueError(f"run {self.id} is already {self.status}")
        self.completed_at = at
        self.months_completed = self.coverage_months()
        if cancelled:
            self.status = CANCELLED
        elif error is not None:
            self.status = PARTIAL if self.bars_processed and self.months_completed else FAILED
            self.error = error[:4000]
        elif self.reached_end():
            self.status = COMPLETED
        else:
            self.status = PARTIAL if self.bars_processed else FAILED
            self.error = self.error or (f"stopped after {self.months_completed} of {self.months_planned} months: "
                                        f"last bar {self.actual_end}, requested end {self.requested_end}"
                                        if self.bars_processed else "no bar was processed")
        return self.status

    def progress_label(self) -> str:
        return f"{self.months_completed or 0} / {self.months_planned if self.months_planned is not None else '?'} months"

    def to_dict(self) -> Dict[str, Any]:
        keys = ("id", "run_uid", "project_name", "run_name", "kind", "status", "config_hash", "code_commit",
                "code_branch", "code_dirty", "requested_start", "requested_end", "actual_start", "actual_end",
                "started_at", "completed_at", "heartbeat_at", "months_planned", "months_completed", "bars_processed",
                "starting_capital", "gross_leverage", "universe_description", "universe_snapshot", "price_source",
                "include_dividends", "include_transaction_costs", "assumptions", "data_snapshot", "results_dir",
                "host", "pid", "strategy_experiment_id", "error", "created_at")
        out = {k: getattr(self, k) for k in keys}
        for k, v in out.items():
            if isinstance(v, (datetime, date)):
                out[k] = v.isoformat()
        out["progress"] = self.progress_label()
        return out

    def __repr__(self) -> str:
        return f"<BacktestRun(id={self.id}, {self.project_name}, {self.status}, {self.progress_label()})>"
