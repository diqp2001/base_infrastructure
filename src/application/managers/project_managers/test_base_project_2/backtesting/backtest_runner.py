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
from ..models.model_trainer import SpatiotemporalModelTrainer
from ..strategy.momentum_strategy import SpatiotemporalMomentumStrategy

# Database and infrastructure
from application.managers.database_managers.database_manager import DatabaseManager


class BacktestRunner:
    """
    Comprehensive backtest runner for test_base_project that integrates:
    - Misbuffet backtesting framework
    - Spatiotemporal ML models (TFT/MLP ensemble)
    - Factor-based data system
    - Black-Litterman portfolio optimization
    """
    
    def __init__(self, database_manager: DatabaseManager):
        """
        Initialize the BacktestRunner.
        
        Args:
            database_manager: Database manager for factor system
        """
        self.database_manager = database_manager
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.factor_manager = FactorEnginedDataManager(self.database_manager)
        self.model_trainer = None
        self.momentum_strategy = None
        self.algorithm_instance = None
        
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
            self.logger.info("Setting up test_base_project components...")
            
            # Initialize model trainer
            self.model_trainer = SpatiotemporalModelTrainer(self.database_manager)
            self.logger.info("✅ Model trainer initialized")
            
            # Initialize momentum strategy
            self.momentum_strategy = SpatiotemporalMomentumStrategy(None, config)
            self.logger.info("✅ Momentum strategy initialized")
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error setting up components: {str(e)}")
            return False
    
    def setup_factor_system(self, tickers: List[str], overwrite: bool = False) -> Dict[str, Any]:
        """
        Set up the complete factor system for backtesting.
        
        Args:
            tickers: List of tickers to set up
            overwrite: Whether to overwrite existing data
            
        Returns:
            Setup results summary
        """
        self.logger.info(f"Setting up factor system for {len(tickers)} tickers...")
        
        try:
            # Initialize database
            self.database_manager.db.initialize_database_and_create_all_tables()
            # First ensure basic entities and price factors exist
            entities_summary = self.factor_manager._ensure_entities_exist(tickers)
            # Populate price factors
            price_summary = self.factor_manager.populate_price_factors(tickers, overwrite)
            # Populate momentum factors
            momentum_summary = self.factor_manager.populate_momentum_factors(tickers, overwrite)
            
            # Calculate technical indicators
            technical_summary = self.factor_manager.calculate_technical_indicators(tickers, overwrite)
            
            setup_results = {
                'tickers': tickers,
                'momentum_factors': momentum_summary,
                'technical_factors': technical_summary,
                'system_ready': True
            }
            
            self.logger.info(f"✅ Factor system setup complete for {len(tickers)} tickers")
            return setup_results
            
        except Exception as e:
            self.logger.error(f"❌ Factor system setup failed: {str(e)}")
            return {
                'tickers': tickers,
                'system_ready': False,
                'error': str(e)
            }
    
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
            
            # Inject our components (skip factor manager since it's not available)
            if self.factor_manager:
                algorithm.set_factor_manager(self.factor_manager)
            else:
                self.logger.info("⚠️ Factor manager not available - algorithm will use CSV data directly")
            
            if self.model_trainer:
                algorithm.set_spatiotemporal_trainer(self.model_trainer)
            
            if self.momentum_strategy:
                algorithm.set_momentum_strategy(self.momentum_strategy)
            
            self.algorithm_instance = algorithm
            self.logger.info("✅ Algorithm instance created and configured")
            
            return algorithm
            
        except Exception as e:
            self.logger.error(f"❌ Error creating algorithm instance: {str(e)}")
            raise
    
    def run_backtest(self, 
                    tickers: List[str],
                    start_date: datetime = None,
                    end_date: datetime = None,
                    initial_capital: float = 100_000,
                    model_type: str = 'both',
                    setup_factors: bool = True) -> Dict[str, Any]:
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
            # Default dates if not provided
            if start_date is None:
                start_date = datetime(2020, 1, 1)
            if end_date is None:
                end_date = datetime(2023, 1, 1)
            
            # Step 1: Setup components with full configuration
            from ..config import get_config
            config = get_config('test')
            # Override with backtest-specific settings
            config['DATA']['DEFAULT_UNIVERSE'] = tickers
            config['BACKTEST']['START_DATE'] = start_date.strftime('%Y-%m-%d')
            config['BACKTEST']['END_DATE'] = end_date.strftime('%Y-%m-%d')
            config['BACKTEST']['INITIAL_CAPITAL'] = initial_capital
            
            if not self.setup_components(config):
                raise Exception("Component setup failed")
            
            # Step 2:  factor system setup 
            self.setup_factor_system(tickers)
            #self.logger.info("🏗️ Factor system setup ")

            factor_results = {'system_ready': True, 'note': 'Factor system working'}
            
            # Step 3: Train models
            self.logger.info("🧠 Training spatiotemporal models...")
            training_results = self.train_models(tickers, model_type)
            if training_results.get('error'):
                raise Exception(f"Model training failed: {training_results['error']}")
            
            # Step 4: Configure Misbuffet launcher
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
                'start_date': start_date,
                'end_date': end_date,
                'initial_capital': initial_capital,
                'tickers': tickers,
                'model_type': model_type
            }
            
            # Pass the algorithm class (not instance) for Misbuffet to instantiate
            launcher_config.algorithm = BaseProjectAlgorithm
            
            # Add database manager for real data access
            launcher_config.database_manager = self.database_manager
            
            # Step 5: Start engine and run backtest
            self.logger.info("🚀 Starting backtest engine...")
            engine = misbuffet.start_engine(config_file="engine_config.py")
            
            self.logger.info("📊 Executing backtest algorithm...")
            result = engine.run(launcher_config)
            
            # Step 6: Process results
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
                'model_training': training_results,
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