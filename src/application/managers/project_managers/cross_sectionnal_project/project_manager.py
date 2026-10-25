"""
CrossSectionalMomentumProjectManager — launches the Misbuffet engine for the cross-sectional momentum classifier
(LightGBM, features and hyper-parameters by Optuna TPE).

Everything that decides (data access, Optuna study, retraining, scoring, trading) happens inside the engine, bar
by bar, in Algorithm.on_data -> CSMTradingCycle.step, with every read clipped by the MarketDataHistoryService
frontier. The same code path is used for live trading; the manager only launches it and, after a backtest, builds
the results report (performance, prediction quality, feature importance, Optuna, data coverage) for the Flask
/csm dashboard and its PDF.
"""

import logging
from typing import Any, Dict, Optional

import pandas as pd

from src.application.managers.project_managers.cross_sectionnal_project import config as project_config
from src.application.managers.project_managers.cross_sectionnal_project.backtesting.backtest_runner import (
    BacktestRunner,
)
from src.application.managers.project_managers.project_manager import ProjectManager
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_report import build_report
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_report_renderer import build_pdf
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_price_history import (
    STMPriceHistoryReader,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_progress import (
    STMProgressTracker,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_report_store import (
    progress_path,
    save_report,
)

OPTUNA_LOG_PREFIXES = ("[CSM] Optuna",)


DASHBOARD_URL = "http://127.0.0.1:5000/csm/"           # progress, results and PDF of this project

class CrossSectionalMomentumProjectManager(ProjectManager):

    def __init__(self, config: Optional[Dict[str, Any]] = None, database_service=None, progress=None):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config or project_config.get_config()
        self.csm_config = project_config.build_csm_configuration(self.config)
        if database_service is None:
            from src.application.services.database_service.database_service import DatabaseService
            database_service = DatabaseService(project_config.CONFIG_TEST['DB_TYPE'])
            database_service.set_ext_db()
        self.setup_database_service(database_service)
        self.results_dir = self.config['results_dir']
        if progress is None:
            progress = STMProgressTracker(persist_path=progress_path(self.results_dir),
                                          last_step_prefixes=OPTUNA_LOG_PREFIXES)
        elif not progress.persist_path:
            progress.persist_path = progress_path(self.results_dir)
        self.progress = progress
        self.runner = BacktestRunner(self.database_service)
        self.runner.progress_tracker = progress
        self.results: Dict[str, Any] = {}

    def run(self) -> Dict[str, Any]:
        """Run the Misbuffet backtest; the algorithm optimises, trains, scores and trades as time advances."""
        bars_total = len(pd.bdate_range(pd.Timestamp(self.config['backtest_start']).normalize(),
                                        pd.Timestamp(self.config['backtest_end']).normalize()))
        self.progress.start("backtest", bars_total=bars_total)
        # where to follow the run (the Flask app must be running: python -m src.interfaces.flask.app)
        print(f"Track this run: {DASHBOARD_URL}   (results: {self.results_dir})", flush=True)
        self.progress.log(f"[run] dashboard: {DASHBOARD_URL}")
        try:
            results = self._run()
        except Exception as e:
            self.progress.fail(str(e))
            raise
        if results.get('report') is None:
            self.progress.fail("The run produced no decisions to report (no model trained during the backtest).")
        else:
            self.progress.phase("Saving results")
            save_report(results['report'], self.results_dir, pdf_builder=build_pdf)
            self.progress.complete(results['report'])
        return results

    def _run(self) -> Dict[str, Any]:
        self.progress.phase("Misbuffet backtest (Optuna TPE / train / score / trade bar by bar)")
        engine_result = self.runner.run_backtest(self.config)
        if isinstance(engine_result, dict):
            summary = str(engine_result.get('misbuffet_result') or '')
            if engine_result.get('success') is False:
                raise RuntimeError(f"Misbuffet backtest failed: {engine_result.get('error')}")
            if 'Backtest failed' in summary:
                raise RuntimeError(f"Misbuffet engine run failed: {summary.split('failed:', 1)[-1].strip()}")
        algorithm = getattr(self.runner, 'algorithm_instance', None)
        cycle_results = getattr(algorithm, 'cycle_results', []) if algorithm else []
        self.progress.phase("Building results report (performance, feature importance, data coverage)")
        report = self.report(cycle_results, algorithm)
        self.results = {
            'engine': engine_result,
            'sessions': len(cycle_results),
            'retrainings': [(str(r.session.date()), r.artifact_id) for r in cycle_results if r.retrained],
            'report': report,
        }
        return self.results

    def report(self, cycle_results, algorithm):
        """Post-run results report of the engine's decisions."""
        if not cycle_results or algorithm is None or algorithm.cycle is None:
            return None
        cycle = algorithm.cycle
        reader = STMPriceHistoryReader(cycle.factory)            # after the run: evaluation only
        id_to_ticker = {eid: t for t, eid in cycle.ticker_to_entity.items()}
        closes = reader.load_close_panel(id_to_ticker, start=cycle.history_start)
        artifacts = run_artifacts(cycle, cycle_results)
        return build_report(cycle_results, closes, self.csm_config, artifacts, history_start=cycle.history_start,
                            feature_engine=cycle.feature_engine)


def run_artifacts(cycle, cycle_results) -> Dict[int, Dict[str, Any]]:
    """{artifact id: metadata} of the models that scored a decision of the run."""
    used = {r.artifact_id for r in cycle_results if getattr(r, "artifact_id", None) is not None}
    return {a.id: m for a, m in cycle.artifact_store.list_artifacts() if a.id in used}
