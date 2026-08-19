"""
Backtest runner for the SPX call spread market making project.

Generic orchestration (Misbuffet wiring, async threading, status/results/stop,
performance metrics) is inherited from BaseBacktestRunner.
Only project-specific logic lives here.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any

from src.application.managers.project_managers.market_making_SPX_call_spread_project.backtesting.base_project_algorithm import Algorithm
from src.application.managers.project_managers.market_making_SPX_call_spread_project.models.model_trainer import ModelTrainer
from src.application.managers.project_managers.market_making_SPX_call_spread_project.strategy.market_making_strategy import Strategy
from src.application.services.database_service.database_service import DatabaseService
from src.application.services.misbuffet.engine.base_backtest_runner import BaseBacktestRunner

logger = logging.getLogger(__name__)


class BacktestRunner(BaseBacktestRunner):
    """
    SPX call spread backtest runner.

    Implements the two abstract hooks from BaseBacktestRunner and adds the
    mock simulation helpers used for development/testing.
    """

    def __init__(self, database_service: DatabaseService):
        super().__init__(database_service)
        self.momentum_strategy = None  # kept for launcher_config compatibility

    # ------------------------------------------------------------------
    # Abstract hook implementations
    # ------------------------------------------------------------------

    def setup_components(self, config: Dict[str, Any]) -> bool:
        """Initialise ModelTrainer and Strategy for this project."""
        try:
            self.logger.info("Setting up SPX call spread components...")

            self.model_trainer = ModelTrainer(self.database_service)
            self.logger.info("✅ Model trainer initialized")

            self.strategy = Strategy(config)
            self.logger.info("✅ Strategy initialized")

            return True

        except Exception as e:
            self.logger.error(f"❌ Error setting up components: {str(e)}")
            return False

    def create_algorithm_instance(self) -> Algorithm:
        """Create and configure the SPX algorithm instance."""
        try:
            algorithm = Algorithm()

            if self.model_trainer:
                algorithm.set_trainer(self.model_trainer)
                if (hasattr(self.model_trainer, 'data_loader')
                        and hasattr(self.model_trainer.data_loader, 'financial_asset_service')):
                    entity_service = self.model_trainer.data_loader.financial_asset_service
                    algorithm.set_entity_service(entity_service)
                    self.logger.info("✅ EntityService injected into algorithm from ModelTrainer")
                else:
                    self.logger.warning("⚠️ EntityService not found in ModelTrainer's data loader")
                self.logger.info("✅ Trainer injected into algorithm")
            else:
                self.logger.warning("⚠️ Model trainer is None")

            if self.strategy:
                algorithm.set_strategy(self.strategy)
                self.logger.info("✅ Strategy injected into algorithm")
            else:
                self.logger.warning("⚠️ Strategy is None")

            self.algorithm_instance = algorithm
            self.logger.info("✅ Algorithm instance created and configured")
            return algorithm

        except Exception as e:
            self.logger.error(f"❌ Error creating algorithm instance: {str(e)}")
            raise

    # ------------------------------------------------------------------
    # Model training (project-specific)
    # ------------------------------------------------------------------

    def train_models(self, tickers: List[str], model_type: str = 'both', seeds: List[int] = None) -> Dict[str, Any]:
        """Train GBM models via the ModelTrainer pipeline."""
        if seeds is None:
            seeds = [42, 123]
        self.logger.info(f"Training models ({model_type}) for {len(tickers)} tickers...")

        try:
            training_results = self.model_trainer.train_complete_pipeline(
                tickers=tickers,
                model_type=model_type,
                seeds=seeds,
            )

            if training_results and not training_results.get('error'):
                self.logger.info("✅ Model training completed successfully")
                return training_results
            else:
                error_msg = training_results.get('error', 'Unknown training error')
                self.logger.error(f"❌ Model training failed: {error_msg}")
                return {'error': error_msg, 'success': False}

        except Exception as e:
            self.logger.error(f"❌ Error during model training: {str(e)}")
            return {'error': str(e), 'success': False}

    # ------------------------------------------------------------------
    # Mock simulation helpers (development / testing only)
    # ------------------------------------------------------------------

    def _execute_backtest_simulation(
        self,
        start_date: str,
        end_date: str,
        initial_capital: float,
    ) -> Dict[str, Any]:
        """Mock backtest simulation used during development."""
        try:
            simulation_start = datetime.now()

            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')

            trading_days = []
            current_date = start_dt
            while current_date <= end_dt:
                if current_date.weekday() < 5:
                    trading_days.append(current_date)
                current_date += timedelta(days=1)

            portfolio_value = initial_capital
            daily_returns = []
            positions_history = []
            trades_executed = []

            for i, trading_date in enumerate(trading_days):
                if not self.is_running:
                    break

                self.progress = (i / len(trading_days)) * 100

                daily_result = self._simulate_trading_day(trading_date, portfolio_value)

                portfolio_value = daily_result.get('end_portfolio_value', portfolio_value)
                daily_returns.append(daily_result.get('daily_return', 0))
                positions_history.append(daily_result.get('positions', {}))
                trades_executed.extend(daily_result.get('trades', []))

                time.sleep(0.001)

            elapsed = (datetime.now() - simulation_start).total_seconds()
            performance_metrics = self._calculate_performance_metrics(
                daily_returns, initial_capital, portfolio_value
            )

            return {
                'success': True,
                'backtest_period': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'trading_days': len(trading_days),
                },
                'portfolio_performance': {
                    'initial_capital': initial_capital,
                    'final_value': portfolio_value,
                    'total_return': (portfolio_value - initial_capital) / initial_capital,
                    'daily_returns': daily_returns,
                },
                'performance_metrics': performance_metrics,
                'trading_activity': {
                    'total_trades': len(trades_executed),
                    'positions_history': positions_history[-10:],
                    'sample_trades': trades_executed[:20],
                },
                'simulation_info': {
                    'duration_seconds': elapsed,
                    'completed': self.is_running or len(trading_days) == len(daily_returns),
                    'completion_timestamp': datetime.now().isoformat(),
                },
            }

        except Exception as e:
            self.logger.error(f"Error in backtest simulation: {e}")
            return {
                'success': False,
                'error': str(e),
                'simulation_info': {'completion_timestamp': datetime.now().isoformat()},
            }

    def _simulate_trading_day(
        self,
        trading_date: datetime,
        start_portfolio_value: float,
    ) -> Dict[str, Any]:
        """Mock single-day simulation."""
        try:
            spx_price = 4500 + (trading_date.timetuple().tm_yday % 100) - 50
            vix = 20 + (trading_date.timetuple().tm_yday % 20) - 10

            market_data = {'date': trading_date, 'spx_price': spx_price, 'vix': vix}

            if hasattr(self, 'algorithm') and hasattr(self.algorithm, 'on_data'):
                self.algorithm.on_data(market_data)

            daily_return = 0.001 * (spx_price - 4500) / 4500
            end_portfolio_value = start_portfolio_value * (1 + daily_return)

            positions = {
                f"spread_{trading_date.strftime('%Y%m%d')}": {
                    'type': 'bull_call_spread',
                    'strikes': {'long': spx_price - 25, 'short': spx_price + 25},
                    'entry_date': trading_date,
                    'size': 1,
                }
            }

            trades = []
            if trading_date.weekday() == 0:
                trades.append({
                    'date': trading_date,
                    'action': 'enter_spread',
                    'spread_type': 'bull_call_spread',
                    'strikes': positions[f"spread_{trading_date.strftime('%Y%m%d')}"]['strikes'],
                })

            return {
                'date': trading_date,
                'start_portfolio_value': start_portfolio_value,
                'end_portfolio_value': end_portfolio_value,
                'daily_return': daily_return,
                'market_data': market_data,
                'positions': positions,
                'trades': trades,
            }

        except Exception as e:
            self.logger.error(f"Error simulating trading day {trading_date}: {e}")
            return {
                'date': trading_date,
                'start_portfolio_value': start_portfolio_value,
                'end_portfolio_value': start_portfolio_value,
                'daily_return': 0,
                'error': str(e),
            }
