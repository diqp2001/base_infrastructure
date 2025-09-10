"""
QuantConnect Lean Python Implementation - Complete Backtesting Framework

This module provides a comprehensive Python implementation of the QuantConnect Lean 
backtesting and live trading engine. It includes all major components needed for 
algorithmic trading including data management, backtesting engine, optimization, 
and API integration.

Modules:
- common: Core interfaces, data structures, and shared utilities
- data: Data acquisition, formatting, and consumption
- engine: Main backtesting and live trading engine
- algorithm_factory: Algorithm creation, loading, and compilation
- api: REST API client for QuantConnect platform integration
- launcher: System bootstrap and configuration management
- optimizer: Parameter optimization algorithms
- optimizer_launcher: Distributed optimization orchestration
- algorithm: Algorithm base classes and utilities
- framework: Algorithm framework with portfolio and risk management components
"""

import logging
from pathlib import Path
from typing import Optional

# Re-export key components from all modules for easy access
from .common import *
from .data import *
from .engine import *
from .algorithm_factory import *
from .api import *
from .launcher import *
from .optimizer import *
from .optimizer_launcher import *
from .brokers import *

# Import algorithm framework
try:
    from .algorithm_framework import *
except ImportError:
    # Framework module might not be available in all contexts
    pass

# Import algorithm module separately to avoid circular imports
try:
    from .algorithm import *
except ImportError:
    # Algorithm module might not be available in all contexts
    pass

from .launcher.interfaces import LauncherConfiguration, LauncherMode
from .launcher.launcher import Launcher


class Misbuffet:
    """
    Main Misbuffet class for launching the backtesting framework.
    
    This class provides the entry point for initializing and running
    backtesting operations as described in the architecture documentation.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        self._launcher: Optional[Launcher] = None
        self._initialized = False
    
    @classmethod
    def launch(cls, config_file: Optional[str] = None) -> 'Misbuffet':
        """
        Launch the misbuffet package with optional configuration file.
        
        Args:
            config_file: Optional path to launch configuration file
            
        Returns:
            Misbuffet instance ready for engine startup
        """
        instance = cls()
        
        # Setup basic logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        
        instance.logger.info("Misbuffet package launched successfully")
        
        if config_file:
            # Load launch configuration
            config_path = Path(config_file)
            if config_path.exists():
                instance.logger.info(f"Loading launch configuration from: {config_file}")
                # Configuration loading would be implemented here
            else:
                instance.logger.warning(f"Launch config file not found: {config_file}")
        
        instance._initialized = True
        return instance
    
    def start_engine(self, config_file: Optional[str] = None):
        """
        Start the engine with optional engine configuration file.
        
        Args:
            config_file: Optional path to engine configuration file
            
        Returns:
            Engine instance ready to run algorithms
        """
        if not self._initialized:
            raise RuntimeError("Misbuffet must be launched before starting engine")
        
        self.logger.info("Starting Misbuffet engine...")
        
        if config_file:
            # Load engine configuration
            config_path = Path(config_file)
            if config_path.exists():
                self.logger.info(f"Loading engine configuration from: {config_file}")
                # Configuration loading would be implemented here
            else:
                self.logger.warning(f"Engine config file not found: {config_file}")
        
        # Create and return engine wrapper
        return MisbuffetEngine(self.logger)


class MisbuffetEngine:
    """
    Engine wrapper for running algorithms.
    """
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._launcher: Optional[Launcher] = None
    
    def run(self, config: LauncherConfiguration):
        """
        Run an algorithm with the given configuration.
        
        Args:
            config: LauncherConfiguration containing algorithm and execution parameters
            
        Returns:
            Results of the algorithm execution
        """
        try:
            self.logger.info(f"Running algorithm: {config.algorithm_type_name}")
            
            # Create launcher if not exists
            if self._launcher is None:
                self._launcher = Launcher(self.logger)
            
            # Initialize and run
            if self._launcher.initialize(config):
                success = self._launcher.run()
                if success:
                    self.logger.info("Algorithm execution completed successfully")
                    return AlgorithmResult(success=True, message="Execution completed")
                else:
                    self.logger.error("Algorithm execution failed")
                    return AlgorithmResult(success=False, message="Execution failed")
            else:
                self.logger.error("Failed to initialize launcher")
                return AlgorithmResult(success=False, message="Initialization failed")
                
        except Exception as e:
            self.logger.error(f"Error running algorithm: {str(e)}")
            return AlgorithmResult(success=False, message=str(e))


class AlgorithmResult:
    """Simple result container for algorithm execution."""
    
    def __init__(self, success: bool, message: str):
        self.success = success
        self.message = message
    
    def summary(self) -> str:
        """Return a summary of the algorithm execution."""
        status = "SUCCESS" if self.success else "FAILED"
        return f"Algorithm execution {status}: {self.message}"


__version__ = "1.0.0"
__author__ = "QuantConnect Lean Python Implementation"

# Import engine components from separate file
from .engine.misbuffet_engine import MisbuffetEngine, BacktestResult, MockPortfolio

# Main Misbuffet class with engine integration
class Misbuffet:
    """Main Misbuffet class for launching and managing backtesting/live trading."""
    
    def __init__(self):
        self.launcher = None
        self.engine = None
        self.logger = None
        
    @staticmethod
    def launch(config_file=None, **kwargs):
        """Launch the misbuffet package with configuration."""
        import logging
        import os
        from .launcher import Launcher, ConfigurationProvider
        
        # Setup logging
        logging.basicConfig(level=logging.INFO)
        logger = logging.getLogger("misbuffet")
        logger.info("Launching Misbuffet package...")
        
        # Create instance
        instance = Misbuffet()
        instance.logger = logger
        
        # Load configuration
        if config_file and os.path.exists(config_file):
            # Try to load config file (launch_config.py)
            config_globals = {}
            with open(config_file, 'r') as f:
                exec(f.read(), config_globals)
            logger.info(f"Loaded configuration from {config_file}")
        
        # Initialize launcher
        instance.launcher = Launcher()
        logger.info("Misbuffet package launched successfully.")
        
        return instance
    
    def start_engine(self, config_file=None, **kwargs):
        """Start the engine with configuration."""
        import logging
        import os
        from .engine import LeanEngine, BacktestingDataFeed, BacktestingTransactionHandler
        from .engine import BacktestingResultHandler, BacktestingSetupHandler
        
        if not self.logger:
            self.logger = logging.getLogger("misbuffet")
            
        self.logger.info("Starting Misbuffet engine...")
        
        # Load engine configuration
        if config_file and os.path.exists(config_file):
            # Try to load config file (engine_config.py)
            config_globals = {}
            with open(config_file, 'r') as f:
                exec(f.read(), config_globals)
            self.logger.info(f"Loaded engine configuration from {config_file}")
        
        # Create engine with handlers
        engine = MisbuffetEngine()
        engine.setup(
            data_feed=BacktestingDataFeed(),
            transaction_handler=BacktestingTransactionHandler(),
            result_handler=BacktestingResultHandler(),
            setup_handler=BacktestingSetupHandler()
        )
        
        self.engine = engine
        self.logger.info("Misbuffet engine started successfully.")
        
        return engine


__all__ = [
    # Main class
    "Misbuffet",
    
    # Engine classes
    "MisbuffetEngine",
    "BacktestResult",
    
    # Core modules are exported via their own __all__ lists
    # This provides a clean namespace for users
]