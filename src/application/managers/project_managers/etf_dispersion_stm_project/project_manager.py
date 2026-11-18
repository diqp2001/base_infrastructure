"""
EtfDispersionSTMProjectManager - launches the Misbuffet engine for the monthly model-filtered ETF dispersion on DIA.

Everything that decides (reads, STM retraining and scoring, option selection, orders) happens inside the engine,
bar by bar, in Algorithm.on_data -> DispersionTradingCycle.step, with every read clipped by the frontier. The
manager launches it and, after the run, writes the A vs B report of the months the cycle traded.

    from src.application.managers.project_managers.etf_dispersion_stm_project.project_manager import (
        EtfDispersionSTMProjectManager,
    )
    EtfDispersionSTMProjectManager().run()          # follow: /dispersion-stm/ (the Flask app)

Command line (file caches of the closes the engine cannot import, then the backtest):
    python -m src.application.managers.project_managers.etf_dispersion_stm_project.project_manager prices
    python -m src.application.managers.project_managers.etf_dispersion_stm_project.project_manager prices-eulerpool
    python -m src.application.managers.project_managers.etf_dispersion_stm_project.project_manager backtest
"""

import logging
import os
import sys
from datetime import date, datetime, timedelta
from typing import Any, Dict, Optional

from src.application.managers.project_managers.etf_dispersion_stm_project import config as project_config
from src.application.managers.project_managers.etf_dispersion_stm_project.backtesting.backtest_runner import (
    BacktestRunner,
)
from src.application.managers.project_managers.etf_dispersion_stm_project.backtesting.base_project_algorithm import (
    TIMINGS_FILE,
)
from src.application.managers.project_managers.etf_dispersion_stm_project.data.dia_universe import build_membership
from src.application.managers.project_managers.etf_dispersion_stm_project.data.price_ingestion import (
    fetch_eulerpool,
    fetch_ibkr,
)
from src.application.managers.project_managers.project_manager import ProjectManager
from src.application.services.dispersion.dispersion_progress import RunStatus
from src.application.services.dispersion.dispersion_report import write_report
from src.application.services.dispersion.realized_payoff import third_fridays
from src.application.services.misbuffet import run_manifest
from src.application.services.timing.step_timings import summarise as summarise_step_timings

DASHBOARD_URL = "http://127.0.0.1:5000/dispersion-stm/"       # progress and results of this project


class EtfDispersionSTMProjectManager(ProjectManager):

    def __init__(self, config: Optional[Dict[str, Any]] = None, database_service=None):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config or project_config.get_config()
        if database_service is None:
            from src.application.services.database_service.database_service import DatabaseService
            database_service = DatabaseService(project_config.CONFIG_TEST['DB_TYPE'])
            database_service.set_ext_db()
        self.setup_database_service(database_service)
        self.results_dir = self.config['results_dir']
        self.runner = BacktestRunner(self.database_service)
        self.results: Dict[str, Any] = {}

    def run(self) -> Dict[str, Any]:
        """Run the Misbuffet backtest; the algorithm trains, scores and trades as time advances."""
        folder = os.path.join(self.results_dir, datetime.now().strftime("%Y%m%dT%H%M%S"))
        settings = project_config.settings(self.config)
        status = RunStatus(self.results_dir, "backtest",
                           on_month=lambda cycle: write_report(cycle.months, folder, settings))
        start, end = project_config.backtest_window(self.config)
        status.update(run_folder=folder, start=start, end=end, months_total=len(third_fridays(start, end)),
                      message="Misbuffet backtest (settle / score / open month by month)")
        self.runner.run_status = status
        print(f"Track this run: {DASHBOARD_URL}   (results: {folder})", flush=True)
        timings_csv = os.path.join(self.results_dir, TIMINGS_FILE)
        if os.path.exists(timings_csv):
            os.remove(timings_csv)
        manifest = run_manifest.build_manifest(
            "backtest", self.config.get('project_name', type(self).__name__), self.config,
            (self.config.get('price_history_start'), self.config['backtest_start'], self.config['backtest_end']))
        run_manifest.write_manifest(self.results_dir, manifest)
        try:
            results = self._run(folder, settings)
        except Exception as e:
            status.update(state="failed", message=f"{type(e).__name__}: {e}"[:500])
            run_manifest.finish_manifest(self.results_dir, manifest, f"failed: {e!r}"[:300], [])
            raise
        finally:
            summary = summarise_step_timings(timings_csv)
            if summary:
                self.logger.info(summary)
        status.update(state="done", message=f"{results['summary']['trades_settled']} trades settled")
        run_manifest.finish_manifest(self.results_dir, manifest, "completed", [])
        return results

    def _run(self, folder: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        engine_result = self.runner.run_backtest(self.config)
        # BaseBacktestRunner reports success even when the engine failed; the engine's own outcome is only in its
        # summary text ("Backtest failed: <error>").
        if isinstance(engine_result, dict):
            text = str(engine_result.get('misbuffet_result') or '')
            if engine_result.get('success') is False:
                raise RuntimeError(f"Misbuffet backtest failed: {engine_result.get('error')}")
            if 'Backtest failed' in text:
                raise RuntimeError(f"Misbuffet engine run failed: {text.split('failed:', 1)[-1].strip()}")
        algorithm = getattr(self.runner, 'algorithm_instance', None)
        cycle = getattr(algorithm, 'cycle', None)
        if cycle is None:
            raise RuntimeError("The engine ran without a dispersion cycle (see the algorithm's initialize log)")
        summary = write_report(cycle.months, folder, settings)
        self.results = {'engine': engine_result, 'summary': summary, 'folder': folder,
                        'value_history': getattr(algorithm, 'value_history', [])}
        return self.results


def main(argv) -> None:
    command = argv[0] if argv else "backtest"
    config = project_config.get_config()
    if command == "backtest":
        EtfDispersionSTMProjectManager(config).run()
        return
    membership = build_membership()
    first = date.fromisoformat(config['price_history_start'])
    last = min(project_config.backtest_window(config)[1] + timedelta(days=config['dispersion']['screen']['max_dte']),
               date.today())
    folder = config['price_history_dir']
    status = RunStatus(config['results_dir'], command)
    try:
        if command == "prices":                     # the ETF (and every member) from IBKR, read-only
            problems = fetch_ibkr([membership.etf] + membership.all_constituents(), first, last,
                                  os.path.join(folder, "ibkr"), progress=status.log)
        elif command == "prices-eulerpool":          # fallback for members IBKR no longer lists
            problems = fetch_eulerpool(membership.all_constituents(), first, last, os.path.join(folder, "eulerpool"))
        else:
            raise SystemExit(f"unknown command {command!r}: prices | prices-eulerpool | backtest")
        status.update(state="done", message=f"symbols without closes: {problems or 'none'}")
    except BaseException as e:
        status.update(state="failed", message=f"{type(e).__name__}: {e}"[:500])
        raise


if __name__ == "__main__":
    main(sys.argv[1:])
