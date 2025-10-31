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

# Interactive Brokers integration
from application.services.misbuffet.brokers.broker_factory import BrokerFactory, create_interactive_brokers_broker
from application.services.misbuffet.brokers.interactive_brokers_broker import InteractiveBrokersBroker

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
        
        # Interactive Brokers broker
        self.ib_broker: Optional[InteractiveBrokersBroker] = None
        
        self.logger.info("🚀 TestBaseProjectManager initialized with Misbuffet integration")

    def run(self, 
            tickers: Optional[List[str]] = None,
            start_date: Optional[datetime] = None,
            end_date: Optional[datetime] = None,
            initial_capital: float = 100_000.0,
            model_type: str = 'both',
            launch_web_interface: bool = True,
            setup_ib_connection: bool = False,
            ib_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main run method that launches web interface and executes backtest.
        
        Follows the exact pattern of TestProjectBacktestManager.run() but with
        our enhanced spatiotemporal momentum system and Interactive Brokers integration.
        
        Args:
            tickers: List of tickers to backtest (defaults to config universe)
            start_date: Backtest start date
            end_date: Backtest end date
            initial_capital: Initial capital amount
            model_type: 'tft', 'mlp', or 'both'
            launch_web_interface: Whether to launch web interface
            setup_ib_connection: Whether to setup Interactive Brokers connection
            ib_config: Configuration for Interactive Brokers connection
            
        Returns:
            Complete backtest results
        """
        self.logger.info("🚀 Starting TestBaseProjectManager with Misbuffet integration...")
        
        # Use default tickers if not provided
        if tickers is None:
            tickers = get_config('test')['DATA']['DEFAULT_UNIVERSE']
        
        try:
            # Setup Interactive Brokers connection if requested
            if setup_ib_connection:
                self._setup_interactive_brokers_connection(ib_config)
                # Get account information and balance after connection
                self._get_ib_account_info_and_balance()
                # Extract S&P 500 data for the day
                self._extract_sp500_daily_data()
            
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
                            launch_web_interface: bool = True) -> Dict[str, Any]:
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
        if tickers is None:
                tickers = get_config('test')['DATA']['DEFAULT_UNIVERSE']
        
        if not run_backtest:
            # Just setup and training, no backtest
            
            
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

    def _setup_interactive_brokers_connection(self, ib_config: Optional[Dict[str, Any]] = None) -> None:
        """
        Setup Interactive Brokers connection for live trading.
        
        Args:
            ib_config: Optional configuration dictionary. Uses defaults if not provided.
        """
        self.logger.info("🔌 Setting up Interactive Brokers connection...")
        
        try:
            # Use default IB configuration if not provided
            if ib_config is None:
                ib_config = {
                    'host': '127.0.0.1',
                    'port': 7497,  # Paper trading port by default
                    'client_id': 1,
                    'paper_trading': True,
                    'timeout': 60,
                    'account_id': 'DEFAULT',
                    'enable_logging': True,
                }
            
            # Create Interactive Brokers broker instance
            self.ib_broker = create_interactive_brokers_broker(**ib_config)
            
            # Attempt to connect to TWS/Gateway
            self.logger.info(f"Connecting to IB TWS/Gateway at {ib_config['host']}:{ib_config['port']}...")
            
            if self.ib_broker.connect():
                self.logger.info("✅ Successfully connected to Interactive Brokers")
                
                # Update web interface with connection status
                if self.web_interface:
                    self.web_interface.progress_queue.put({
                        'timestamp': datetime.now().isoformat(),
                        'level': 'SUCCESS',
                        'message': f'Connected to Interactive Brokers (Paper: {ib_config["paper_trading"]})'
                    })
                
                # Log broker information
                broker_info = self.ib_broker.get_broker_specific_info()
                self.logger.info(f"IB Broker Status: {broker_info}")
                
            else:
                self.logger.error("❌ Failed to connect to Interactive Brokers")
                if self.web_interface:
                    self.web_interface.progress_queue.put({
                        'timestamp': datetime.now().isoformat(),
                        'level': 'ERROR',
                        'message': 'Failed to connect to Interactive Brokers - check TWS/Gateway is running'
                    })
                
        except Exception as e:
            self.logger.error(f"❌ Error setting up Interactive Brokers connection: {str(e)}")
            if self.web_interface:
                self.web_interface.progress_queue.put({
                    'timestamp': datetime.now().isoformat(),
                    'level': 'ERROR',
                    'message': f'IB Connection Error: {str(e)}'
                })
    
    def disconnect_interactive_brokers(self) -> None:
        """Disconnect from Interactive Brokers if connected."""
        if self.ib_broker:
            try:
                self.logger.info("Disconnecting from Interactive Brokers...")
                self.ib_broker.disconnect()
                self.ib_broker = None
                self.logger.info("✅ Disconnected from Interactive Brokers")
                
                if self.web_interface:
                    self.web_interface.progress_queue.put({
                        'timestamp': datetime.now().isoformat(),
                        'level': 'INFO',
                        'message': 'Disconnected from Interactive Brokers'
                    })
                    
            except Exception as e:
                self.logger.error(f"Error disconnecting from Interactive Brokers: {str(e)}")
    
    def get_ib_account_info(self) -> Dict[str, Any]:
        """
        Get Interactive Brokers account information.
        
        Returns:
            Account information dictionary or empty dict if not connected
        """
        if not self.ib_broker:
            return {'error': 'Not connected to Interactive Brokers'}
        
        try:
            account_info = {
                'broker_info': self.ib_broker.get_broker_specific_info(),
                'account_summary': self.ib_broker.get_account_summary(),
                'positions': self.ib_broker.get_positions_summary(),
                'market_open': self.ib_broker.is_market_open(),
                'connection_status': self.ib_broker.is_connected()
            }
            return account_info
            
        except Exception as e:
            self.logger.error(f"Error getting IB account info: {str(e)}")
            return {'error': str(e)}
    
    def _get_ib_account_info_and_balance(self) -> Dict[str, Any]:
        """
        Get Interactive Brokers account information and balance on hand after connection.
        
        Returns:
            Account information with balance details
        """
        if not self.ib_broker:
            self.logger.error("Cannot get account info - not connected to Interactive Brokers")
            return {'error': 'Not connected to Interactive Brokers'}
        
        try:
            self.logger.info("📊 Retrieving IB account information and balance...")
            
            # Get comprehensive account information
            account_info = self.get_ib_account_info()
            
            if 'error' not in account_info:
                # Extract key balance information
                account_summary = account_info.get('account_summary', {})
                
                # Log key account metrics
                cash_value = account_summary.get('TotalCashValue', {}).get('value', '0')
                net_liquidation = account_summary.get('NetLiquidation', {}).get('value', '0')
                buying_power = account_summary.get('BuyingPower', {}).get('value', '0')
                
                self.logger.info(f"💰 Account Balance Information:")
                self.logger.info(f"   Cash Value: ${cash_value}")
                self.logger.info(f"   Net Liquidation: ${net_liquidation}")
                self.logger.info(f"   Buying Power: ${buying_power}")
                
                # Update web interface with account info
                if self.web_interface:
                    self.web_interface.progress_queue.put({
                        'timestamp': datetime.now().isoformat(),
                        'level': 'SUCCESS',
                        'message': f'Account Info - Cash: ${cash_value}, Net Liq: ${net_liquidation}, Buying Power: ${buying_power}'
                    })
                
                # Store account info for later use
                self.ib_account_info = account_info
                
                return account_info
            else:
                self.logger.error(f"❌ Failed to retrieve account info: {account_info['error']}")
                if self.web_interface:
                    self.web_interface.progress_queue.put({
                        'timestamp': datetime.now().isoformat(),
                        'level': 'ERROR',
                        'message': f'Failed to get account info: {account_info["error"]}'
                    })
                return account_info
                
        except Exception as e:
            self.logger.error(f"❌ Error getting IB account info: {str(e)}")
            if self.web_interface:
                self.web_interface.progress_queue.put({
                    'timestamp': datetime.now().isoformat(),
                    'level': 'ERROR',
                    'message': f'Account info error: {str(e)}'
                })
            return {'error': str(e)}
    
    def _extract_sp500_daily_data(self) -> Dict[str, Any]:
        """
        Extract S&P 500 data for the day (open and close prices).
        
        Returns:
            S&P 500 data with open, close, high, low prices
        """
        if not self.ib_broker:
            self.logger.error("Cannot get S&P 500 data - not connected to Interactive Brokers")
            return {'error': 'Not connected to Interactive Brokers'}
        
        try:
            self.logger.info("📈 Retrieving S&P 500 data for today...")
            
            # Use SPY as S&P 500 proxy (most liquid ETF)
            sp500_symbol = 'SPY'
            
            # Get market data for SPY
            market_data = self.ib_broker.get_market_data(sp500_symbol)
            
            if market_data and 'data' in market_data:
                # Extract tick data (IB uses specific tick types)
                tick_data = market_data['data']
                
                # Map common tick types for stocks/ETFs
                # Tick Type 1 = Bid Price, Tick Type 2 = Ask Price
                # Tick Type 4 = Last Price, Tick Type 6 = High, Tick Type 7 = Low
                # Tick Type 9 = Close Price, Tick Type 14 = Open Price
                
                sp500_data = {
                    'symbol': sp500_symbol,
                    'date': datetime.now().strftime('%Y-%m-%d'),
                    'open': tick_data.get('tickType_14', 'N/A'),
                    'close': tick_data.get('tickType_9', 'N/A'),
                    'high': tick_data.get('tickType_6', 'N/A'),
                    'low': tick_data.get('tickType_7', 'N/A'),
                    'last': tick_data.get('tickType_4', 'N/A'),
                    'bid': tick_data.get('tickType_1', 'N/A'),
                    'ask': tick_data.get('tickType_2', 'N/A'),
                    'timestamp': market_data.get('timestamp', datetime.now().isoformat())
                }
                
                self.logger.info(f"📊 S&P 500 (SPY) Data for {sp500_data['date']}:")
                self.logger.info(f"   Open: {sp500_data['open']}")
                self.logger.info(f"   Close: {sp500_data['close']}")
                self.logger.info(f"   High: {sp500_data['high']}")
                self.logger.info(f"   Low: {sp500_data['low']}")
                self.logger.info(f"   Last: {sp500_data['last']}")
                
                # Update web interface with S&P 500 data
                if self.web_interface:
                    self.web_interface.progress_queue.put({
                        'timestamp': datetime.now().isoformat(),
                        'level': 'INFO',
                        'message': f'S&P 500 Data - Open: {sp500_data["open"]}, Close: {sp500_data["close"]}, Last: {sp500_data["last"]}'
                    })
                
                # Store S&P 500 data for later use
                self.sp500_data = sp500_data
                
                return sp500_data
            else:
                self.logger.warning("⚠️ No market data available for S&P 500 (SPY)")
                
                # Try alternative approach - get data from database if available
                try:
                    sp500_data = self._get_sp500_from_database()
                    if sp500_data:
                        return sp500_data
                except Exception as db_e:
                    self.logger.warning(f"Could not get S&P 500 data from database: {db_e}")
                
                if self.web_interface:
                    self.web_interface.progress_queue.put({
                        'timestamp': datetime.now().isoformat(),
                        'level': 'WARNING',
                        'message': 'S&P 500 market data not available from IB'
                    })
                
                return {'error': 'Market data not available', 'symbol': sp500_symbol}
                
        except Exception as e:
            self.logger.error(f"❌ Error extracting S&P 500 data: {str(e)}")
            if self.web_interface:
                self.web_interface.progress_queue.put({
                    'timestamp': datetime.now().isoformat(),
                    'level': 'ERROR',
                    'message': f'S&P 500 data error: {str(e)}'
                })
            return {'error': str(e)}
    
    def _get_sp500_from_database(self) -> Optional[Dict[str, Any]]:
        """
        Get S&P 500 data from database as fallback.
        
        Returns:
            S&P 500 data from database or None if not available
        """
        try:
            if not self.database_manager:
                return None
            
            # Query for SPY data from today
            today = datetime.now().strftime('%Y-%m-%d')
            
            # This would depend on your database schema
            # Placeholder implementation - adjust based on your actual schema
            query = f"""
                SELECT open_price, close_price, high_price, low_price, 
                       last_price, date
                FROM market_data 
                WHERE symbol = 'SPY' 
                AND date = '{today}' 
                ORDER BY timestamp DESC 
                LIMIT 1
            """
            
            result = self.database_manager.execute_query(query)
            
            if result and len(result) > 0:
                row = result[0]
                return {
                    'symbol': 'SPY',
                    'date': str(row.get('date', today)),
                    'open': row.get('open_price', 'N/A'),
                    'close': row.get('close_price', 'N/A'),
                    'high': row.get('high_price', 'N/A'),
                    'low': row.get('low_price', 'N/A'),
                    'last': row.get('last_price', 'N/A'),
                    'source': 'database',
                    'timestamp': datetime.now().isoformat()
                }
            
            return None
            
        except Exception as e:
            self.logger.warning(f"Could not retrieve S&P 500 data from database: {e}")
            return None
    
    def get_stored_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get the stored IB account information.
        
        Returns:
            Previously retrieved account information or None
        """
        return getattr(self, 'ib_account_info', None)
    
    def get_stored_sp500_data(self) -> Optional[Dict[str, Any]]:
        """
        Get the stored S&P 500 data.
        
        Returns:
            Previously retrieved S&P 500 data or None
        """
        return getattr(self, 'sp500_data', None)
    
    def __del__(self):
        """Cleanup method to ensure proper disconnection from Interactive Brokers."""
        try:
            self.disconnect_interactive_brokers()
        except Exception:
            pass  # Ignore errors during cleanup