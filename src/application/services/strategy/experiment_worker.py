"""
Worker process of one strategy experiment:  python -m src.application.services.strategy.experiment_worker <id>

1. load the experiment and its LOCKED configuration; check the configuration did not change since launch (hash)
2. mark it RUNNING (pid, host), beat every 30 s from a thread with its OWN database session
3. translate the configuration into the project's native config, with the experiment's own results folder and
   portfolio name, and run the project's own manager (its cycle, model and portfolio rule, unchanged)
4. record what the run used and produced: model artifacts, universe membership, data coverage, headline metrics
5. SUCCEEDED, or FAILED with the error; the monitoring dashboard sees it through the existing JobRecorder

``run_experiment`` takes its collaborators as arguments so tests run it in-process on SQLite with a fake project.
"""

from __future__ import annotations

import logging
import os
import socket
import sys
import threading
import traceback
from datetime import datetime
from typing import Any, Callable, Dict, Optional

from src.domain.entities.strategy.strategy_experiment import StrategyExperiment

HEARTBEAT_SECONDS = 30
logger = logging.getLogger(__name__)


def portfolio_name(base: str, experiment_id: int) -> str:
    """Each experiment books into its own portfolio: experiments never share (or reset) each other's book."""
    return f"{base}_exp{experiment_id}"


def summarise(report) -> Dict[str, Any]:
    """Headline numbers of a project report (CSM: table_performance, STM: table_raw): the model's row."""
    if report is None:
        return {}
    out: Dict[str, Any] = {"model": getattr(report, "model_name", None),
                           "period": list(getattr(report, "period", ()) or ()),
                           "decisions": getattr(report, "n_sessions", None)}
    table = getattr(report, "table_performance", None)
    if table is None:
        table = getattr(report, "table_raw", None)
    if table is not None and len(table):
        row = table.loc[out["model"]] if out["model"] in table.index else table.iloc[0]
        out["metrics"] = {str(k): (None if v != v else float(v)) for k, v in row.items()
                          if isinstance(v, (int, float))}
        out["benchmarks"] = {str(name): {"Sharpe": float(r["Sharpe"]) if "Sharpe" in r and r["Sharpe"] == r["Sharpe"]
                                         else None} for name, r in table.iterrows() if name != out["model"]}
    cov = getattr(report, "coverage_summary", None)
    if cov is not None and "Value" in cov:
        out["coverage"] = {str(k): (float(v) if isinstance(v, (int, float)) else str(v))
                           for k, v in cov["Value"].items()}
    return out


def provenance_of(manager, results: Dict[str, Any], native_config: Dict[str, Any]) -> Dict[str, Any]:
    """What the run used: model artifacts, universe membership per decision, preload coverage, native config."""
    algorithm = getattr(getattr(manager, "runner", None), "algorithm_instance", None)
    cycle = getattr(algorithm, "cycle", None)
    cycle_results = list(getattr(algorithm, "cycle_results", []) or [])
    eligible = {}
    for r in cycle_results:
        session = getattr(r, "session", None)
        if session is not None and getattr(r, "eligible", None):
            eligible[str(session)] = list(r.eligible)
    universe = {}
    if cycle is not None:
        universe = {"tickers": list(getattr(cycle, "ticker_to_entity", {}) or {}),
                    "entity_ids": {t: int(e) for t, e in (getattr(cycle, "ticker_to_entity", {}) or {}).items()},
                    "universe_id": getattr(cycle, "universe_id", None)}
    preload = os.path.join(native_config.get("results_dir", ""), "preload.csv")
    return {
        "artifacts": sorted({int(r.artifact_id) for r in cycle_results if getattr(r, "artifact_id", None) is not None}),
        "retrainings": [[str(s), a] for s, a in results.get("retrainings", [])],
        "universe": universe,
        "eligible_per_decision": eligible,
        "preload_report": preload if os.path.exists(preload) else None,
        "native_config": {k: v for k, v in native_config.items() if isinstance(v, (str, int, float, bool))},
    }


class _Heartbeat(threading.Thread):

    def __init__(self, beat: Callable[[], None], seconds: float = HEARTBEAT_SECONDS):
        super().__init__(daemon=True)
        self.beat, self.seconds, self.stop_event = beat, seconds, threading.Event()

    def run(self):
        while not self.stop_event.wait(self.seconds):
            try:
                self.beat()
            except Exception as e:                       # a missed beat never stops the run
                logger.warning(f"heartbeat failed: {e}")


def run_experiment(experiment_id: int, experiments, configurations, beat_repository_factory: Optional[Callable] = None,
                   database_service=None, clock: Callable[[], datetime] = datetime.utcnow,
                   pid: Optional[int] = None, host: Optional[str] = None,
                   manager_factory: Optional[Callable] = None) -> StrategyExperiment:
    """``experiments`` / ``configurations``: repositories. ``manager_factory(adapter, native_config,
    database_service)`` builds the project manager (default: the adapter's manager class)."""
    from src.application.services.strategy.configuration_service import StrategyConfigurationService

    experiment = experiments.get_by_id(experiment_id)
    if experiment is None:
        raise LookupError(f"experiment {experiment_id} does not exist")
    service = StrategyConfigurationService(configurations)
    configuration = service.get(experiment.configuration_id)
    experiment.start(pid or os.getpid(), host or socket.gethostname(), clock())
    experiment = experiments.update(experiment)
    heartbeat = None
    if beat_repository_factory is not None:
        beat_repo = beat_repository_factory()

        def beat():
            e = beat_repo.get_by_id(experiment_id)
            if e is not None and not e.is_finished:
                e.beat(clock())
                beat_repo.update(e)
        heartbeat = _Heartbeat(beat)
        heartbeat.start()
    recorder = None
    try:
        from src.application.services.monitoring.job_tracker import JobRecorder
        recorder = JobRecorder("strategy_experiment", f"{configuration.name} v{configuration.version}",
                               details={"experiment_id": experiment_id, "project": configuration.project_key}).start()
    except Exception:
        recorder = None
    try:
        if configuration.status != "locked" or configuration.content_hash != experiment.configuration_hash:
            raise RuntimeError("the configuration changed after the experiment was launched")
        adapter = service.registry.get(configuration.project_key)
        base = adapter.base_config()["Portfolio"]["name"]
        native = service.native_config(configuration, results_dir=experiment.results_dir,
                                       portfolio_name=portfolio_name(base, experiment_id))
        if manager_factory is None:
            manager = adapter.manager_class()(config=native, database_service=database_service)
        else:
            manager = manager_factory(adapter, native, database_service)
        results = manager.run()
        report = results.get("report") if isinstance(results, dict) else None
        if report is None:
            raise RuntimeError("the run produced no report (no model was trained during the backtest)")
        experiment = experiments.get_by_id(experiment_id)
        experiment.succeed(clock(), summary=summarise(report), provenance=provenance_of(manager, results, native))
        if recorder is not None:
            recorder.finish(True)
    except BaseException as e:                           # KeyboardInterrupt too: never leave it RUNNING
        experiment = experiments.get_by_id(experiment_id)
        if not experiment.is_finished:
            experiment.fail(clock(), f"{type(e).__name__}: {e}\n{traceback.format_exc()[-4000:]}")
        if recorder is not None:
            try:
                recorder.finish(False, error=str(e))
            except Exception:
                pass
        if not isinstance(e, Exception):
            experiments.update(experiment)
            raise
    finally:
        if heartbeat is not None:
            heartbeat.stop_event.set()
    return experiments.update(experiment)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 1 or not argv[0].isdigit():
        print("usage: python -m src.application.services.strategy.experiment_worker <experiment id>")
        return 2
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    from src.application.services.strategy.strategy_services import StrategyServices
    services = StrategyServices.from_database()
    result = run_experiment(int(argv[0]), services.experiment_repository, services.configuration_repository,
                            beat_repository_factory=services.new_experiment_repository,
                            database_service=services.database_service)
    print(f"experiment {result.id}: {result.status}" + (f" — {result.error.splitlines()[0]}" if result.error else ""))
    return 0 if result.status == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
