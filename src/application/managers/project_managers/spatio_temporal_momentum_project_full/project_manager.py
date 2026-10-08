"""
SpatioTemporalMomentumFullProjectManager — launches the Misbuffet engine for the
Spatio-Temporal Momentum strategy.

Everything that decides (data access, retraining, scoring, trading) happens
inside the engine, bar by bar, in Algorithm.on_data -> STMTradingCycle.step,
with every read clipped by the MarketDataHistoryService frontier.  The same
code path is used for live trading; the manager only launches it and, after a
backtest, summarises what the engine decided.
"""

import logging
from typing import Any, Dict, Optional

from src.application.managers.project_managers.project_manager import ProjectManager
from src.application.managers.project_managers.spatio_temporal_momentum_project_full import config as project_config
from src.application.managers.project_managers.spatio_temporal_momentum_project_full.backtesting.backtest_runner import (
    BacktestRunner,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_research_report import (
    build_report,
)
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
import pandas as pd


class SpatioTemporalMomentumFullProjectManager(ProjectManager):

    def __init__(self, config: Optional[Dict[str, Any]] = None, database_service=None, progress=None):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config or project_config.get_config()
        self.stm_config = project_config.build_stm_configuration(self.config)
        if database_service is None:
            from src.application.services.database_service.database_service import DatabaseService
            database_service = DatabaseService(project_config.CONFIG_TEST['DB_TYPE'])
            database_service.set_ext_db()
        self.setup_database_service(database_service)
        # Progress and results always go to results_dir, so the Flask /stm dashboard can
        # follow a run started from anywhere (main.py, VS Code, ...).
        self.results_dir = self.config['results_dir']
        if progress is None:
            progress = STMProgressTracker(persist_path=progress_path(self.results_dir))
        elif not progress.persist_path:
            progress.persist_path = progress_path(self.results_dir)
        self.progress = progress
        self.runner = BacktestRunner(self.database_service)
        self.runner.progress_tracker = progress
        self.results: Dict[str, Any] = {}

    def run(self) -> Dict[str, Any]:
        """Run the Misbuffet backtest; the algorithm trains, scores and trades as time advances."""
        bars_total = len(pd.bdate_range(self.config['backtest_start'], self.config['backtest_end']))
        self.progress.start("backtest", bars_total=bars_total)
        try:
            results = self._run()
        except Exception as e:
            self.progress.fail(str(e))
            raise
        if results.get('report') is None:
            self.progress.fail("The run produced no decisions to report (no model eligible during the backtest).")
        else:
            self.progress.phase("Saving results")
            save_report(results['report'], self.results_dir)
            self.progress.complete(results['report'])
        return results

    def _run(self) -> Dict[str, Any]:
        self.progress.phase("Misbuffet backtest (train / score / trade bar by bar)")
        engine_result = self.runner.run_backtest(self.config)
        # BaseBacktestRunner reports success even when the engine failed; the engine's own
        # outcome is only in its summary text ("❌ Backtest failed: <error>").
        if isinstance(engine_result, dict):
            summary = str(engine_result.get('misbuffet_result') or '')
            if engine_result.get('success') is False:
                raise RuntimeError(f"Misbuffet backtest failed: {engine_result.get('error')}")
            if 'Backtest failed' in summary:
                raise RuntimeError(f"Misbuffet engine run failed: {summary.split('failed:', 1)[-1].strip()}")
        algorithm = getattr(self.runner, 'algorithm_instance', None)
        cycle_results = getattr(algorithm, 'cycle_results', []) if algorithm else []
        self.progress.phase("Building research report (tables, figures, SHAP)")
        report = self.report(cycle_results, algorithm)
        self.results = {
            'engine': engine_result,
            'sessions': len(cycle_results),
            'retrainings': [(str(r.session.date()), r.artifact_id) for r in cycle_results if r.retrained],
            'report': report,
        }
        return self.results

    def report(self, cycle_results, algorithm):
        """Post-run research report (paper tables and figures) of the engine's decisions."""
        if not cycle_results or algorithm is None or algorithm.cycle is None:
            return None
        cycle = algorithm.cycle
        reader = STMPriceHistoryReader(cycle.factory)          # after the run: evaluation only
        id_to_ticker = {eid: t for t, eid in cycle.ticker_to_entity.items()}
        closes = reader.load_close_panel(id_to_ticker, start=cycle.history_start)
        return build_report(cycle_results, closes, self.stm_config, factory=cycle.factory)
