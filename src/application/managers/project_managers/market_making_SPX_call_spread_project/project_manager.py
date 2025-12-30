import os
import time
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path
import mlflow
import mlflow.sklearn
import mlflow.pytorch

# Base classes
from src.application.services.database_service.database_service import DatabaseService
from src.application.managers.project_managers.project_manager import ProjectManager

# Interactive Brokers integration
from src.application.services.misbuffet.brokers.broker_factory import BrokerFactory, create_interactive_brokers_broker
from application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker

# Backtesting components
from .backtesting.backtest_runner import BacktestRunner
from .backtesting.base_project_algorithm import BaseProjectAlgorithm

# Data components

from .data.factor_manager import FactorEnginedDataManager



# Configuration
from .config import DEFAULT_CONFIG, get_config
from . import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MarketMakingSPXCallSpreadProjectManager(ProjectManager):
    """
    Enhanced Project Manager for backtesting operations.
    Implements a complete backtesting pipeline using  Misbuffet framework integration.
    
    
    """
    
    def __init__(self):
        """
        Initialize the Test Base Project Manager following TestProjectBacktestManager pattern.
        """
        super().__init__()
        
        # Initialize required managers - use TEST config like test_project_backtest
        self.setup_database_service(DatabaseService(config.CONFIG_TEST['DB_TYPE']))
        self.database_service.set_ext_db()
        # Initialize core components
        self.factor_manager = FactorEnginedDataManager(self.database_service)
        # Backtesting components
        self.backtest_runner = BacktestRunner(self.database_service)
        self.algorithm = None
        self.results = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Web interface manager
        try:
            from src.application.services.misbuffet.web.web_interface import WebInterfaceManager
            self.web_interface = WebInterfaceManager()
        except ImportError:
            self.logger.warning("Web interface not available")
            self.web_interface = None
        
        # Runtime state
        self.trained_model = None
        self.strategy = None
        self.signal_generator = None
        self.pipeline_results = {}
        
        # Interactive Brokers broker
        self.ib_broker: Optional[InteractiveBrokersBroker] = None
        
        # MLflow tracking setup
        self.mlflow_experiment_name = "market_making_call_spread_spx_project_manager"
        self.mlflow_run = None
        self._setup_mlflow_tracking()
        
        self.logger.info("🚀 Market making Call Spread SPX ProjectManager initialized with Misbuffet integration and MLflow tracking")
    
    def _setup_mlflow_tracking(self):
        """Setup MLflow experiment tracking."""
        try:
            mlflow.set_experiment(self.mlflow_experiment_name)
            self.logger.info(f"MLflow experiment set: {self.mlflow_experiment_name}")
        except Exception as e:
            self.logger.warning(f"Could not setup MLflow tracking: {e}")
    
    def run(
        self,
        initial_capital: float = 100000,
        start_date: str = "2023-01-01",
        end_date: str = "2024-12-31",
        check_data: bool = True,
        import_data: bool = True,
        run_backtest: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Run the complete SPX call spread market making pipeline.
        
        Args:
            initial_capital: Initial capital for trading
            start_date: Backtest start date
            end_date: Backtest end date
            check_data: Whether to check for existing data
            import_data: Whether to import data if missing
            run_backtest: Whether to run backtest
            **kwargs: Additional configuration
            
        Returns:
            Dict containing comprehensive results
        """
        try:
            self.logger.info("🚀 Starting SPX Call Spread Market Making Pipeline")
            
            # Start MLflow run
            self.mlflow_run = mlflow.start_run()
            
            # Log parameters
            mlflow.log_params({
                'initial_capital': initial_capital,
                'start_date': start_date,
                'end_date': end_date,
                'check_data': check_data,
                'import_data': import_data,
                'run_backtest': run_backtest,
                **kwargs
            })
            
            pipeline_results = {
                'pipeline_start': datetime.now().isoformat(),
                'parameters': {
                    'initial_capital': initial_capital,
                    'start_date': start_date,
                    'end_date': end_date,
                },
                'stages': {},
                'success': False,
            }
            
            # Stage 1: Data Verification and Import
            if check_data or import_data:
                data_stage = self._run_data_stage(import_data)
                pipeline_results['stages']['data_stage'] = data_stage
                
                if not data_stage.get('success', False) and not data_stage.get('data_available', False):
                    raise Exception("Data stage failed and no data available")
            
            # Stage 2: Market Making Strategy Setup
            strategy_stage = self._run_strategy_setup_stage()
            pipeline_results['stages']['strategy_stage'] = strategy_stage
            
            # Stage 3: Backtesting (if requested)
            if run_backtest:
                backtest_stage = self._run_backtest_stage(initial_capital, start_date, end_date)
                pipeline_results['stages']['backtest_stage'] = backtest_stage
                
                # Log backtest metrics
                if backtest_stage.get('success', False):
                    results = backtest_stage.get('results', {})
                    performance = results.get('performance_metrics', {})
                    
                    mlflow.log_metrics({
                        'total_return': performance.get('total_return', 0),
                        'sharpe_ratio': performance.get('sharpe_ratio', 0),
                        'max_drawdown': performance.get('max_drawdown', 0),
                        'win_rate': performance.get('win_rate', 0),
                    })
            
            # Stage 4: Results Compilation
            results_stage = self._compile_final_results(pipeline_results)
            pipeline_results['stages']['results_stage'] = results_stage
            
            pipeline_results['success'] = True
            pipeline_results['pipeline_end'] = datetime.now().isoformat()
            
            # Log artifacts
            mlflow.log_dict(pipeline_results, "pipeline_results.json")
            
            self.logger.info("✅ SPX Call Spread Market Making Pipeline completed successfully")
            return pipeline_results
            
        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            pipeline_results['error'] = str(e)
            pipeline_results['success'] = False
            
            # Log error to MLflow
            mlflow.log_param("error", str(e))
            
            return pipeline_results
            
        finally:
            # End MLflow run
            if self.mlflow_run:
                mlflow.end_run()
    
    def _run_data_stage(self, import_if_missing: bool = True) -> Dict[str, Any]:
        """Run the data verification and import stage."""
        try:
            self.logger.info("📊 Running Data Stage...")
            
            from .data.data_loader import SPXDataLoader
            
            data_loader = SPXDataLoader(self.database_service)
            
            # Check data availability
            data_check = data_loader.check_spx_data_availability()
            has_data = data_check.get('has_spx_data', False)
            
            import_results = None
            
            # Import data if missing and requested
            if not has_data and import_if_missing:
                self.logger.info("💾 Importing SPX data...")
                import_results = data_loader.import_spx_historical_data()
                has_data = import_results.get('success', False)
            
            return {
                'success': True,
                'data_check': data_check,
                'import_results': import_results,
                'data_available': has_data,
                'stage_timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Error in data stage: {e}")
            return {
                'success': False,
                'error': str(e),
                'data_available': False,
                'stage_timestamp': datetime.now().isoformat(),
            }
    
    def _run_strategy_setup_stage(self) -> Dict[str, Any]:
        """Run the strategy setup stage."""
        try:
            self.logger.info("⚙️ Setting up Market Making Strategy...")
            
            # Initialize strategy components
            from .strategy.market_making_strategy import CallSpreadMarketMakingStrategy
            from .strategy.risk_manager import RiskManager
            from .models.pricing_engine import CallSpreadPricingEngine
            from .models.volatility_model import VolatilityModel
            
            strategy = CallSpreadMarketMakingStrategy(self.config)
            risk_manager = RiskManager(self.config)
            pricing_engine = CallSpreadPricingEngine()
            volatility_model = VolatilityModel()
            
            # Store references
            self.strategy = strategy
            self.risk_manager = risk_manager
            self.pricing_engine = pricing_engine
            self.volatility_model = volatility_model
            
            return {
                'success': True,
                'components_initialized': [
                    'CallSpreadMarketMakingStrategy',
                    'RiskManager', 
                    'CallSpreadPricingEngine',
                    'VolatilityModel'
                ],
                'stage_timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Error in strategy setup stage: {e}")
            return {
                'success': False,
                'error': str(e),
                'stage_timestamp': datetime.now().isoformat(),
            }
    
    def _run_backtest_stage(
        self,
        initial_capital: float,
        start_date: str,
        end_date: str
    ) -> Dict[str, Any]:
        """Run the backtesting stage."""
        try:
            self.logger.info("🎯 Running Backtest Stage...")
            
            from .backtesting.backtest_runner import BacktestRunner
            from .backtesting.base_project_algorithm import SPXCallSpreadAlgorithm
            
            # Initialize backtest runner
            runner = BacktestRunner(self.database_service)
            
            # Configure backtest
            backtest_config = {
                'initial_capital': initial_capital,
                'backtest_start': start_date,
                'backtest_end': end_date,
                **self.config
            }
            
            # Run backtest
            backtest_results = runner.run_backtest(backtest_config, SPXCallSpreadAlgorithm)
            
            return {
                'success': backtest_results.get('success', False),
                'results': backtest_results,
                'stage_timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Error in backtest stage: {e}")
            return {
                'success': False,
                'error': str(e),
                'stage_timestamp': datetime.now().isoformat(),
            }
    
    def _compile_final_results(self, pipeline_results: Dict[str, Any]) -> Dict[str, Any]:
        """Compile final results from all stages."""
        try:
            self.logger.info("📋 Compiling Final Results...")
            
            # Extract key metrics from each stage
            data_stage = pipeline_results['stages'].get('data_stage', {})
            strategy_stage = pipeline_results['stages'].get('strategy_stage', {})
            backtest_stage = pipeline_results['stages'].get('backtest_stage', {})
            
            summary = {
                'data_available': data_stage.get('data_available', False),
                'strategy_setup_success': strategy_stage.get('success', False),
                'backtest_success': backtest_stage.get('success', False),
            }
            
            # Performance summary if backtest ran
            if backtest_stage.get('success', False):
                results = backtest_stage.get('results', {})
                performance = results.get('portfolio_performance', {})
                metrics = results.get('performance_metrics', {})
                
                summary.update({
                    'final_portfolio_value': performance.get('final_value'),
                    'total_return': performance.get('total_return'),
                    'sharpe_ratio': metrics.get('sharpe_ratio'),
                    'max_drawdown': metrics.get('max_drawdown'),
                    'total_trades': results.get('trading_activity', {}).get('total_trades'),
                })
            
            return {
                'success': True,
                'summary': summary,
                'compilation_timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Error compiling results: {e}")
            return {
                'success': False,
                'error': str(e),
                'compilation_timestamp': datetime.now().isoformat(),
            }