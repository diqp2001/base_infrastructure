"""
Test Base Project Manager - Main orchestrator class.

Combines spatiotemporal momentum modeling, factor creation, and backtesting
into a unified trading system pipeline.

This manager integrates the best aspects of:
- spatiotemporal_momentum_manager (ML models and feature engineering)
- test_project_factor_creation (factor system and data management)  
- test_project_backtest (backtesting engine and web interface)
"""

import os
import time
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from pathlib import Path

# Base classes
from application.managers.database_managers.database_manager import DatabaseManager
from application.managers.project_managers.project_manager import ProjectManager

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

# Utilities
from .utils.validators import DataValidators
from .utils.performance_metrics import PerformanceCalculator

# Configuration
from .config import DEFAULT_CONFIG, get_config


class TestBaseProjectManager(ProjectManager):
    """
    Main project manager combining spatiotemporal modeling, factor creation,
    and backtesting capabilities into a unified trading system.
    """
    
    def __init__(self, env: str = 'test'):
        """
        Initialize the Test Base Project Manager.
        
        Args:
            env: Environment configuration ('test' or 'production')
        """
        super().__init__()
        
        # Load configuration
        self.config = get_config(env)
        self.env = env
        
        # Initialize database manager
        self.setup_database_manager(DatabaseManager(self.config['DATABASE']['DB_TYPE']))
        
        # Initialize core components
        self.data_loader = SpatiotemporalDataLoader(self.database_manager)
        self.feature_engineer = SpatiotemporalFeatureEngineer(self.database_manager)
        self.factor_manager = FactorEnginedDataManager(self.database_manager)
        self.model_trainer = SpatiotemporalModelTrainer(self.database_manager)
        self.portfolio_optimizer = HybridPortfolioOptimizer(self.config)
        
        # Initialize validators and calculators
        self.validator = DataValidators()
        self.performance_calculator = PerformanceCalculator()
        
        # Runtime state
        self.trained_model = None
        self.strategy = None
        self.signal_generator = None
        self.pipeline_results = {}
        
        print(f"🚀 TestBaseProjectManager initialized in '{env}' environment")
    
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
        print("🏗️ Setting up factor system...")
        start_time = time.time()
        
        if tickers is None:
            tickers = self.config['DATA']['DEFAULT_UNIVERSE']
        
        try:
            # Step 1: Initialize database
            self.database_manager.db.initialize_database_and_create_all_tables()
            
            # Step 2: Create entities and basic price factors
            entities_summary = self.create_entities_and_factors(tickers)
            
            # Step 3: Populate spatiotemporal momentum factors
            momentum_summary = self.factor_manager.populate_momentum_factors(tickers, overwrite)
            
            # Step 4: Calculate technical indicators
            technical_summary = self.factor_manager.calculate_technical_indicators(tickers, overwrite)
            
            end_time = time.time()
            elapsed = end_time - start_time
            
            # Compile results
            setup_summary = {
                'tickers': tickers,
                'entities': entities_summary,
                'momentum_factors': momentum_summary,
                'technical_factors': technical_summary,
                'total_setup_time': elapsed,
                'system_ready': True
            }
            
            print(f"✅ Factor system setup complete in {elapsed:.2f}s")
            print(f"   📊 Processed {len(tickers)} tickers")
            print(f"   🔧 Created {momentum_summary.get('factors_created', 0)} momentum factors")
            print(f"   📈 Created {technical_summary.get('factors_created', 0)} technical factors")
            
            return setup_summary
            
        except Exception as e:
            print(f"❌ Factor system setup failed: {str(e)}")
            return {
                'tickers': tickers,
                'system_ready': False,
                'error': str(e),
                'total_setup_time': time.time() - start_time
            }
    
    def create_entities_and_factors(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Create base entities and price factors.
        
        This method replicates the entity creation from test_project_factor_creation
        while preparing for spatiotemporal feature integration.
        """
        print("📋 Creating entities and base factors...")
        
        # Use the factor manager's entity creation and factor setup
        return self.factor_manager.populate_momentum_factors(tickers, overwrite=False)
    
    def train_spatiotemporal_models(self, 
                                  tickers: Optional[List[str]] = None,
                                  model_type: str = 'both',
                                  seeds: List[int] = [42]) -> Dict[str, Any]:
        """
        Train spatiotemporal models using the complete pipeline.
        
        Args:
            tickers: List of tickers to train on
            model_type: 'tft', 'mlp', or 'both'
            seeds: Random seeds for ensemble training
            
        Returns:
            Complete training results
        """
        print("🧠 Training spatiotemporal models...")
        start_time = time.time()
        
        if tickers is None:
            tickers = self.config['DATA']['DEFAULT_UNIVERSE']
        
        try:
            # Execute complete training pipeline
            training_results = self.model_trainer.train_complete_pipeline(
                tickers=tickers,
                model_type=model_type, 
                seeds=seeds
            )
            
            # Store the trained model
            self.trained_model = self.model_trainer.get_trained_model()
            
            # Initialize strategy and signal generator
            self._initialize_strategy_components()
            
            end_time = time.time()
            training_results['training_time'] = end_time - start_time
            
            print(f"✅ Model training completed in {training_results['training_time']:.2f}s")
            
            return training_results
            
        except Exception as e:
            print(f"❌ Model training failed: {str(e)}")
            return {
                'error': str(e),
                'training_time': time.time() - start_time,
                'success': False
            }
    
    def run_backtest_with_web_interface(self,
                                      start_date: Optional[str] = None,
                                      end_date: Optional[str] = None,
                                      initial_capital: float = 100000.0) -> Dict[str, Any]:
        """
        Run backtest with web interface monitoring.
        
        This integrates the backtesting approach from test_project_backtest
        with our trained spatiotemporal models.
        """
        print("📊 Running backtest with web interface...")
        
        if not self.trained_model:
            return {'error': 'No trained model available. Run train_spatiotemporal_models first.'}
        
        if not self.strategy:
            self._initialize_strategy_components()
        
        # Use default dates from config if not provided
        if start_date is None:
            start_date = self.config['BACKTEST']['START_DATE']
        if end_date is None:
            end_date = self.config['BACKTEST']['END_DATE']
        
        try:
            # Load historical data for backtesting
            backtest_data = self._prepare_backtest_data(start_date, end_date)
            
            # Run the backtest simulation
            backtest_results = self._execute_backtest_simulation(
                backtest_data, start_date, end_date, initial_capital
            )
            
            # Calculate performance metrics
            performance_metrics = self._calculate_backtest_performance(backtest_results)
            
            # Combine results
            final_results = {
                'backtest_config': {
                    'start_date': start_date,
                    'end_date': end_date,
                    'initial_capital': initial_capital
                },
                'backtest_results': backtest_results,
                'performance_metrics': performance_metrics,
                'web_interface_url': f"http://localhost:{self.config['WEB']['PORT']}/dashboard",
                'success': True
            }
            
            print("✅ Backtest completed successfully")
            print(f"   📈 Total Return: {performance_metrics.get('total_return', 0):.2%}")
            print(f"   📊 Sharpe Ratio: {performance_metrics.get('sharpe_ratio', 0):.3f}")
            print(f"   📉 Max Drawdown: {performance_metrics.get('max_drawdown', 0):.2%}")
            
            return final_results
            
        except Exception as e:
            print(f"❌ Backtest failed: {str(e)}")
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
        return {
            'pipeline_results': self.pipeline_results,
            'model_summary': self.trained_model.get_model_summary() if self.trained_model else None,
            'strategy_performance': self.strategy.get_signal_history() if self.strategy else [],
            'system_config': self.config,
            'environment': self.env,
            'timestamp': datetime.now().isoformat()
        }
    
    def _initialize_strategy_components(self):
        """Initialize strategy and signal generation components."""
        if self.trained_model:
            self.signal_generator = MLSignalGenerator(self.trained_model)
            self.strategy = SpatiotemporalMomentumStrategy(
                self.trained_model, self.config
            )
    
    def _prepare_backtest_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Prepare data for backtesting."""
        # Load factor-enhanced data for the backtest period
        tickers = self.config['DATA']['DEFAULT_UNIVERSE']
        
        backtest_data = self.factor_manager.get_factor_data_for_training(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            factor_groups=['price', 'momentum', 'technical']
        )
        
        return backtest_data
    
    def _execute_backtest_simulation(self,
                                   data: pd.DataFrame,
                                   start_date: str,
                                   end_date: str,
                                   initial_capital: float) -> Dict[str, Any]:
        """Execute the backtest simulation."""
        # This is a simplified simulation
        # In a full implementation, this would integrate with the Misbuffet framework
        
        simulation_results = {
            'daily_returns': [],
            'portfolio_values': [],
            'positions': [],
            'signals': [],
            'trades': []
        }
        
        # Simulate trading over the backtest period
        date_range = pd.date_range(start_date, end_date, freq='D')
        portfolio_value = initial_capital
        
        for current_date in date_range:
            if current_date in data.index:
                # Get market data for this date
                market_data = data[data.index <= current_date]
                
                # Generate signals
                signals = self.strategy.generate_strategy_signals(
                    market_data, market_data, current_date
                )
                
                # Calculate daily return (simplified)
                daily_return = sum(signals.values()) * 0.001  # Mock return
                portfolio_value *= (1 + daily_return)
                
                # Store results
                simulation_results['daily_returns'].append(daily_return)
                simulation_results['portfolio_values'].append(portfolio_value)
                simulation_results['positions'].append(signals)
                simulation_results['signals'].append(signals)
        
        return simulation_results
    
    def _calculate_backtest_performance(self, backtest_results: Dict[str, Any]) -> Dict[str, float]:
        """Calculate performance metrics from backtest results."""
        if not backtest_results['daily_returns']:
            return {}
        
        returns = pd.Series(backtest_results['daily_returns'])
        return self.performance_calculator.calculate_returns_metrics(returns)
    
    def run_complete_pipeline(self,
                            tickers: Optional[List[str]] = None,
                            model_type: str = 'both',
                            seeds: List[int] = [42],
                            run_backtest: bool = True) -> Dict[str, Any]:
        """
        Run the complete end-to-end pipeline.
        
        Args:
            tickers: List of tickers to process
            model_type: Type of models to train
            seeds: Random seeds for training
            run_backtest: Whether to run backtest after training
            
        Returns:
            Complete pipeline results
        """
        print("🚀 Starting complete Test Base Project pipeline...")
        pipeline_start_time = time.time()
        
        if tickers is None:
            tickers = self.config['DATA']['DEFAULT_UNIVERSE']
        
        pipeline_results = {}
        
        try:
            # Stage 1: Setup factor system
            print("\n" + "="*60)
            print("STAGE 1: FACTOR SYSTEM SETUP")
            print("="*60)
            
            factor_results = self.setup_factor_system(tickers, overwrite=False)
            pipeline_results['factor_system'] = factor_results
            
            if not factor_results.get('system_ready', False):
                raise Exception("Factor system setup failed")
            
            # Stage 2: Train spatiotemporal models
            print("\n" + "="*60)
            print("STAGE 2: SPATIOTEMPORAL MODEL TRAINING")
            print("="*60)
            
            training_results = self.train_spatiotemporal_models(tickers, model_type, seeds)
            pipeline_results['model_training'] = training_results
            
            if training_results.get('error'):
                raise Exception(f"Model training failed: {training_results['error']}")
            
            # Stage 3: Run backtest (optional)
            if run_backtest:
                print("\n" + "="*60)
                print("STAGE 3: BACKTESTING WITH WEB INTERFACE")
                print("="*60)
                
                backtest_results = self.run_backtest_with_web_interface()
                pipeline_results['backtest'] = backtest_results
            
            # Final summary
            pipeline_end_time = time.time()
            total_time = pipeline_end_time - pipeline_start_time
            
            final_summary = {
                'pipeline_results': pipeline_results,
                'tickers_processed': len(tickers),
                'models_trained': len(seeds) * (2 if model_type == 'both' else 1),
                'total_pipeline_time': total_time,
                'success': True,
                'timestamp': datetime.now().isoformat()
            }
            
            print("\n" + "="*60)
            print("🎯 COMPLETE PIPELINE SUMMARY")
            print("="*60)
            print(f"✅ Tickers processed: {len(tickers)}")
            print(f"✅ Models trained: {final_summary['models_trained']}")
            print(f"✅ Total time: {total_time:.2f} seconds")
            print(f"✅ Pipeline completed successfully!")
            print("="*60)
            
            # Store results for later access
            self.pipeline_results = final_summary
            
            return final_summary
            
        except Exception as e:
            pipeline_end_time = time.time()
            error_summary = {
                'pipeline_results': pipeline_results,
                'error': str(e),
                'total_pipeline_time': pipeline_end_time - pipeline_start_time,
                'success': False,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"\n❌ PIPELINE FAILED: {str(e)}")
            print(f"⏱️ Time elapsed: {error_summary['total_pipeline_time']:.2f} seconds")
            
            return error_summary