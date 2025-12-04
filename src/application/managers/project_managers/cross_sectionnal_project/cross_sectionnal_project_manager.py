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
import mlflow

# Base classes
from application.services.database_service.database_service import DatabaseService
from application.managers.project_managers.project_manager import ProjectManager

# Interactive Brokers integration
from application.services.misbuffet.brokers.broker_factory import BrokerFactory, create_interactive_brokers_broker
from application.services.misbuffet.brokers.interactive_brokers_broker import InteractiveBrokersBroker

# Backtesting components
from .backtesting.backtest_runner import BacktestRunner




# Configuration
from .config import DEFAULT_CONFIG, get_config
from . import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CrossSectionnal(ProjectManager):
    """
    Enhanced Project Manager for backtesting operations.
    Implements a complete backtesting pipeline using the system with Misbuffet framework integration.
    
    Follows the exact structure of TestProjectBacktestManager but integrates
    all the advanced features from the test_base_project ecosystem.
    """
    
    def __init__(self):
        """
        Initialize the Test Base Project Manager following TestProjectBacktestManager pattern.
        """
        super().__init__()
        
        # Initialize required managers - use TEST config like test_project_backtest
        self.setup_database_service(DatabaseService(config.CONFIG_TEST['DB_TYPE']))
        self.database_service.set_ext_db()
        # Backtesting components
        self.backtest_runner = BacktestRunner(self.database_service)
        
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
        
        # Interactive Brokers broker
        self.ib_broker: Optional[InteractiveBrokersBroker] = None
        
        # MLflow tracking setup
        self.mlflow_experiment_name = "test_base_project_manager"
        self.mlflow_run = None
        self._setup_mlflow_tracking()
        
        self.logger.info("🚀 TestBaseProjectManager initialized with Misbuffet integration and MLflow tracking")

    def _setup_mlflow_tracking(self):
        """
        Set up MLflow experiment tracking for the TestBaseProjectManager.
        """
        try:
            # Set MLflow tracking URI (defaults to local mlruns directory)
            mlflow.set_tracking_uri("file:./mlruns")
            
            # Create or get existing experiment
            experiment = mlflow.get_experiment_by_name(self.mlflow_experiment_name)
            if experiment is None:
                experiment_id = mlflow.create_experiment(self.mlflow_experiment_name)
                self.logger.info(f"✅ Created MLflow experiment: {self.mlflow_experiment_name}")
            else:
                experiment_id = experiment.experiment_id
                self.logger.info(f"✅ Using existing MLflow experiment: {self.mlflow_experiment_name}")
            
            mlflow.set_experiment(self.mlflow_experiment_name)
            
        except Exception as e:
            self.logger.warning(f"⚠️ MLflow setup failed: {str(e)}")
    
    def _start_mlflow_run(self, run_name: str = None):
        """
        Start MLflow run with basic parameters.
        
        Args:
            run_name: Name for the MLflow run
        """
        try:
            if run_name is None:
                run_name = f"simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            self.mlflow_run = mlflow.start_run(run_name=run_name)
            self.logger.info(f"🎯 Started MLflow run: {run_name}")
            
            # Log basic system information
            mlflow.log_param("manager_class", self.__class__.__name__)
            mlflow.log_param("start_timestamp", datetime.now().isoformat())
            
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to start MLflow run: {str(e)}")
    
    def _end_mlflow_run(self):
        """
        End the current MLflow run.
        """
        try:
            if self.mlflow_run:
                mlflow.log_param("end_timestamp", datetime.now().isoformat())
                mlflow.end_run()
                self.logger.info("✅ Ended MLflow run")
                self.mlflow_run = None
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to end MLflow run: {str(e)}")
    
    def _log_mlflow_metrics(self, metrics: Dict[str, Any], step: int = None):
        """
        Log metrics to MLflow.
        
        Args:
            metrics: Dictionary of metric names and values
            step: Optional step number for time-series metrics
        """
        try:
            if self.mlflow_run:
                for key, value in metrics.items():
                    if isinstance(value, (int, float)):
                        mlflow.log_metric(key, value, step=step)
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to log MLflow metrics: {str(e)}")
    
    def _log_mlflow_params(self, params: Dict[str, Any]):
        """
        Log parameters to MLflow.
        
        Args:
            params: Dictionary of parameter names and values
        """
        try:
            if self.mlflow_run:
                for key, value in params.items():
                    mlflow.log_param(key, str(value))
        except Exception as e:
            self.logger.warning(f"⚠️ Failed to log MLflow params: {str(e)}")

    def run(self, 
            launch_web_interface: bool = True,
            setup_ib_connection: bool = False,
            ib_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Main run method that launches web interface and executes backtest.
        
        Follows the exact pattern of TestProjectBacktestManager.run() but with
        our enhanced spatiotemporal momentum system and Interactive Brokers integration.
        
        Args:
            
            launch_web_interface: Whether to launch web interface
            setup_ib_connection: Whether to setup Interactive Brokers connection
            ib_config: Configuration for Interactive Brokers connection
            
        Returns:
            Complete backtest results
        """
        self.logger.info("🚀 Starting TestBaseProjectManager with Misbuffet integration...")
        
        
        
        # Start MLflow tracking
        run_name = f"simulation_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self._start_mlflow_run(run_name)
        
        # Log run parameters
        run_params = {
            'launch_web_interface': launch_web_interface,
            'setup_ib_connection': setup_ib_connection,
        }
        self._log_mlflow_params(run_params)
        
        try:
            # Setup Interactive Brokers connection if requested
            if setup_ib_connection:
                self._setup_interactive_brokers_connection(ib_config)
                # Get account information and balance after connection
                self._get_ib_account_info_and_balance()
                # Extract S&P 500 data for the day
                self._extract_sp500_daily_data()
            
            """# Start web interface if requested
            if launch_web_interface and self.web_interface:
                self.web_interface.start_interface_and_open_browser()"""
            
            # Run the actual backtest with our enhanced system
            result = self._run_backtest()
            
            # Log backtest results to MLflow
            if result.get('success'):
                self._log_mlflow_metrics({
                    'final_portfolio_value': result.get('final_portfolio_value', 0),
                    'total_return': result.get('total_return', 0),
                    'sharpe_ratio': result.get('sharpe_ratio', 0),
                    'max_drawdown': result.get('max_drawdown', 0),
                    'execution_time_seconds': result.get('execution_time', 0)
                })
                mlflow.set_tag("status", "success")
                
                # Save artifacts for successful runs
                self._save_mlflow_artifacts()
            else:
                mlflow.set_tag("status", "failed")
                mlflow.set_tag("error", result.get('error', 'Unknown error'))
            
            # End MLflow run
            self._end_mlflow_run()
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ Error in run method: {str(e)}")
            
            # Log error to MLflow
            if self.mlflow_run:
                mlflow.set_tag("status", "error")
                mlflow.set_tag("error", str(e))
                self._end_mlflow_run()
            
            return {
                'error': str(e),
                'success': False,
                'timestamp': datetime.now().isoformat()
            }

    def _run_backtest(self) -> Dict[str, Any]:
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
                    'message': f'Setting up backtest...'
                })
            
            # Run the comprehensive backtest using our BacktestRunner
            result = self.backtest_runner.run_backtest()
            
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
    
    def get_stored_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get the stored IB account information.
        
        Returns:
            Previously retrieved account information or None
        """
        return getattr(self, 'ib_account_info', None)
    
    
    def _save_mlflow_artifacts(self):
        """
        Save model artifacts and results to MLflow.
        """
        try:
            if self.mlflow_run and self.results:
                # Save results as JSON artifact
                import json
                import tempfile
                
                results_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
                json.dump(self.results, results_file, default=str, indent=2)
                results_file.close()
                
                mlflow.log_artifact(results_file.name, "simulation_results")
                os.unlink(results_file.name)
                
                # Save model artifacts if available
                if self.trained_model:
                    try:
                        model_path = tempfile.mkdtemp()
                        # This would depend on how your models are structured
                        # For now, we'll just log basic model info
                        model_info = {
                            'model_type': type(self.trained_model).__name__,
                            'model_summary': str(self.trained_model)
                        }
                        model_info_file = os.path.join(model_path, 'model_info.json')
                        with open(model_info_file, 'w') as f:
                            json.dump(model_info, f, indent=2)
                        mlflow.log_artifacts(model_path, "model_info")
                    except Exception as e:
                        self.logger.warning(f"Could not save model artifacts: {e}")
                        
        except Exception as e:
            self.logger.warning(f"Failed to save MLflow artifacts: {e}")

    def __del__(self):
        """Cleanup method to ensure proper disconnection from Interactive Brokers and MLflow."""
        try:
            # End MLflow run if still active
            if self.mlflow_run:
                self._end_mlflow_run()
                
            # Disconnect from Interactive Brokers
            self.disconnect_interactive_brokers()
        except Exception:
            pass  # Ignore errors during cleanup