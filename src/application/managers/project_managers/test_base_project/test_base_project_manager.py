"""
Test Base Project Manager - Main orchestrator class.

Combines spatiotemporal momentum modeling, factor creation, and backtesting
into a unified trading system pipeline following the exact structure of
TestProjectBacktestManager.

This manager integrates the best aspects of:
- spatiotemporal_momentum_manager (ML models and feature engineering)
- test_project_factor_creation (factor system and data management)  
- test_project_backtest (backtesting engine and web interface)
"""

import os
import time
import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

# Base classes
from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.project_managers.project_manager import ProjectManager

# Backtesting components
from .backtesting.backtest_runner import BacktestRunner
from .backtesting.base_project_algorithm import BaseProjectAlgorithm

# Data components
from .data.data_loader import SpatiotemporalDataLoader
from .data.feature_engineer import SpatiotemporalFeatureEngineer
from .data.factor_manager import FactorEnginedDataManager

# Model components  
from .models.spatiotemporal_model import HybridSpatiotemporalModel
from .models.model_trainer import SpatiotemporalModelTrainer

# Strategy components
from .strategy.momentum_strategy import SpatiotemporalMomentumStrategy
from .strategy.portfolio_optimizer import HybridPortfolioOptimizer
from .strategy.signal_generator import MLSignalGenerator

# Configuration
from .config import DEFAULT_CONFIG, get_config
from . import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestBaseProjectManager(ProjectManager):
    """
    Enhanced Project Manager for backtesting operations.
    Implements a complete backtesting pipeline using the hybrid spatiotemporal
    momentum system with Misbuffet framework integration.
    
    Follows the exact structure of TestProjectBacktestManager but integrates
    all the advanced features from the test_base_project ecosystem.
    """
    
    def __init__(self):
        """
        Initialize the Test Base Project Manager following TestProjectBacktestManager pattern.
        """
        super().__init__()
        
        # Initialize required managers - use TEST config like test_project_backtest
        self.setup_database_manager(DatabaseManager(config.CONFIG_TEST['DB_TYPE']))
        
        # Initialize core components
        self.data_loader = SpatiotemporalDataLoader(self.database_manager)
        self.feature_engineer = SpatiotemporalFeatureEngineer(self.database_manager)
        self.factor_manager = FactorEnginedDataManager(self.database_manager)
        self.model_trainer = SpatiotemporalModelTrainer(self.database_manager)
        self.portfolio_optimizer = HybridPortfolioOptimizer(get_config('test'))
        
        # Backtesting components
        self.backtest_runner = BacktestRunner(self.database_manager)
        self.algorithm = None
        self.results = None
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Web interface manager
        try:
            from application.services.misbuffet.web.web_interface import WebInterfaceManager
            self.web_interface = WebInterfaceManager()
        except ImportError:
            self.logger.warning("Web interface not available")
            self.web_interface = None
        
        # Runtime state
        self.trained_model = None
        self.strategy = None
        self.signal_generator = None
        self.pipeline_results = {}
        
        self.logger.info("🚀 TestBaseProjectManager initialized with Misbuffet integration")

    def run(self, 
            tickers: Optional[List[str]] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            initial_capital: float = 100_000.0,
            model_type: str = 'both',
            launch_web_interface: bool = True) -> Dict[str, Any]:
        """
        Main run method that launches web interface and executes backtest.
        
        Follows the exact pattern of TestProjectBacktestManager.run() but with
        our enhanced spatiotemporal momentum system.
        
        Args:
            tickers: List of tickers to backtest (defaults to config universe)
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Initial capital amount
            model_type: 'tft', 'mlp', or 'both'
            launch_web_interface: Whether to launch web interface
            
        Returns:
            Complete backtest results
        """
        self.logger.info("🚀 Starting TestBaseProjectManager with Misbuffet integration...")
        
        # Use default tickers if not provided
        if tickers is None:
            tickers = get_config('test')['DATA']['DEFAULT_UNIVERSE']
        
        try:
            # Start web interface if requested
            if launch_web_interface and self.web_interface:
                self.web_interface.start_interface_and_open_browser()
            
            # Run the actual backtest with our enhanced system
            return self._run_backtest(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                model_type=model_type
            )
            
        except Exception as e:
            self.logger.error(f"❌ Error in run method: {str(e)}")
            return {
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }

    def _run_backtest(self,
                     tickers: List[str],
                     start_date: Optional[datetime] = None,
                     end_date: Optional[datetime] = None,
                     initial_capital: float = 100_000.0,
                     model_type: str = 'both') -> Dict[str, Any]:
        """
        Execute the actual backtest with progress logging.
        
        Integrates our spatiotemporal momentum system with the Misbuffet framework.
        """
        self.logger.info("🏗️ Setting up enhanced factor system...")
        
        # Send initial progress message
        if self.web_interface:
            self.web_interface.progress_queue.put({
                'timestamp': datetime.now().isoformat(),
                'level': 'INFO',
                'message': 'Starting TestBaseProjectManager with hybrid ML system...'
            })

        try:
            # Send progress updates during setup
            if self.web_interface:
                self.web_interface.progress_queue.put({
                    'timestamp': datetime.now().isoformat(),
                    'level': 'INFO',
                    'message': f'Setting up factor system for {len(tickers)} tickers with ML integration...'
                })
            
            # Run the comprehensive backtest using our BacktestRunner
            result = self.backtest_runner.run_backtest(
                tickers=tickers,
                start_date=start_date,
                end_date=end_date,
                initial_capital=initial_capital,
                model_type=model_type,
                setup_factors=True
            )
            
            if self.web_interface:
                if result.get('success'):
                    self.web_interface.progress_queue.put({
                        'timestamp': datetime.now().isoformat(),
                        'level': 'SUCCESS',
                        'message': f'Enhanced backtest completed successfully! Execution time: {result.get("execution_time", 0):.2f}s'
                    })
                else:
                    self.web_interface.progress_queue.put({
                        'timestamp': datetime.now().isoformat(),
                        'level': 'ERROR',
                        'message': f'Enhanced backtest failed: {result.get("error", "Unknown error")}'
                    })
            
            self.results = result
            return result
            
        except Exception as e:
            self.logger.error(f"Error running enhanced backtest: {e}")
            
            if self.web_interface:
                self.web_interface.progress_queue.put({
                    'timestamp': datetime.now().isoformat(),
                    'level': 'ERROR',
                    'message': f'Enhanced backtest failed: {str(e)}'
                })
            
            return {
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }

    def run_misbuffet_backtest(self,
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None,
                              universe: Optional[List[str]] = None,
                              initial_capital: float = 100_000.0,
                              model_type: str = 'both',
                              launch_web_interface: bool = False) -> Dict[str, Any]:
        """
        Run Misbuffet backtest with our enhanced spatiotemporal momentum system.
        
        Args:
            start_date: Backtest start date
            end_date: Backtest end date
            universe: List of tickers to trade
            initial_capital: Starting capital
            model_type: 'tft', 'mlp', or 'both'
            launch_web_interface: Whether to launch web interface
            
        Returns:
            Backtest results with performance metrics
        """
        return self.run(
            tickers=universe,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            model_type=model_type,
            launch_web_interface=launch_web_interface
        )

    def run_web_interface_backtest(self) -> Dict[str, Any]:
        """
        Run backtest with web interface monitoring (matching test_project_backtest).
        
        Returns:
            Backtest results
        """
        return self.run(launch_web_interface=True)

    def setup_factor_system(self, 
                          tickers: Optional[List[str]] = None,
                          overwrite: bool = False) -> Dict[str, Any]:
        """
        Set up the complete factor system with entities and factor definitions.
        
        Args:
            tickers: List of tickers to set up (uses config default if None)
            overwrite: Whether to overwrite existing factor values
            
        Returns:
            Summary of factor system setup
        """
        self.logger.info("🏗️ Setting up enhanced factor system...")
        start_time = time.time()
        
        if tickers is None:
            tickers = get_config('test')['DATA']['DEFAULT_UNIVERSE']
        
        try:
            # Use the BacktestRunner's factor system setup
            setup_results = self.backtest_runner.setup_factor_system(tickers, overwrite)
            
            end_time = time.time()
            elapsed = end_time - start_time
            setup_results['total_setup_time'] = elapsed
            
            self.logger.info(f"✅ Enhanced factor system setup complete in {elapsed:.2f}s")
            return setup_results
            
        except Exception as e:
            self.logger.error(f"❌ Enhanced factor system setup failed: {str(e)}")
            return {
                'tickers': tickers,
                'system_ready': False,
                'error': str(e),
                'total_setup_time': time.time() - start_time
            }
    
    def train_spatiotemporal_models(self, 
                                  tickers: Optional[List[str]] = None,
                                  model_type: str = 'both',
                                  seeds: List[int] = [42, 123]) -> Dict[str, Any]:
        """
        Train spatiotemporal models using the complete pipeline.
        
        Args:
            tickers: List of tickers to train on
            model_type: 'tft', 'mlp', or 'both'
            seeds: Random seeds for ensemble training
            
        Returns:
            Complete training results
        """
        self.logger.info("🧠 Training enhanced spatiotemporal models...")
        
        if tickers is None:
            tickers = get_config('test')['DATA']['DEFAULT_UNIVERSE']
        
        try:
            # Use the BacktestRunner's model training
            training_results = self.backtest_runner.train_models(tickers, model_type, seeds)
            
            if not training_results.get('error'):
                self.trained_model = self.model_trainer.get_trained_model()
                self.logger.info("✅ Enhanced model training completed successfully")
            else:
                self.logger.error(f"❌ Enhanced model training failed: {training_results['error']}")
            
            return training_results
            
        except Exception as e:
            self.logger.error(f"❌ Enhanced model training error: {str(e)}")
            return {
                'error': str(e),
                'success': False
            }

    def get_comprehensive_results(self) -> Dict[str, Any]:
        """
        Get comprehensive results from all pipeline stages.
        
        Returns:
            Complete results dictionary with factor system, models, and backtest results
        """
        performance_metrics = {}
        if self.backtest_runner:
            performance_metrics = self.backtest_runner.get_performance_metrics()
        
        return {
            'pipeline_results': self.pipeline_results,
            'backtest_results': self.results,
            'performance_metrics': performance_metrics,
            'model_summary': self.trained_model.get_model_summary() if self.trained_model else None,
            'strategy_performance': self.strategy.get_signal_history() if self.strategy else [],
            'system_config': get_config('test'),
            'timestamp': datetime.now().isoformat()
        }

    def run_complete_pipeline(self,
                            tickers: Optional[List[str]] = None,
                            model_type: str = 'both',
                            seeds: List[int] = [42, 123],
                            run_backtest: bool = True,
                            launch_web_interface: bool = False) -> Dict[str, Any]:
        """
        Run the complete end-to-end pipeline with web interface option.
        
        Args:
            tickers: List of tickers to process
            model_type: Type of models to train
            seeds: Random seeds for training
            run_backtest: Whether to run backtest after training
            launch_web_interface: Whether to launch web interface
            
        Returns:
            Complete pipeline results
        """
        self.logger.info("🚀 Starting complete enhanced Test Base Project pipeline...")
        
        if not run_backtest:
            # Just setup and training, no backtest
            if tickers is None:
                tickers = get_config('test')['DATA']['DEFAULT_UNIVERSE']
            
            # Setup factor system
            factor_results = self.setup_factor_system(tickers, overwrite=False)
            
            # Train models
            training_results = self.train_spatiotemporal_models(tickers, model_type, seeds)
            
            return {
                'factor_system': factor_results,
                'model_training': training_results,
                'backtest': None,
                'success': not training_results.get('error'),
                'timestamp': datetime.now().isoformat()
            }
        else:
            # Run complete pipeline with backtest
            return self.run(
                tickers=tickers,
                model_type=model_type,
                launch_web_interface=launch_web_interface
            )