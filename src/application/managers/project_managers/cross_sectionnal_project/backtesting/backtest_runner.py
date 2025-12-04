"""
BacktestRunner for test_base_project.

Orchestrates the complete Misbuffet backtesting pipeline with 
spatiotemporal momentum models and factor integration.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

# Misbuffet framework imports
from application.services.misbuffet import Misbuffet
from application.services.misbuffet.launcher.interfaces import LauncherConfiguration, LauncherMode
from application.services.misbuffet.common.interfaces import IAlgorithm
from application.services.misbuffet.common.enums import Resolution
from application.services.misbuffet.tools.optimization.portfolio.blacklitterman import BlackLittermanOptimizer

# Import config files
from ..launch_config import MISBUFFET_LAUNCH_CONFIG
from ..engine_config import MISBUFFET_ENGINE_CONFIG

# Import result handling
from application.services.misbuffet.results import (
    BacktestResultHandler, BacktestResult, PerformanceAnalyzer
)

# Test base project imports
from .base_project_algorithm import BaseProjectAlgorithm
from ..data.factor_manager import FactorEnginedDataManager
from ..models.model_trainer import ModelTrainer
from ..strategy.momentum_strategy import SpatiotemporalMomentumStrategy

# Database and infrastructure
from application.services.database_service.database_service import DatabaseService


class BacktestRunner:
    """
    Comprehensive backtest runner for test_base_project that integrates:
    - Misbuffet backtesting framework
    - Spatiotemporal ML models (TFT/MLP ensemble)
    - Factor-based data system
    - Black-Litterman portfolio optimization
    """
    
    def __init__(self, database_service: DatabaseService):
        """
        Initialize the BacktestRunner.
        
        Args:
            database_manager: Database manager for factor system
        """
        self.database_service = database_service
        self.logger = logging.getLogger(__name__)

        from ..config import get_config
        config = get_config('test')
        self.setup_components(config)

        
        
        # Results storage
        self.results = None
        self.performance_metrics = {}
        
    def setup_components(self, config: Dict[str, Any]) -> bool:
        """
        Set up all test_base_project components.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            True if setup successful, False otherwise
        """
        try:

            
            # Step 1: Setup components with full configuration
            
            # Override with backtest-specific settings
            self.tickers = config['DATA']['DEFAULT_UNIVERSE']
            self.start_date  = config['BACKTEST']['START_DATE']
            self.end_date = config['BACKTEST']['END_DATE']
            self.initial_capital = config['BACKTEST']['INITIAL_CAPITAL']
            self.model_type = config['BACKTEST']['INITIAL_CAPITAL']
            
            # Initialize components
            self.factor_manager = FactorEnginedDataManager(self.database_service)
            self.logger.info("Setting up test_base_project components...")
            
            # Initialize model trainer
            self.model_trainer = ModelTrainer(self.database_service)
            self.logger.info("✅ Model trainer initialized")
            
            # Initialize momentum strategy
            self.momentum_strategy = SpatiotemporalMomentumStrategy(None, config)
            self.logger.info("✅ Momentum strategy initialized")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error setting up components: {str(e)}")
            return False
    
    def train_models(self, tickers: List[str], model_type: str = 'both', seeds: List[int] = [42, 123]) -> Dict[str, Any]:
        """
        Train the spatiotemporal models.
        
        Args:
            tickers: List of tickers to train on
            model_type: 'tft', 'mlp', or 'both'
            seeds: Random seeds for ensemble training
            
        Returns:
            Training results
        """
        self.logger.info(f"Training spatiotemporal models ({model_type}) for {len(tickers)} tickers...")
        
        try:
            # Execute complete training pipeline
            training_results = self.model_trainer.train_complete_pipeline(
                tickers=tickers,
                model_type=model_type,
                seeds=seeds
            )
            
            if training_results and not training_results.get('error'):
                self.logger.info("✅ Model training completed successfully")
                return training_results
            else:
                error_msg = training_results.get('error', 'Unknown training error')
                self.logger.error(f"❌ Model training failed: {error_msg}")
                return {
                    'error': error_msg,
                    'success': False
                }
                
        except Exception as e:
            self.logger.error(f"❌ Error during model training: {str(e)}")
            return {
                'error': str(e),
                'success': False
            }
    
    def create_algorithm_instance(self) -> BaseProjectAlgorithm:
        """
        Create and configure the algorithm instance.
        
        Returns:
            Configured BaseProjectAlgorithm instance
        """
        try:
            # Create algorithm instance
            algorithm = BaseProjectAlgorithm()
            
            # CRITICAL: Inject dependencies IMMEDIATELY after creation and BEFORE
            # any framework interaction to prevent race conditions with on_data()
            self.logger.info("🔧 Injecting dependencies immediately after algorithm creation...")
            
            # Always inject our components - ensure they are not None
            if self.factor_manager:
                algorithm.set_factor_manager(self.factor_manager)
                self.logger.info("✅ Factor manager injected into algorithm")
            else:
                self.logger.warning("⚠️ Factor manager is None - algorithm will have limited functionality")
            
            if self.model_trainer:
                algorithm.set_spatiotemporal_trainer(self.model_trainer)
                self.logger.info("✅ Spatiotemporal trainer injected into algorithm")
            else:
                self.logger.warning("⚠️ Model trainer is None")
            
            if self.momentum_strategy:
                algorithm.set_momentum_strategy(self.momentum_strategy)
                self.logger.info("✅ Momentum strategy injected into algorithm")
            else:
                self.logger.warning("⚠️ Momentum strategy is None")
            
            # Verify all dependencies are injected before returning
            self.logger.info(f"🔍 Dependency verification - factor_manager: {algorithm.factor_manager is not None}")
            self.logger.info(f"🔍 Dependency verification - spatiotemporal_trainer: {algorithm.spatiotemporal_trainer is not None}")
            self.logger.info(f"🔍 Dependency verification - momentum_strategy: {algorithm.momentum_strategy is not None}")
            
            self.algorithm_instance = algorithm
            self.logger.info("✅ Algorithm instance created and configured with all dependencies")
            
            return algorithm
            
        except Exception as e:
            self.logger.error(f"❌ Error creating algorithm instance: {str(e)}")
            raise
    
    def run_backtest(self) -> Dict[str, Any]:
        """
        Run the complete backtest pipeline.
        
        Args:
            tickers: List of tickers to backtest
            start_date: Backtest start date
            end_date: Backtest end date  
            initial_capital: Initial capital amount
            model_type: Type of models to use
            setup_factors: Whether to setup factor system
            
        Returns:
            Complete backtest results
        """
        self.logger.info("🚀 Starting complete test_base_project backtest...")
        start_time = datetime.now()
        
        try:
            
            
            
            self.logger.info("🔧 Creating configured algorithm instance...")
            configured_algorithm = self.create_algorithm_instance()
            
            # Step 5: Configure Misbuffet launcher
            self.logger.info("🔧 Configuring Misbuffet framework...")
            
            # Launch Misbuffet with config file path (not dictionary)
            misbuffet = Misbuffet.launch(config_file="launch_config.py")
            
            # Configure engine with LauncherConfiguration
            launcher_config = LauncherConfiguration(
                mode=LauncherMode.BACKTESTING,
                algorithm_type_name="BaseProjectAlgorithm",
                algorithm_location=__file__,
                data_folder="./downloads",
                environment="backtesting",
                live_mode=False,
                debugging=True
            )
            
            # Override with custom config values
            launcher_config.custom_config = {
                'start_date': self.start_date,
                'end_date': self.end_date,
                'initial_capital': self.initial_capital,
                'tickers': self.tickers,
                'model_type': self.model_type
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
                    'tickers': self.tickers,
                    'start_date': self.start_date,
                    'end_date': self.end_date,
                    'initial_capital': self.initial_capital,
                    'model_type': self.model_type
                },
                #'factor_system': factor_results if setup_factors else None,
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
            return backtest_summary
            
        except Exception as e:
            end_time = datetime.now()
            elapsed_time = (end_time - start_time).total_seconds()
            
            error_summary = {
                'error': str(e),
                'execution_time': elapsed_time,
                'success': False,
                'timestamp': end_time.isoformat()
            }
            
            self.logger.error(f"❌ Backtest failed: {str(e)}")
            return error_summary
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get comprehensive performance metrics from the backtest.
        
        Returns:
            Performance metrics dictionary
        """
        if not self.results or not self.results.get('success'):
            return {'error': 'No successful backtest results available'}
        
        try:
            # Calculate performance metrics from results
            metrics = {
                'backtest_duration': self.results.get('execution_time', 0),
                'model_training_success': bool(self.results.get('model_training', {}).get('success', False)),
                'factor_system_ready': bool(self.results.get('factor_system', {}).get('system_ready', False)),
                'misbuffet_summary': self.results.get('misbuffet_result', {}),
                'configuration': self.results.get('backtest_config', {})
            }
            
            return metrics
            
        except Exception as e:
            self.logger.error(f"Error calculating performance metrics: {str(e)}")
            return {'error': str(e)}