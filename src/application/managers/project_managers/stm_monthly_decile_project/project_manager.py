"""
STMMonthlyDecileProjectManager - launches the Misbuffet engine for the monthly cross-sectional decile strategy of
the spatio-temporal momentum model on the Dow members.

Everything that decides (reads, monthly retraining, scoring, deciles, orders) happens inside the engine, bar by bar,
in Algorithm.on_data -> STMDecileTradingCycle.step, with every read clipped by the frontier. The manager launches it
and, after the run (and after every month, for the progress), writes the decile report (decile_report).

    from src.application.managers.project_managers.stm_monthly_decile_project.project_manager import (
        STMMonthlyDecileProjectManager,
    )
    STMMonthlyDecileProjectManager().run()
"""

import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, Optional

from src.application.managers.project_managers.project_manager import ProjectManager
from src.application.managers.project_managers.stm_monthly_decile_project import config as project_config
from src.application.managers.project_managers.stm_monthly_decile_project.backtesting.backtest_runner import (
    BacktestRunner,
)
from src.application.managers.project_managers.stm_monthly_decile_project.backtesting.base_project_algorithm import (
    TIMINGS_FILE,
)
from src.application.services.misbuffet import run_manifest
from src.application.services.portfolio_research.decile_report import decile_status, write_report
from src.application.services.timing.step_timings import summarise as summarise_step_timings


class STMMonthlyDecileProjectManager(ProjectManager):

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
        """Run the Misbuffet backtest; the algorithm retrains, scores, forms the deciles and trades D10 - D1."""
        folder = os.path.join(self.results_dir, datetime.now().strftime("%Y%m%dT%H%M%S"))
        settings = project_config.settings(self.config)
        status = decile_status(self.results_dir, "backtest", on_month=lambda cycle: write_report(cycle, folder, settings))
        start, end = project_config.backtest_window(self.config)
        months_total = (end.year - start.year) * 12 + end.month - start.month   # rebalances: one per month after the first
        status.update(run_folder=folder, start=str(start), end=str(end), months_total=months_total,
                      variants=project_config.variants(self.config),
                      message="Misbuffet backtest (monthly deciles)")
        self.runner.run_status = status
        print(f"Results: {folder}  (progress: {os.path.join(self.results_dir, 'status.json')})", flush=True)
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
        status.update(state="done", message=f"report in {folder}")
        run_manifest.finish_manifest(self.results_dir, manifest, "completed", [])
        return results

    def _run(self, folder: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        engine_result = self.runner.run_backtest(self.config)
        if isinstance(engine_result, dict):
            text = str(engine_result.get('misbuffet_result') or '')
            if engine_result.get('success') is False:
                raise RuntimeError(f"Misbuffet backtest failed: {engine_result.get('error')}")
            if 'Backtest failed' in text:
                raise RuntimeError(f"Misbuffet engine run failed: {text.split('failed:', 1)[-1].strip()}")
        algorithm = getattr(self.runner, 'algorithm_instance', None)
        cycle = getattr(algorithm, 'cycle', None)
        if cycle is None:
            raise RuntimeError("The engine ran without a decile cycle (see the algorithm's initialize log)")
        summary = write_report(cycle, folder, settings)
        self.results = {'engine': engine_result, 'summary': summary, 'folder': folder,
                        'value_history': getattr(algorithm, 'value_history', [])}
        return self.results


if __name__ == "__main__":
    STMMonthlyDecileProjectManager().run()
    sys.exit(0)
