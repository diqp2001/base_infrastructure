"""
BacktestRunner: Orchestrates the execution of BaseProject backtests using
the Misbuffet framework with factor integration and ML models.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Import Misbuffet framework components
from application.services.misbuffet import Misbuffet
from application.services.misbuffet.launcher.interfaces import LauncherConfiguration, LauncherMode
from application.services.misbuffet.results import BacktestResultHandler, BacktestResult, PerformanceAnalyzer

# Import project components
from .base_project_algorithm import BaseProjectAlgorithm
from .launch_config import MISBUFFET_LAUNCH_CONFIG
from .engine_config import MISBUFFET_ENGINE_CONFIG
from ..config import Config

# Configure logging
logger = logging.getLogger(__name__)


class BacktestRunner:
    """
    Runs backtests for the BaseProject hybrid trading system.
    
    Integrates Misbuffet framework with:
    - Factor data system
    - ML model training and prediction
    - Portfolio optimization
    - Performance analysis
    """
    
    def __init__(self, database_manager=None, web_interface=None):
        """
        Initialize the backtest runner.
        
        Args:
            database_manager: Database manager for factor data access
            web_interface: Optional web interface for progress reporting
        """
        self.database_manager = database_manager
        self.web_interface = web_interface
        self.config = Config()
        
        # Backtest state
        self.misbuffet = None
        self.engine = None
        self.result = None
        
        logger.info("BacktestRunner initialized")

    def run_backtest(self,
                    start_date: Optional[datetime] = None,
                    end_date: Optional[datetime] = None,
                    initial_capital: float = 100_000,
                    universe: Optional[list] = None) -> Dict[str, Any]:
        """
        Execute a complete backtest.
        
        Args:
            start_date: Backtest start date (defaults to config)
            end_date: Backtest end date (defaults to config)
            initial_capital: Starting capital amount
            universe: List of tickers to trade (defaults to config)
            
        Returns:
            Dictionary containing backtest results and performance metrics
        """
        try:
            self._send_progress("Starting BaseProject backtest...")
            
            # Configure backtest parameters
            self._configure_backtest_parameters(start_date, end_date, initial_capital, universe)
            
            # Initialize Misbuffet framework
            self._initialize_misbuffet()
            
            # Configure and start engine
            self._configure_and_start_engine()
            
            # Run the backtest
            self._execute_backtest()
            
            # Analyze and format results
            results = self._analyze_results()
            
            self._send_progress("Backtest completed successfully!")
            logger.info("Backtest execution completed")
            
            return results
            
        except Exception as e:
            error_msg = f"Backtest execution failed: {str(e)}"
            self._send_progress(error_msg, level='ERROR')
            logger.error(error_msg)
            raise

    def _configure_backtest_parameters(self,
                                     start_date: Optional[datetime],
                                     end_date: Optional[datetime],
                                     initial_capital: float,
                                     universe: Optional[list]):
        """Configure backtest parameters."""
        # Update engine config with custom parameters
        if start_date:
            MISBUFFET_ENGINE_CONFIG['start_date'] = start_date
        if end_date:
            MISBUFFET_ENGINE_CONFIG['end_date'] = end_date
        if initial_capital:
            MISBUFFET_ENGINE_CONFIG['initial_capital'] = initial_capital
        if universe:
            MISBUFFET_ENGINE_CONFIG['universe'] = universe
            
        logger.info(f"Configured backtest: {MISBUFFET_ENGINE_CONFIG['start_date']} to "
                   f"{MISBUFFET_ENGINE_CONFIG['end_date']}, capital: ${initial_capital:,.0f}")

    def _initialize_misbuffet(self):
        """Initialize the Misbuffet framework."""
        try:
            self._send_progress("Initializing Misbuffet framework...")
            
            # Launch Misbuffet with custom config
            self.misbuffet = Misbuffet.launch(config_file=None, config_dict=MISBUFFET_LAUNCH_CONFIG)
            
            logger.info("Misbuffet framework initialized successfully")
            
        except Exception as e:
            raise Exception(f"Failed to initialize Misbuffet: {e}")

    def _configure_and_start_engine(self):
        """Configure and start the backtesting engine."""
        try:
            self._send_progress("Configuring backtesting engine...")
            
            # Create launcher configuration
            launcher_config = LauncherConfiguration(
                mode=LauncherMode.BACKTESTING,
                algorithm_type_name="BaseProjectAlgorithm",
                algorithm_location=__file__,
                data_folder=MISBUFFET_ENGINE_CONFIG.get("data_folder", "./downloads"),
                environment="backtesting",
                live_mode=False,
                debugging=True
            )
            
            # Add custom configuration
            launcher_config.custom_config = MISBUFFET_ENGINE_CONFIG
            launcher_config.algorithm = BaseProjectAlgorithm
            
            # Add database manager for factor data access
            if self.database_manager:
                launcher_config.database_manager = self.database_manager
            
            # Start the engine
            self._send_progress("Starting backtesting engine...")
            self.engine = self.misbuffet.start_engine(config_dict=MISBUFFET_ENGINE_CONFIG)
            
            logger.info("Backtesting engine started successfully")
            
        except Exception as e:
            raise Exception(f"Failed to configure/start engine: {e}")

    def _execute_backtest(self):
        """Execute the actual backtest."""
        try:
            self._send_progress("Executing backtest algorithm...")
            
            # Create launcher configuration for execution
            launcher_config = LauncherConfiguration(
                mode=LauncherMode.BACKTESTING,
                algorithm_type_name="BaseProjectAlgorithm",
                algorithm_location=__file__,
                environment="backtesting",
                live_mode=False
            )
            
            launcher_config.algorithm = BaseProjectAlgorithm
            launcher_config.custom_config = MISBUFFET_ENGINE_CONFIG
            
            if self.database_manager:
                launcher_config.database_manager = self.database_manager
            
            # Run the backtest
            self.result = self.engine.run(launcher_config)
            
            logger.info("Backtest execution completed")
            
        except Exception as e:
            raise Exception(f"Failed to execute backtest: {e}")

    def _analyze_results(self) -> Dict[str, Any]:
        """Analyze backtest results and create comprehensive report."""
        if not self.result:
            return {"error": "No backtest results available"}
        
        try:
            self._send_progress("Analyzing backtest results...")
            
            # Basic result extraction
            basic_results = {
                'backtest_completed': True,
                'start_date': MISBUFFET_ENGINE_CONFIG.get('start_date'),
                'end_date': MISBUFFET_ENGINE_CONFIG.get('end_date'),
                'initial_capital': MISBUFFET_ENGINE_CONFIG.get('initial_capital'),
                'universe': MISBUFFET_ENGINE_CONFIG.get('universe'),
                'algorithm': 'BaseProjectAlgorithm'
            }
            
            # Extract performance metrics if available
            if hasattr(self.result, 'summary'):
                basic_results['summary'] = self.result.summary()
            
            if hasattr(self.result, 'get_performance_metrics'):
                basic_results['performance_metrics'] = self.result.get_performance_metrics()
            
            # Add factor integration status
            basic_results['factor_integration'] = {
                'enabled': True,
                'factor_groups': MISBUFFET_ENGINE_CONFIG.get('factor_system', {}).get('factor_groups', []),
                'ml_models_enabled': MISBUFFET_ENGINE_CONFIG.get('ml_models', {}).get('tft_enabled', False)
            }
            
            # Use PerformanceAnalyzer if available
            try:
                analyzer = PerformanceAnalyzer()
                if hasattr(analyzer, 'analyze'):
                    detailed_analysis = analyzer.analyze(self.result)
                    basic_results['detailed_analysis'] = detailed_analysis
            except Exception as e:
                logger.warning(f"Could not perform detailed analysis: {e}")
            
            logger.info("Results analysis completed")
            return basic_results
            
        except Exception as e:
            logger.error(f"Error analyzing results: {e}")
            return {
                "error": f"Failed to analyze results: {e}",
                "raw_result": str(self.result) if self.result else None
            }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a concise performance summary."""
        if not self.result:
            return {"error": "No results available"}
        
        try:
            # Extract key performance metrics
            summary = {}
            
            if hasattr(self.result, 'total_return'):
                summary['total_return'] = self.result.total_return
            
            if hasattr(self.result, 'sharpe_ratio'):
                summary['sharpe_ratio'] = self.result.sharpe_ratio
                
            if hasattr(self.result, 'max_drawdown'):
                summary['max_drawdown'] = self.result.max_drawdown
            
            if hasattr(self.result, 'volatility'):
                summary['volatility'] = self.result.volatility
                
            # Add backtest metadata
            summary.update({
                'algorithm': 'BaseProjectAlgorithm',
                'universe_size': len(MISBUFFET_ENGINE_CONFIG.get('universe', [])),
                'backtest_period_days': (
                    MISBUFFET_ENGINE_CONFIG.get('end_date', datetime.now()) - 
                    MISBUFFET_ENGINE_CONFIG.get('start_date', datetime.now())
                ).days,
                'factor_integration': True,
                'ml_models': True
            })
            
            return summary
            
        except Exception as e:
            return {"error": f"Failed to generate performance summary: {e}"}

    def _send_progress(self, message: str, level: str = 'INFO'):
        """Send progress message to web interface if available."""
        try:
            if self.web_interface and hasattr(self.web_interface, 'progress_queue'):
                self.web_interface.progress_queue.put({
                    'timestamp': datetime.now().isoformat(),
                    'level': level,
                    'message': message
                })
        except Exception:
            pass  # Ignore web interface errors
        
        # Also log the message
        getattr(logger, level.lower(), logger.info)(message)

    def cleanup(self):
        """Clean up resources after backtest completion."""
        try:
            if self.engine:
                # Attempt to cleanup engine resources
                if hasattr(self.engine, 'stop'):
                    self.engine.stop()
                
            if self.misbuffet:
                # Attempt to cleanup framework resources
                if hasattr(self.misbuffet, 'cleanup'):
                    self.misbuffet.cleanup()
                    
            logger.info("BacktestRunner cleanup completed")
            
        except Exception as e:
            logger.warning(f"Error during cleanup: {e}")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.cleanup()