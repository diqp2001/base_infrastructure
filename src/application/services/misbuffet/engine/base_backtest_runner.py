"""
Generic backtest runner base class.

Project-specific runners subclass BaseBacktestRunner and implement the two
abstract hooks:
  - setup_components(config)     — init ModelTrainer, Strategy, etc.
  - create_algorithm_instance()  — return a configured Algorithm instance

All Misbuffet engine wiring, async threading, status/results/stop helpers,
and performance-metric delegation live here so they don't have to be repeated
in every project.

Run registry (2026-11-18): every run_backtest is a BacktestRun (src/application/services/backtest_registry):
a unique id, the full config snapshot, the git commit, the requested and the processed window, the portfolios it
created, the models it used and a status decided from the bars actually processed (COMPLETED only when the last
bar reaches the requested end; an early stop is PARTIAL). Each run books into its own portfolios
(<Portfolio.name>_run<id>), so runs never reset or share each other's book. Projects describe their run with
describe_run(config) (universe, price source, dividends, costs, leverage ...). config['run_registry'] =
{'enabled': False} turns it off; a registry failure is logged and never stops the backtest.
"""

import functools
import logging
import threading
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional

from src.application.services.database_service.database_service import DatabaseService
from src.application.services.misbuffet import Misbuffet
from src.application.services.misbuffet.engine.performance_metrics import calculate_performance_metrics
from src.application.services.misbuffet.launcher.interfaces import LauncherConfiguration, LauncherMode

logger = logging.getLogger(__name__)


def _record_job(func):
    """Record backtest start / end for the read-only monitoring dashboard.

    Monitoring never changes the run: recorder errors are swallowed, the result is returned
    unchanged and exceptions propagate exactly as before.
    """
    @functools.wraps(func)
    def wrapper(self, config, *args, **kwargs):
        recorder = None
        try:
            from src.application.services.monitoring.job_tracker import JobRecorder
            from src.application.services.monitoring.log_store import install_monitoring_log_handler
            install_monitoring_log_handler(process_name="backtest")
            recorder = JobRecorder("backtest", str(config.get("project_name") or type(self).__name__),
                                   details={"runner": type(self).__name__,
                                            "backtest_start": str(config.get("backtest_start")),
                                            "backtest_end": str(config.get("backtest_end"))}).start()
        except Exception:
            recorder = None
        try:
            result = func(self, config, *args, **kwargs)
        except BaseException as e:
            if recorder is not None:
                recorder.finish(False, error=f"{type(e).__name__}: {e}")
            raise
        if recorder is not None:
            try:
                summary = str((result or {}).get("misbuffet_result") or "") if isinstance(result, dict) else ""
                ok = isinstance(result, dict) and result.get("success") is not False and "Backtest failed" not in summary
                error = None if ok else (result.get("error") if isinstance(result, dict) and result.get("error")
                                         else summary[:500] or "backtest reported failure")
                recorder.finish(ok, error=error)
            except Exception:
                pass
        return result
    return wrapper


class BaseBacktestRunner(ABC):
    """
    Framework-level backtest orchestrator.

    Handles: Misbuffet launch + LauncherConfiguration wiring, async threading,
    status/results/stop helpers, and performance-metric calculation.

    Subclasses must implement setup_components and create_algorithm_instance.
    """

    def __init__(self, database_service: DatabaseService):
        self.database_service = database_service
        self.logger = logging.getLogger(self.__class__.__name__)

        self.model_trainer = None
        self.strategy = None
        self.algorithm_instance = None

        self.is_running = False
        self.backtest_thread: Optional[threading.Thread] = None
        self.results: Dict[str, Any] = {}
        self.progress: float = 0.0
        self.run = None                      # BacktestRun of the current / last run_backtest (None: no registry)
        self.run_tracker = None
        self._registry_service = None
        self._registry_session = None

    # ------------------------------------------------------------------
    # Abstract hooks — implemented by each project's BacktestRunner
    # ------------------------------------------------------------------

    @abstractmethod
    def setup_components(self, config: Dict[str, Any]) -> bool:
        """
        Initialise project-specific components (ModelTrainer, Strategy, …).

        Returns True on success, False on failure.
        """

    @abstractmethod
    def create_algorithm_instance(self):
        """
        Create, configure, and return the project Algorithm instance.

        Called by run_backtest after setup_components succeeds.
        """

    def describe_run(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Run attributes for the registry that the config alone does not say (override per project):
        universe_description, universe_snapshot, price_source, include_dividends, include_transaction_costs,
        gross_leverage, assumptions, data_snapshot, run_name."""
        return {}

    # ------------------------------------------------------------------
    # Run registry (generic research / backtest registry)
    # ------------------------------------------------------------------

    def _registry_factory(self):
        from sqlalchemy.orm import sessionmaker
        from src.infrastructure.repositories.repository_factory import RepositoryFactory
        if self._registry_session is None:
            # its own session: registry commits never commit (or roll back) the engine's pending work
            self._registry_session = sessionmaker(bind=self.database_service.session.get_bind())()
        return RepositoryFactory(self._registry_session)

    def _register_run(self, config: Dict[str, Any], start_date, end_date) -> Dict[str, Any]:
        """Register the run and give it its own portfolio name. Returns the config the run uses."""
        self.run, self.run_tracker = None, None
        settings = config.get('run_registry') or {}
        if settings.get('enabled', True) is False:
            return config
        try:
            from src.application.services.backtest_registry.backtest_run_service import BacktestRunService
            service = BacktestRunService(self._registry_factory())
            describe = dict(self.describe_run(config) or {})
            run_name = describe.pop('run_name', None) or config.get('run_name')
            run = service.register(str(config.get('project_name') or type(self).__name__), config,
                                   run_name=run_name, requested_start=start_date, requested_end=end_date,
                                   describe=describe)
            portfolio = config.get('Portfolio')
            if isinstance(portfolio, dict) and portfolio.get('name') and settings.get('unique_portfolios', True):
                config = dict(config)
                config['Portfolio'] = {**portfolio, 'name': f"{portfolio['name']}_run{run.id}"}
            self.run = service.start(run)
            self.run_tracker = service.tracker(self.run)
            self._registry_service = service
            self.logger.info(f"Backtest run {self.run.id} ({self.run.run_uid}) registered: "
                             f"{self.run.months_planned} months planned")
        except Exception as e:
            self.logger.warning(f"Backtest run registry unavailable, the run is not registered: {e}")
            self.run, self.run_tracker = None, None
        return config

    def _track_bars(self, algorithm) -> None:
        """Wrap the algorithm's on_data: every processed bar moves the run's actual window."""
        if self.run_tracker is None or algorithm is None or not hasattr(algorithm, 'on_data'):
            return
        tracker, inner = self.run_tracker, algorithm.on_data

        def on_data(data, *args, **kwargs):
            result = inner(data, *args, **kwargs)
            try:
                tracker.bar(getattr(data, 'time', None) or getattr(algorithm, 'time', None))
            except Exception:
                pass
            return result
        algorithm.on_data = on_data

    def _finish_run(self, error: Optional[str] = None, cancelled: bool = False) -> None:
        if self.run is None or self._registry_service is None:
            return
        service = self._registry_service
        try:
            if self.run_tracker is not None:
                self.run_tracker.flush()
                self.run = self.run_tracker.run
            algorithm = self.algorithm_instance
            portfolio = getattr(algorithm, '_current_portfolio_entity', None)
            if portfolio is not None and getattr(portfolio, 'id', None) is not None:
                service.register_portfolio_tree(self.run, portfolio.id, label=getattr(portfolio, 'name', None))
            from src.application.services.misbuffet import run_manifest
            artifacts = run_manifest.models_of(algorithm)
            if artifacts:
                service.link_artifacts(self.run, artifacts)
            self.run = service.finish(self.run, error=error, cancelled=cancelled)
            from src.application.services.backtest_registry.research_result_service import ResearchResultService
            ResearchResultService(service.factory).engine_metrics(self.run.id, calculate_performance_metrics,
                                                                  self.run.starting_capital)
            self.logger.info(f"Backtest run {self.run.id}: {self.run.status} ({self.run.progress_label()})")
        except Exception as e:
            self.logger.warning(f"Backtest run {getattr(self.run, 'id', None)}: registry update failed: {e}")

    # ------------------------------------------------------------------
    # Generic backtest execution
    # ------------------------------------------------------------------

    @_record_job
    def run_backtest(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a synchronous backtest via the Misbuffet engine.

        Parses config, calls setup_components and create_algorithm_instance,
        then wires LauncherConfiguration and runs the engine.
        """
        try:
            self.logger.info("Starting backtest...")

            def _parse_date(d):
                if isinstance(d, datetime):
                    return d
                for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                    try:
                        return datetime.strptime(d, fmt)
                    except (ValueError, TypeError):
                        continue
                raise ValueError(f"Cannot parse date: {d!r}")

            start_date = _parse_date(config.get('backtest_start', '2025-07-01'))
            end_date = _parse_date(config.get('backtest_end', '2025-12-31'))
            config = self._register_run(config, start_date, end_date)
            initial_capital = config.get('initial_capital', 100000)
            universe = config.get('universe')
            model_type = config.get('model_type')
            config_interval = config.get('config_interval')

            if not self.setup_components(config):
                raise Exception("Component setup failed")

            self.is_running = True
            self.progress = 0.0

            self.logger.info("Creating configured algorithm instance...")
            configured_algorithm = self.create_algorithm_instance()
            if configured_algorithm is not None:
                self.algorithm_instance = configured_algorithm
            self._track_bars(configured_algorithm)

            self.logger.info("Configuring Misbuffet framework...")
            misbuffet = Misbuffet.launch(config_file="launch_config.py")

            launcher_config = LauncherConfiguration(
                mode=LauncherMode.BACKTESTING,
                algorithm_type_name="Algorithm",
                algorithm_location=__file__,
                data_folder="",
                environment="backtesting",
                live_mode=False,
                debugging=True,
            )

            launcher_config.custom_config = {
                'start_date': start_date,
                'end_date': end_date,
                'initial_capital': initial_capital,
                'tickers': universe,
                'model_type': model_type,
                'custom_interval': config_interval,
            }
            launcher_config.main_config = config
            launcher_config.algorithm = configured_algorithm
            launcher_config.database_service = self.database_service
            launcher_config.model_trainer = self.model_trainer
            launcher_config.momentum_strategy = self.strategy

            self.logger.info("Starting backtest engine...")
            engine = misbuffet.start_engine(config_file="engine_config.py")

            self.logger.info("Executing backtest algorithm...")
            t0 = datetime.now()
            result = engine.run(launcher_config)
            elapsed = (datetime.now() - t0).total_seconds()

            backtest_summary = {
                'backtest_config': {
                    'tickers': universe,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'initial_capital': initial_capital,
                    'model_type': model_type,
                },
                'misbuffet_result': result.summary() if result else None,
                'execution_time': elapsed,
                'success': True,
                'timestamp': datetime.now().isoformat(),
            }

            self.logger.info(f"Backtest completed in {elapsed:.2f}s")
            if result:
                self.logger.info(f"Result summary: {result.summary()}")

            summary_text = str(backtest_summary.get('misbuffet_result') or '')
            engine_error = None
            if 'Backtest failed' in summary_text:
                engine_error = summary_text.split('failed:', 1)[-1].strip() or summary_text
            self._finish_run(error=engine_error)
            if self.run is not None:
                backtest_summary['run_id'] = self.run.id
                backtest_summary['run_status'] = self.run.status
                backtest_summary['run_progress'] = self.run.progress_label()
            self.results = backtest_summary
            self.is_running = False
            return backtest_summary

        except KeyboardInterrupt:
            self._finish_run(cancelled=True)
            self.is_running = False
            raise
        except Exception as e:
            self.logger.error(f"Error running backtest: {e}")
            self._finish_run(error=f"{type(e).__name__}: {e}")
            self.is_running = False
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'run_id': getattr(self.run, 'id', None),
                'run_status': getattr(self.run, 'status', None),
            }

    def run_backtest_async(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Start run_backtest in a daemon thread and return immediately."""
        try:
            if self.is_running:
                return {
                    'success': False,
                    'message': 'Backtest already running',
                    'status': 'already_running',
                }

            self.backtest_thread = threading.Thread(
                target=self.run_backtest,
                args=(config,),
                daemon=True,
            )
            self.backtest_thread.start()

            return {
                'success': True,
                'message': 'Backtest started successfully',
                'status': 'started',
                'start_timestamp': datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error starting async backtest: {e}")
            return {
                'success': False,
                'error': str(e),
                'status': 'failed_to_start',
            }

    # ------------------------------------------------------------------
    # Status / results / control
    # ------------------------------------------------------------------

    def get_backtest_status(self) -> Dict[str, Any]:
        """Return current running state and progress."""
        try:
            return {
                'is_running': self.is_running,
                'progress': self.progress,
                'has_results': bool(self.results),
                'thread_alive': self.backtest_thread.is_alive() if self.backtest_thread else False,
                'status_timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Error getting backtest status: {e}")
            return {'is_running': False, 'progress': 0, 'has_results': False, 'error': str(e)}

    def get_backtest_results(self) -> Dict[str, Any]:
        """Return stored results, or indicate none are available."""
        try:
            if not self.results:
                return {'has_results': False, 'message': 'No backtest results available'}
            return {
                'has_results': True,
                'results': self.results,
                'retrieval_timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Error getting backtest results: {e}")
            return {'has_results': False, 'error': str(e)}

    def stop_backtest(self) -> Dict[str, Any]:
        """Signal the running backtest to stop and wait up to 10 s for the thread."""
        try:
            if not self.is_running:
                return {'success': True, 'message': 'No backtest running', 'status': 'not_running'}

            self.is_running = False

            if self.backtest_thread and self.backtest_thread.is_alive():
                self.backtest_thread.join(timeout=10)

            return {
                'success': True,
                'message': 'Backtest stopped',
                'status': 'stopped',
                'stop_timestamp': datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"Error stopping backtest: {e}")
            return {'success': False, 'error': str(e), 'status': 'error'}

    # ------------------------------------------------------------------
    # Performance metrics helper (delegates to standalone function)
    # ------------------------------------------------------------------

    def _calculate_performance_metrics(
        self,
        daily_returns: List[float],
        initial_capital: float,
        final_value: float,
    ) -> Dict[str, Any]:
        return calculate_performance_metrics(daily_returns, initial_capital, final_value)
