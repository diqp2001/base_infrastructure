"""
MarketMakingSPXCallSpreadV2ProjectManager — launches the Misbuffet engine for
the SPX call spread market maker (structure of the Spatio-Temporal Momentum
project managers).

Everything that decides (factor refresh, option entry, greeks, delta hedge)
happens inside the engine, bar by bar, in Algorithm.on_data ->
SPXCallSpreadTradingCycle.step.  The manager only launches the run, follows it
(``progress.json``) and, at the end, writes a summary (``results.json``) of what
the engine did, both in ``config['results_dir']``.
"""

import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, Optional

import pandas as pd

from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2 import config as project_config
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.backtesting.backtest_runner import (
    BacktestRunner,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.utils.progress import (
    MMProgressTracker,
)
from src.application.managers.project_managers.project_manager import ProjectManager

PROGRESS_FILE = "progress.json"
RESULTS_FILE = "results.json"


def expected_bars(config: Dict[str, Any]) -> int:
    """Approximate number of engine bars between backtest_start and backtest_end."""
    start, end = pd.Timestamp(config['backtest_start']), pd.Timestamp(config['backtest_end'])
    interval = config.get('config_interval') or {}
    if interval.get('custom_interval_minutes'):
        per_day = max(1, int(390 // interval['custom_interval_minutes']))
        return len(pd.bdate_range(start.normalize(), end.normalize())) * per_day
    days = interval.get('custom_interval_days', 1) or 1
    return max(1, len(pd.bdate_range(start.normalize(), end.normalize())) // int(days))


class MarketMakingSPXCallSpreadV2ProjectManager(ProjectManager):

    def __init__(self, config: Optional[Dict[str, Any]] = None, database_service=None,
                 progress: Optional[MMProgressTracker] = None):
        super().__init__()
        self.logger = logging.getLogger(self.__class__.__name__)
        self.config = config or project_config.get_config()
        if database_service is None:
            from src.application.services.database_service.database_service import DatabaseService
            database_service = DatabaseService(project_config.CONFIG_TEST['DB_TYPE'])
            database_service.set_ext_db()
        self.setup_database_service(database_service)
        self.results_dir = self.config['results_dir']
        if progress is None:
            progress = MMProgressTracker(persist_path=os.path.join(self.results_dir, PROGRESS_FILE))
        elif not progress.persist_path:
            progress.persist_path = os.path.join(self.results_dir, PROGRESS_FILE)
        self.progress = progress
        self.runner = BacktestRunner(self.database_service)
        self.runner.progress_tracker = progress
        self.results: Dict[str, Any] = {}

    def run(self) -> Dict[str, Any]:
        """Run the Misbuffet backtest; the algorithm refreshes factors, enters and hedges bar by bar."""
        self.progress.start("backtest", bars_total=expected_bars(self.config))
        mlflow_run = self._start_mlflow()
        try:
            results = self._run()
        except Exception as e:
            self.write_data_report()                     # what was missing up to the failure
            self.progress.fail(str(e))
            self._end_mlflow(mlflow_run, error=str(e))
            raise
        self.progress.phase("Saving results")
        results['summary']['data_report'] = self.write_data_report()
        self.save_results(results['summary'])
        self.progress.complete(results['summary'])
        self._end_mlflow(mlflow_run, summary=results['summary'])
        return results

    def _run(self) -> Dict[str, Any]:
        self.progress.phase("Misbuffet backtest (factors / entry / greeks / hedge bar by bar)")
        engine_result = self.runner.run_backtest(self.config)
        # BaseBacktestRunner reports success even when the engine failed; the engine's own
        # outcome is only in its summary text ("❌ Backtest failed: <error>").
        if isinstance(engine_result, dict):
            text = str(engine_result.get('misbuffet_result') or '')
            if engine_result.get('success') is False:
                raise RuntimeError(f"Misbuffet backtest failed: {engine_result.get('error')}")
            if 'Backtest failed' in text:
                raise RuntimeError(f"Misbuffet engine run failed: {text.split('failed:', 1)[-1].strip()}")
        algorithm = getattr(self.runner, 'algorithm_instance', None)
        if algorithm is not None and algorithm.cycle is None:
            raise RuntimeError("The SPX v2 trading cycle was not built (see the log for the cause).")
        cycle_results = list(getattr(algorithm, 'cycle_results', []) or [])
        self.results = {
            'engine': engine_result,
            'cycle_results': cycle_results,
            'summary': self.summarize(cycle_results, algorithm, engine_result),
        }
        return self.results

    def summarize(self, cycle_results, algorithm, engine_result) -> Dict[str, Any]:
        """JSON summary of what the engine decided during the run."""
        values = getattr(algorithm, 'value_history', []) if algorithm is not None else []
        return {
            'project': self.config['project_name'],
            'period': [str(self.config['backtest_start']), str(self.config['backtest_end'])],
            'bars': len(cycle_results),
            'option_entries': sum(r.option_order is not None for r in cycle_results),
            'hedges': sum(r.hedge_order is not None for r in cycle_results),
            'step_errors': [r.summary() for r in cycle_results if r.error][:50],
            'final_portfolio_value': getattr(algorithm, 'portfolio_value', None),
            'portfolio_values': [{'time': str(t), 'value': v} for t, v in values],
            'steps': [r.summary() for r in cycle_results],
            'execution_time_s': (engine_result or {}).get('execution_time') if isinstance(engine_result, dict) else None,
            'saved_at': datetime.now().isoformat(timespec="seconds"),
        }

    def data_report(self):
        """The run's DataReport (built with the trading cycle), or None before the cycle exists."""
        algorithm = getattr(self.runner, 'algorithm_instance', None)
        cycle = getattr(algorithm, 'cycle', None)
        return getattr(getattr(cycle, 'position_book', None), 'report', None)

    def write_data_report(self) -> Optional[str]:
        """Write ``data_report.txt`` (missing data and why) to results_dir; returns its path."""
        report = self.data_report()
        if report is None:
            return None
        algorithm = getattr(self.runner, 'algorithm_instance', None)
        report.bars = len(getattr(algorithm, 'cycle_results', []) or [])
        try:
            return report.write(self.results_dir)
        except Exception as e:
            logging.getLogger(__name__).error(f"Could not write the data report: {e}")
            return None

    def save_results(self, summary: Dict[str, Any]) -> str:
        os.makedirs(self.results_dir, exist_ok=True)
        path = os.path.join(self.results_dir, RESULTS_FILE)
        tmp = f"{path}.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(summary, f, default=str, indent=1)
        os.replace(tmp, path)
        return path

    # ------------------------------------------------------------------ MLflow (as the original project)
    def _start_mlflow(self):
        try:
            import mlflow
            mlflow.set_tracking_uri(f"file:{self.config.get('mlflow_tracking_uri', './mlruns')}")
            mlflow.set_experiment(self.config['mlflow_experiment_name'])
            run = mlflow.start_run()
            mlflow.log_params({
                'initial_capital': self.config.get('initial_capital'),
                'backtest_start': self.config.get('backtest_start'),
                'backtest_end': self.config.get('backtest_end'),
                'bar_size_setting': self.config.get('bar_size_setting'),
                'option_entry_weight': self.config.get('option_entry_weight'),
                'hedge_symbol': self.config.get('hedge_symbol'),
            })
            return run
        except Exception as e:
            self.logger.warning(f"MLflow tracking disabled: {e}")
            return None

    def _end_mlflow(self, run, summary: Optional[Dict[str, Any]] = None, error: Optional[str] = None) -> None:
        if run is None:
            return
        try:
            import mlflow
            if summary is not None:
                metrics = {k: summary[k] for k in ('bars', 'option_entries', 'hedges') if summary.get(k) is not None}
                if summary.get('final_portfolio_value') is not None:
                    metrics['final_portfolio_value'] = float(summary['final_portfolio_value'])
                mlflow.log_metrics(metrics)
            if error is not None:
                mlflow.log_param('error', error[:500])
            mlflow.end_run()
        except Exception as e:
            self.logger.warning(f"MLflow logging failed: {e}")
