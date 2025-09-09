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

import os
import logging
from typing import Optional
from pathlib import Path

# Re-export key components from all modules for easy access
from .common import *
from .data import *
from .engine import *
from .algorithm_factory import *
from .api import *
from .launcher import *
from .optimizer import *
from .optimizer_launcher import *

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

__all__ = [
    'Misbuffet',
    'MisbuffetEngine',
    'AlgorithmResult',
    'LauncherConfiguration',
    'LauncherMode'
    # Core modules are exported via their own __all__ lists
    # This provides a clean namespace for users
]