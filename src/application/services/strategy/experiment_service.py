"""
ExperimentService — launching, following and recovering strategy experiments (backtests of locked strategies).

launch   locks the strategy (it never changes again), records a QUEUED experiment with its own results
         folder and portfolio name, then starts a separate worker process (JobRunner). The web request returns
         at once; the worker marks the experiment RUNNING, beats every 30 s, and ends it SUCCEEDED or FAILED.
recover  an experiment marked RUNNING / QUEUED whose worker process is gone (crash, reboot, killed) becomes
         INTERRUPTED. Called before every launch and when the experiment list is shown.

One experiment runs at a time: every project uses the same IBKR client id and the same TWS session.
Only backtests can be launched; paper / live trading are not available from this interface.
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, List, Optional

from src.application.services.backtest_registry.run_identity import pid_alive  # noqa: F401  (re-exported)
from src.application.services.strategy.strategy_service import StrategyService
from src.domain.entities.strategy.strategy_experiment import (
    BACKTEST,
    FAILED,
    INTERRUPTED,
    QUEUED,
    RUNNING,
    StrategyExperiment,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_RESULTS_ROOT = REPO_ROOT / "results" / "strategy_experiments"
STARTUP_GRACE = timedelta(minutes=5)          # a QUEUED experiment whose worker never reported in


class ExperimentConflict(Exception):
    """Another experiment is running."""


class JobRunner:
    """Starts ``python -m src.application.services.strategy.experiment_worker <id>`` as a detached process whose
    output goes to the experiment's log."""

    def __init__(self, python: str = sys.executable, cwd: Path = REPO_ROOT):
        self.python = python
        self.cwd = cwd

    def command(self, experiment: StrategyExperiment) -> List[str]:
        return [self.python, "-m", "src.application.services.strategy.experiment_worker", str(experiment.id)]

    def start(self, experiment: StrategyExperiment) -> int:
        os.makedirs(os.path.dirname(experiment.log_path), exist_ok=True)
        log = open(experiment.log_path, "ab")
        flags = 0
        if os.name == "nt":                       # survives the web server; no console window
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        process = subprocess.Popen(self.command(experiment), cwd=str(self.cwd), stdout=log, stderr=subprocess.STDOUT,
                                   stdin=subprocess.DEVNULL, creationflags=flags, close_fds=True)
        log.close()
        return process.pid


class ExperimentService:

    def __init__(self, repository, configurations: StrategyService, runner: Optional[JobRunner] = None,
                 results_root: Path = DEFAULT_RESULTS_ROOT, clock: Callable[[], datetime] = datetime.utcnow,
                 is_alive: Callable[[Optional[int]], bool] = pid_alive, host: Optional[str] = None,
                 artifact_repository=None):
        self.repository = repository
        self.artifact_repository = artifact_repository
        self.configurations = configurations
        self.runner = runner or JobRunner()
        self.results_root = Path(results_root)
        self.clock = clock
        self.is_alive = is_alive
        self.host = host or socket.gethostname()

    # -- reads --------------------------------------------------------------------------------------------------
    def get(self, experiment_id: int) -> StrategyExperiment:
        experiment = self.repository.get_by_id(experiment_id)
        if experiment is None:
            raise LookupError(f"experiment {experiment_id} does not exist")
        return experiment

    def list(self, configuration_id: Optional[int] = None) -> List[StrategyExperiment]:
        self.recover()
        if configuration_id is not None:
            return self.repository.get_by_strategy(configuration_id)
        return self.repository.get_all()

    def active(self) -> List[StrategyExperiment]:
        return self.repository.get_by_status(QUEUED) + self.repository.get_by_status(RUNNING)

    def log_tail(self, experiment_id: int, lines: int = 200) -> str:
        path = self.get(experiment_id).log_path
        if not path or not os.path.exists(path):
            return ""
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 200_000))
            text = f.read().decode("utf-8", errors="replace")
        return "\n".join(text.splitlines()[-lines:])

    def report(self, experiment_id: int):
        """(experiment, stored report or None, renderer module) — the project's own report of the run."""
        from src.application.services.data.entities.factor.spatio_temporal_momentum import stm_report_store as store
        experiment = self.get(experiment_id)
        renderer = self.configurations.registry.get(experiment.strategy_type).renderer()
        report = None
        if experiment.results_dir and store.report_mtime(experiment.results_dir) is not None:
            report = store.load_report(experiment.results_dir)
        return experiment, report, renderer

    def artifacts(self, experiment_id: int) -> List[dict]:
        """The model artifacts the run used: file, training window, CV score, features, parameters."""
        import json
        experiment = self.get(experiment_id)
        out = []
        for artifact_id in experiment.provenance.get("artifacts", []):
            artifact = self.artifact_repository.get_by_id(int(artifact_id)) if self.artifact_repository else None
            if artifact is None:
                out.append({"id": artifact_id, "missing": True})
                continue
            meta = artifact.artifact_metadata
            if isinstance(meta, str):
                try:
                    meta = json.loads(meta)
                except ValueError:
                    meta = {}
            out.append({"id": artifact.id, "name": artifact.name, "location": artifact.location,
                        "file_present": bool(artifact.location and os.path.exists(artifact.location)),
                        "created_at": artifact.created_at, "metadata": meta or {}})
        return out

    def compare(self, experiment_ids: List[int]) -> dict:
        """Side by side: configuration, assumptions, metrics of the backtests. Experiments that differ in project,
        period, universe or capital are flagged: their numbers are not directly comparable."""
        rows, warnings = [], []
        for experiment_id in experiment_ids:
            e = self.get(experiment_id)
            c = self.configurations.get(e.strategy_id)
            ev, universe = c.section("evaluation"), c.section("universe")
            from src.application.services.strategy.backtest_window import window_of
            window = window_of(e)                       # the backtest's own window (older ones: the strategy's)
            period = window.label() if window else f"{ev.get('backtest_start')} .. {ev.get('backtest_end')}"
            capital = window.initial_capital if window else ev.get("initial_capital")
            rows.append({
                "experiment": e.id, "status": e.status, "configuration": f"{c.name} v{c.version}",
                "project": c.strategy_type, "period": period,
                "universe": universe.get("name") or universe.get("instruments"), "capital": capital,
                "decisions": e.summary.get("decisions"), "metrics": e.summary.get("metrics", {}),
                "benchmarks": e.summary.get("benchmarks", {}), "sections": c.sections,
            })
        done = [r for r in rows if r["status"] == "succeeded"]
        for r in rows:
            if r["status"] != "succeeded":
                warnings.append(f"experiment {r['experiment']} is {r['status']}: no results to compare")
        for key, label in (("project", "project implementations"), ("period", "backtest periods"),
                           ("universe", "universes"), ("capital", "initial capital")):
            if len({str(r[key]) for r in done}) > 1:
                warnings.append(f"different {label}: the metrics are not directly comparable")
        differences = []
        if len(done) > 1:
            for section in sorted({s for r in done for s in r["sections"]}):
                for field in sorted({f for r in done for f in r["sections"].get(section, {})}):
                    values = [r["sections"].get(section, {}).get(field) for r in done]
                    if len({repr(v) for v in values}) > 1:
                        differences.append({"section": section, "field": field, "by_experiment": values})
        metrics = sorted({m for r in done for m in r["metrics"]})
        return {"rows": rows, "metrics": metrics, "differences": differences, "warnings": warnings,
                "note": "Backtests: out-of-sample decisions of the walk-forward run, not paper or live results. "
                        "Do not rank on a single Sharpe ratio."}

    # -- writes -------------------------------------------------------------------------------------------------
    def recover(self) -> List[StrategyExperiment]:
        """Experiments whose worker is gone become INTERRUPTED (only workers started on this host are checked)."""
        now = self.clock()
        interrupted = []
        for e in self.active():
            if e.host and e.host != self.host:
                continue                                       # another machine's worker: cannot check its pid
            if e.status == RUNNING and not self.is_alive(e.pid):
                e.interrupt(now, f"worker process {e.pid} is no longer running (crash, reboot or killed)")
            elif e.status == QUEUED and not self.is_alive(e.pid) and e.created_at and now - e.created_at > STARTUP_GRACE:
                e.interrupt(now, "the worker never started")
            else:
                continue
            interrupted.append(self.repository.update(e))
        return interrupted

    def default_window(self, configuration_id: int):
        """The strategy's own dates and capital (the launch form's default); None when its config cannot be built."""
        from src.application.services.strategy.backtest_window import default_window
        try:
            return default_window(self.configurations.native_config(self.configurations.get(configuration_id)))
        except Exception:
            return None

    def _check_window(self, strategy, window) -> None:
        """A project with a form checks its history needs on the window (price history before the start)."""
        from src.application.services.strategy.backtest_window import history_start
        adapter = self.configurations.registry.get(strategy.strategy_type)
        sections = strategy.sections
        if hasattr(adapter, "native_config_for") or "evaluation" not in sections:
            return
        native = self.configurations.native_config(strategy)
        sections["evaluation"] = {**sections["evaluation"],
                                  "backtest_start": f"{window.start} {str(native['backtest_start'])[11:19] or '16:00:00'}",
                                  "backtest_end": f"{window.end} {str(native['backtest_end'])[11:19] or '16:00:00'}",
                                  "price_history_start": history_start(native, window),
                                  "initial_capital": float(window.initial_capital)}
        _, issues = adapter.validate(sections)
        errors = [i for i in issues if i.severity == "error"]
        if errors:
            from src.application.services.strategy.strategy_service import ConfigurationInvalid
            raise ConfigurationInvalid(errors)

    def retry(self, experiment_id: int) -> StrategyExperiment:
        """A failed or interrupted experiment run again: a NEW experiment of the same strategy over the same window
        and starting capital (the failed one is kept as it is, with its log)."""
        from src.application.services.strategy.backtest_window import window_of
        previous = self.get(experiment_id)
        if previous.status not in (FAILED, INTERRUPTED):
            raise ValueError(f"experiment {experiment_id} is {previous.status}: only a failed or interrupted "
                             f"experiment can be retried")
        experiment = self.launch(previous.strategy_id, kind=previous.kind, window=window_of(previous))
        experiment.provenance = {**(experiment.provenance or {}), "retry_of": previous.id}
        return self.repository.update(experiment)

    def launch(self, configuration_id: int, kind: str = BACKTEST, window=None) -> StrategyExperiment:
        """A backtest of the strategy over ``window`` (BacktestWindow: start, end, starting capital; default: the
        strategy's own dates). A strategy can be backtested over many windows."""
        if kind != BACKTEST:
            raise ValueError(f"only backtests can be launched from the strategy interface (not '{kind}')")
        strategy = self.configurations.get(configuration_id)
        adapter = self.configurations.registry.get(strategy.strategy_type)
        if getattr(adapter, "launchable", True) is False:
            raise ValueError(f"project {strategy.strategy_type} cannot be launched as a backtest from this interface "
                             f"(live trading / not a backtest project)")
        self.recover()
        running = self.active()
        if running:
            raise ExperimentConflict(f"experiment {running[0].id} is {running[0].status}: one run at a time "
                                     f"(shared IBKR client)")
        configuration = self.configurations.lock(configuration_id)          # validates; raises when invalid
        window = window or self.default_window(configuration_id)
        if window is None:
            raise ValueError("no backtest window: give a start, an end and a starting capital")
        self._check_window(configuration, window)
        from src.application.services.strategy.backtest_window import as_datetime
        experiment = self.repository.add(StrategyExperiment(
            strategy_id=configuration.id, strategy_hash=configuration.content_hash,
            strategy_type=configuration.strategy_type, kind=kind, status=QUEUED, created_at=self.clock(), host=self.host,
            backtest_start=as_datetime(window.start), backtest_end=as_datetime(window.end),
            initial_capital=float(window.initial_capital),
            provenance={"configuration": {"name": configuration.name, "version": configuration.version},
                        "window": {"start": str(window.start), "end": str(window.end),
                                   "initial_capital": float(window.initial_capital)}}))
        folder = self.results_root / f"experiment_{experiment.id}"
        experiment.results_dir = str(folder)
        experiment.log_path = str(folder / "worker.log")
        experiment = self.repository.update(experiment)
        try:
            experiment.pid = self.runner.start(experiment)
        except Exception as e:
            experiment.fail(self.clock(), f"could not start the worker: {e}")
            return self.repository.update(experiment)
        return self.repository.update(experiment)
