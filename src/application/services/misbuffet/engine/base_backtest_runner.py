"""
Generic backtest runner base class.

Project-specific runners subclass BaseBacktestRunner and implement the two
abstract hooks:
  - setup_components(config)     — init ModelTrainer, Strategy, etc.
  - create_algorithm_instance()  — return a configured Algorithm instance

All Misbuffet engine wiring, async threading, status/results/stop helpers,
and performance-metric delegation live here so they don't have to be repeated
in every project.
"""

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

    # ------------------------------------------------------------------
    # Generic backtest execution
    # ------------------------------------------------------------------

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

            self.results = backtest_summary
            self.is_running = False
            return backtest_summary

        except Exception as e:
            self.logger.error(f"Error running backtest: {e}")
            self.is_running = False
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
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
