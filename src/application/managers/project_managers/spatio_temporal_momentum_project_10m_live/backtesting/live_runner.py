"""
LiveRunner — runs the Spatio-Temporal Momentum algorithm in the Misbuffet engine against IBKR (paper or live).

Same components as the 10m project's BacktestRunner (STMModelTrainer + Algorithm), launched with:
    live_mode=True, brokerage=<connected InteractiveBrokersBroker>   -> BrokerageTransactionHandler, live algorithm
    live_clock=<LiveClock>                                          -> one step per closed bar, on the wall clock
and a live stack factory: when the algorithm initialises, build_live_stack wires the order ledger, start-up
recovery, reconciliation and the pre-trade gate around the broker, and start-up recovery must pass before the run
goes on. At the end (session over, stop requested, Ctrl+C, failure) the stack is shut down.

run_backtest is refused: this project's book is a live book.
"""

import logging
from datetime import datetime
from typing import Any, Dict

from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.backtesting.base_project_algorithm import (
    Algorithm,
)
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.data.shortable_inventory import (
    ShortableInventory,
)
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.models.model_trainer import (
    STMModelTrainer,
)
from src.application.services.misbuffet import Misbuffet
from src.application.services.misbuffet.engine.base_backtest_runner import BaseBacktestRunner
from src.application.services.misbuffet.launcher.interfaces import LauncherConfiguration, LauncherMode
from src.application.services.misbuffet.live.live_stack import LiveStackConfig, build_live_stack

logger = logging.getLogger(__name__)


class LiveRunner(BaseBacktestRunner):

    def __init__(self, database_service):
        super().__init__(database_service)
        self.broker = None
        self.config: Dict[str, Any] = {}
        self.algorithm_instance = None
        self.shutdown_report = None

    def setup_components(self, config: Dict[str, Any]) -> bool:
        try:
            self.model_trainer = STMModelTrainer(self.database_service, config)
            self.strategy = None
            return True
        except Exception as e:
            self.logger.error(f"Error setting up Spatio-Temporal Momentum components: {e}")
            return False

    def create_algorithm_instance(self) -> Algorithm:
        algorithm = Algorithm()
        # NB: BaseBacktestRunner uses `self.progress` for its own percentage (float)
        algorithm.progress_tracker = getattr(self, "progress_tracker", None)
        algorithm.project_config = self.config
        algorithm.live_stack_factory = self.build_stack
        algorithm.set_trainer(self.model_trainer)
        algorithm.set_entity_service(self.model_trainer.data_loader.financial_asset_service)
        self.algorithm_instance = algorithm
        return algorithm

    def run_backtest(self, config: Dict[str, Any]) -> Dict[str, Any]:
        raise RuntimeError("spatio_temporal_momentum_project_10m_live is a live deployment; backtest the strategy "
                           "with spatio_temporal_momentum_project_10m")

    # ------------------------------------------------------------------ live stack
    def stack_config(self) -> LiveStackConfig:
        live = self.config["live"]
        return LiveStackConfig(
            account=live["account"], strategy=live["strategy"], limits=live["limits"],
            allow_delayed_prices=live.get("allow_delayed_prices", False),
            paper_bar_prices=live.get("paper_bar_prices", False),
            max_orders=live.get("max_orders", 20), order_window_seconds=live.get("order_window_seconds", 60.0),
            duplicate_seconds=live.get("duplicate_seconds", 30.0),
        )

    def build_stack(self, algorithm):
        """Called by Algorithm.initialize (live mode, book registered): wire the order path or refuse."""
        live = self.config["live"]
        stack = build_live_stack(self.broker, algorithm._unified_portfolio_manager, algorithm.repository_factory,
                                 self.stack_config(), logger=self.logger,
                                 # paper: the gate prices on the bars the step imported (no IBKR request per order)
                                 bar_prices=algorithm.bar_price if live.get("paper_bar_prices") else None)
        if live.get("shortable_check", True):
            algorithm.shortable = ShortableInventory(logger=self.logger)
        if not self.config["live"].get("paper_bar_prices", False):
            stack.subscribe(self.model_trainer.stm_config.universe.tickers)     # quotes that size orders
        if not stack.recovery.ensure():
            report = stack.recovery.last_report
            stack.shutdown("start-up recovery blocked trading")
            raise RuntimeError("start-up recovery blocked trading: "
                               + (report.summary() if report else "no report")
                               + " — resolve the discrepancies (monitor Trading page) and start again")
        self.logger.warning(f"live stack ready, recovery: {stack.recovery.last_report.summary()}")
        return stack

    # ------------------------------------------------------------------ run
    def run_live(self, config: Dict[str, Any], broker, clock) -> Dict[str, Any]:
        """Run the engine from config['backtest_start'] to config['backtest_end'] on the wall clock."""
        self.config, self.broker = config, broker
        if not self.setup_components(config):
            raise RuntimeError("Component setup failed")
        algorithm = self.create_algorithm_instance()
        launcher_config = LauncherConfiguration(
            mode=LauncherMode.LIVE_TRADING,
            algorithm_type_name="Algorithm",
            algorithm_location=__file__,
            data_folder="",
            environment="live",
            live_mode=True,
            debugging=True,
        )
        launcher_config.custom_config = {
            'start_date': config['backtest_start'],
            'end_date': config['backtest_end'],
            'initial_capital': config.get('initial_capital'),
            'tickers': config.get('universe'),
            'model_type': config.get('model_type'),
            'custom_interval': config.get('config_interval'),
        }
        launcher_config.main_config = config
        launcher_config.algorithm = algorithm
        launcher_config.database_service = self.database_service
        launcher_config.model_trainer = self.model_trainer
        launcher_config.momentum_strategy = None
        launcher_config.brokerage = broker
        launcher_config.live_clock = clock

        misbuffet = Misbuffet.launch(config_file="launch_config.py")
        engine = misbuffet.start_engine(config_file="engine_config.py")
        self.is_running = True
        t0 = datetime.now()
        reason = "end of session"
        try:
            result = engine.run(launcher_config)
            if result is None or not result.success:
                reason = f"engine failed: {getattr(result, 'error_message', None)}"
                raise RuntimeError(f"Misbuffet live run failed: {getattr(result, 'error_message', None)}")
            if clock.stopped:
                reason = clock.stop_reason or "stop requested"
        except BaseException as e:                      # Ctrl+C included: the stack is still shut down
            if reason == "end of session":
                reason = f"interrupted: {e!r}"
            raise
        finally:
            self.is_running = False
            stack = getattr(algorithm, "live_stack", None)
            if stack is not None:
                self.shutdown_report = stack.shutdown(
                    reason, cancel_working=self.config["live"].get("cancel_working_on_shutdown", True))
        return {
            'success': True,
            'reason': reason,
            'decisions': len(algorithm.cycle_results),
            'skipped_steps': [str(t) for t in clock.skipped],
            'shutdown': self.shutdown_report,
            'execution_time': (datetime.now() - t0).total_seconds(),
        }
