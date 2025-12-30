"""
Backtest Runner for SPX Call Spread Market Making

This module implements the backtesting engine for the SPX call spread market making strategy,
integrating with the Misbuffet framework.
"""

import logging
import os
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

from application.managers.project_managers.market_making_SPX_call_spread_project.backtesting.base_project_algorithm import Algorithm
from application.managers.project_managers.market_making_SPX_call_spread_project.data.factor_manager import FactorManager
from application.managers.project_managers.market_making_SPX_call_spread_project.models.model_trainer import ModelTrainer
from application.managers.project_managers.market_making_SPX_call_spread_project.strategy.market_making_strategy import Strategy
from application.services.misbuffet import Misbuffet
from application.services.misbuffet.launcher.interfaces import LauncherConfiguration, LauncherMode
from src.application.services.database_service.database_service import DatabaseService

logger = logging.getLogger(__name__)


class BacktestRunner:
    """
    Backtest runner for SPX call spread market making strategy.
    Manages the execution of backtests using the Misbuffet framework.
    """
    
    def __init__(self, database_service: DatabaseService):
        """
        Initialize the backtest runner.
        
        Args:
            database_service: Database service instance
        """
        self.database_service = database_service
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize components
        self.factor_manager = FactorManager(self.database_service)
        self.model_trainer = None
        self.momentum_strategy = None
        self.algorithm_instance = None

        # Backtest state
        self.is_running = False
        self.backtest_thread = None
        self.results = {}
        self.progress = 0
        
        # Misbuffet components (to be initialized when needed)
        self.misbuffet_engine = None
        self.algorithm = None
    def setup_components(self, config: Dict[str, Any]) -> bool:
        """
        Set up all test_base_project components.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if setup successful, False otherwise
        """
        try:
            self.logger.info("Setting up test_base_project components...")
            
            # Initialize model trainer
            self.model_trainer = ModelTrainer(self.database_service)
            self.logger.info("✅ Model trainer initialized")
            
            # Initialize momentum strategy
            self.strategy = Strategy( config)
            self.logger.info("✅ Momentum strategy initialized")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error setting up components: {str(e)}")
            return False
    def run_backtest(
        self,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Run a backtest with the specified configuration and algorithm.
        
        Args:
            config: Backtest configuration
            algorithm_class: Algorithm class to run
            
        Returns:
            Dict containing backtest results
        """
        try:
            self.logger.info("Starting SPX call spread backtest...")
            
            # Initialize backtest parameters
            model_type = "pricing"
            tickers = ["SPX"]
            start_date = config.get('backtest_start', '2025-07-01')
            end_date = config.get('backtest_end', '2025-12-31')
            initial_capital = config.get('initial_capital', 100000)

            if not self.setup_components(config):
                raise Exception("Component setup failed")
            
            
            
            # Configure algorithm
            algorithm_config = {
                'start_date': start_date,
                'end_date': end_date,
                'initial_capital': initial_capital,
                'database_service': self.database_service,
                **config
            }
            
            
            
            # Run backtest simulation
            self.is_running = True
            self.progress = 0
            
            self.logger.info("🔧 Creating configured algorithm instance...")
            configured_algorithm = self.create_algorithm_instance()
            
            # Step 5: Configure Misbuffet launcher
            self.logger.info("🔧 Configuring Misbuffet framework...")
            
            # Launch Misbuffet with config file path (not dictionary)
            misbuffet = Misbuffet.launch(config_file="launch_config.py")
            
            # Configure engine with LauncherConfiguration
            launcher_config = LauncherConfiguration(
                mode=LauncherMode.BACKTESTING,
                algorithm_type_name="Algorithm",
                algorithm_location=__file__,
                data_folder="",
                environment="backtesting",
                live_mode=False,
                debugging=True
            )
            
            # Override with custom config values
            launcher_config.custom_config = {
                'start_date': start_date,
                'end_date': end_date,
                'initial_capital': initial_capital,
                'tickers': tickers,
                'model_type': model_type
            }
            
            # Pass the configured algorithm INSTANCE (not class) for Misbuffet to use
            launcher_config.algorithm = configured_algorithm
            
            # Add database manager and other dependencies for real data access
            launcher_config.database_service = self.database_service
            launcher_config.factor_manager = self.factor_manager
            launcher_config.model_trainer = self.model_trainer
            launcher_config.momentum_strategy = self.momentum_strategy
            
            # Step 6: Start engine and run backtest
            self.logger.info("🚀 Starting backtest engine...")
            engine = misbuffet.start_engine(config_file="engine_config.py")
            
            self.logger.info("📊 Executing backtest algorithm...")
            result = engine.run(launcher_config)
            
            # Step 7: Process results
            end_time = datetime.now()
            elapsed_time = (end_time - start_time).total_seconds()
            
            backtest_summary = {
                'backtest_config': {
                    'tickers': tickers,
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'initial_capital': initial_capital,
                    'model_type': model_type
                },
                'factor_system': factor_results if setup_factors else None,
                #'model_training': training_results,
                'misbuffet_result': result.summary() if result else None,
                'execution_time': elapsed_time,
                'success': True,
                'timestamp': end_time.isoformat()
            }
            
            self.logger.info(f"✅ Backtest completed successfully in {elapsed_time:.2f} seconds")
            if result:
                self.logger.info(f"📈 Result summary: {result.summary()}")
            
            self.results = backtest_summary
            self.is_running = False
            
            self.logger.info("✅ SPX call spread backtest completed")
            return backtest_summary
            
        except Exception as e:
            self.logger.error(f"Error running backtest: {e}")
            self.is_running = False
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
            }
    def create_algorithm_instance(self) -> Algorithm:
        """
        Create and configure the algorithm instance.
        
        Returns:
            Configured BaseProjectAlgorithm instance
        """
        try:
            # Create algorithm instance
            algorithm = Algorithm()
            
            # Always inject our components - ensure they are not None
            if self.factor_manager:
                algorithm.set_factor_manager(self.factor_manager)
                self.logger.info("✅ Factor manager injected into algorithm")
            else:
                self.logger.warning("⚠️ Factor manager is None - algorithm will have limited functionality")
            
            if self.model_trainer:
                algorithm.set_trainer(self.model_trainer)
                self.logger.info("✅ Spatiotemporal trainer injected into algorithm")
            else:
                self.logger.warning("⚠️ Model trainer is None")
            
            if self.strategy:
                algorithm.set_strategy(self.strategy)
                self.logger.info("✅ strategy injected into algorithm")
            else:
                self.logger.warning("⚠️ Momentum strategy is None")
            
            self.algorithm_instance = algorithm
            self.logger.info("✅ Algorithm instance created and configured")
            
            return algorithm
            
        except Exception as e:
            self.logger.error(f"❌ Error creating algorithm instance: {str(e)}")
            raise
    def run_backtest_async(
        self,
        config: Dict[str, Any],
        algorithm_class: type
    ) -> Dict[str, Any]:
        """
        Run backtest asynchronously.
        
        Args:
            config: Backtest configuration
            algorithm_class: Algorithm class to run
            
        Returns:
            Dict containing backtest startup status
        """
        try:
            if self.is_running:
                return {
                    'success': False,
                    'message': 'Backtest already running',
                    'status': 'already_running',
                }
            
            # Start backtest in separate thread
            self.backtest_thread = threading.Thread(
                target=self.run_backtest,
                args=(config, algorithm_class)
            )
            self.backtest_thread.daemon = True
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
    
    def get_backtest_status(self) -> Dict[str, Any]:
        """
        Get current backtest status and progress.
        
        Returns:
            Dict containing status information
        """
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
            return {
                'is_running': False,
                'progress': 0,
                'has_results': False,
                'error': str(e),
            }
    
    def get_backtest_results(self) -> Dict[str, Any]:
        """
        Get backtest results if available.
        
        Returns:
            Dict containing backtest results
        """
        try:
            if not self.results:
                return {
                    'has_results': False,
                    'message': 'No backtest results available',
                }
            
            return {
                'has_results': True,
                'results': self.results,
                'retrieval_timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Error getting backtest results: {e}")
            return {
                'has_results': False,
                'error': str(e),
            }
    
    def stop_backtest(self) -> Dict[str, Any]:
        """
        Stop running backtest.
        
        Returns:
            Dict containing stop status
        """
        try:
            if not self.is_running:
                return {
                    'success': True,
                    'message': 'No backtest running',
                    'status': 'not_running',
                }
            
            # Signal stop
            self.is_running = False
            
            # Wait for thread to finish (with timeout)
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
            return {
                'success': False,
                'error': str(e),
                'status': 'error',
            }
    
    def _execute_backtest_simulation(
        self,
        start_date: str,
        end_date: str,
        initial_capital: float
    ) -> Dict[str, Any]:
        """
        Execute the actual backtest simulation.
        
        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Initial capital amount
            
        Returns:
            Dict containing simulation results
        """
        try:
            simulation_start = datetime.now()
            
            # Simulate trading days
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            total_days = (end_dt - start_dt).days
            trading_days = []
            
            # Generate trading days (weekdays only)
            current_date = start_dt
            while current_date <= end_dt:
                if current_date.weekday() < 5:  # Monday = 0, Friday = 4
                    trading_days.append(current_date)
                current_date += timedelta(days=1)
            
            # Initialize portfolio tracking
            portfolio_value = initial_capital
            daily_returns = []
            positions_history = []
            trades_executed = []
            
            # Simulate each trading day
            for i, trading_date in enumerate(trading_days):
                if not self.is_running:  # Check if stopped
                    break
                
                # Update progress
                self.progress = (i / len(trading_days)) * 100
                
                # Simulate daily trading
                daily_result = self._simulate_trading_day(
                    trading_date, portfolio_value
                )
                
                # Update portfolio
                portfolio_value = daily_result.get('end_portfolio_value', portfolio_value)
                daily_return = daily_result.get('daily_return', 0)
                daily_returns.append(daily_return)
                
                # Track positions and trades
                positions_history.append(daily_result.get('positions', {}))
                trades_executed.extend(daily_result.get('trades', []))
                
                # Brief pause to allow for stopping
                time.sleep(0.001)
            
            simulation_end = datetime.now()
            simulation_duration = (simulation_end - simulation_start).total_seconds()
            
            # Calculate performance metrics
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
                    'positions_history': positions_history[-10:],  # Last 10 days
                    'sample_trades': trades_executed[:20],  # First 20 trades
                },
                'simulation_info': {
                    'duration_seconds': simulation_duration,
                    'completed': self.is_running or len(trading_days) == len(daily_returns),
                    'completion_timestamp': datetime.now().isoformat(),
                },
            }
            
        except Exception as e:
            self.logger.error(f"Error in backtest simulation: {e}")
            return {
                'success': False,
                'error': str(e),
                'simulation_info': {
                    'completion_timestamp': datetime.now().isoformat(),
                },
            }
    
    def _simulate_trading_day(
        self,
        trading_date: datetime,
        start_portfolio_value: float
    ) -> Dict[str, Any]:
        """
        Simulate a single trading day.
        
        Args:
            trading_date: Date to simulate
            start_portfolio_value: Portfolio value at start of day
            
        Returns:
            Dict containing day's results
        """
        try:
            # Generate mock market data for the day
            spx_price = 4500 + (trading_date.timetuple().tm_yday % 100) - 50  # Simple variation
            vix = 20 + (trading_date.timetuple().tm_yday % 20) - 10  # VIX variation
            
            market_data = {
                'date': trading_date,
                'spx_price': spx_price,
                'vix': vix,
            }
            
            # Call algorithm's on_data method (if implemented)
            if hasattr(self.algorithm, 'on_data'):
                self.algorithm.on_data(market_data)
            
            # Simulate some trading activity
            daily_return = 0.001 * (spx_price - 4500) / 4500  # Simple return calculation
            end_portfolio_value = start_portfolio_value * (1 + daily_return)
            
            # Mock positions and trades
            positions = {
                f"spread_{trading_date.strftime('%Y%m%d')}": {
                    'type': 'bull_call_spread',
                    'strikes': {'long': spx_price - 25, 'short': spx_price + 25},
                    'entry_date': trading_date,
                    'size': 1,
                }
            }
            
            trades = []
            if trading_date.weekday() == 0:  # Enter positions on Monday
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
    
    def _calculate_performance_metrics(
        self,
        daily_returns: List[float],
        initial_capital: float,
        final_value: float
    ) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics.
        
        Args:
            daily_returns: List of daily returns
            initial_capital: Initial capital amount
            final_value: Final portfolio value
            
        Returns:
            Dict containing performance metrics
        """
        try:
            if not daily_returns:
                return {'error': 'No returns data available'}
            
            import numpy as np
            
            returns_array = np.array(daily_returns)
            
            # Basic metrics
            total_return = (final_value - initial_capital) / initial_capital
            annualized_return = (1 + total_return) ** (252 / len(daily_returns)) - 1
            
            # Risk metrics
            volatility = np.std(returns_array) * np.sqrt(252)  # Annualized
            sharpe_ratio = annualized_return / volatility if volatility != 0 else 0
            
            # Drawdown analysis
            cumulative_returns = np.cumprod(1 + returns_array)
            running_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (cumulative_returns - running_max) / running_max
            max_drawdown = np.min(drawdowns)
            
            # Win rate
            positive_days = np.sum(returns_array > 0)
            win_rate = positive_days / len(returns_array)
            
            return {
                'total_return': total_return,
                'annualized_return': annualized_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'total_trading_days': len(daily_returns),
                'best_day': np.max(returns_array),
                'worst_day': np.min(returns_array),
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {e}")
            return {
                'error': str(e),
                'total_return': (final_value - initial_capital) / initial_capital,
            }