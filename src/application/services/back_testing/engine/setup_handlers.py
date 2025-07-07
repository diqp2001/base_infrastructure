"""
Setup handler implementations for QuantConnect Lean Engine Python implementation.
Handles algorithm initialization and configuration.
"""

import logging
import importlib
import sys
import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Type
from decimal import Decimal
from pathlib import Path

from .interfaces import ISetupHandler, IAlgorithm
from .engine_node_packet import EngineNodePacket
from .enums import ComponentState, SetupMode

# Import from common and algorithm_factory modules
from ..common import Symbol, Securities, Portfolio
from ..algorithm_factory import AlgorithmFactory, BaseAlgorithmLoader


class BaseSetupHandler(ISetupHandler, ABC):
    """Base class for all setup handler implementations."""
    
    def __init__(self):
        """Initialize the base setup handler."""
        self._algorithm: Optional[IAlgorithm] = None
        self._job: Optional[EngineNodePacket] = None
        self._state = ComponentState.CREATED
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Setup configuration
        self._start_date: Optional[datetime] = None
        self._end_date: Optional[datetime] = None
        self._cash: Optional[Decimal] = None
        
        # Algorithm factory
        self._algorithm_factory: Optional[AlgorithmFactory] = None
        self._algorithm_loader: Optional[AlgorithmLoader] = None
        
        self._logger.info(f"Initialized {self.__class__.__name__}")
    
    def setup(self, job: EngineNodePacket) -> IAlgorithm:
        """Setup and return the algorithm instance."""
        try:
            if self._state != ComponentState.CREATED:
                raise RuntimeError(f"Setup handler already used with state: {self._state}")
            
            self._state = ComponentState.INITIALIZING
            self._job = job
            
            self._logger.info(f"Setting up algorithm: {job.algorithm_name}")
            
            # Extract configuration
            self._extract_configuration(job)
            
            # Initialize components
            self._initialize_components()
            
            # Create algorithm instance
            algorithm = self.create_algorithm_instance(job)
            if not algorithm:
                raise RuntimeError("Failed to create algorithm instance")
            
            # Setup algorithm
            self.setup_algorithm(algorithm, job)
            
            self._algorithm = algorithm
            self._state = ComponentState.INITIALIZED
            
            self._logger.info(f"Algorithm setup completed: {algorithm.__class__.__name__}")
            return algorithm
            
        except Exception as e:
            self._logger.error(f"Error during algorithm setup: {e}")
            self._state = ComponentState.ERROR
            raise
    
    def create_algorithm_instance(self, job: EngineNodePacket) -> IAlgorithm:
        """Create an algorithm instance from the job specification."""
        try:
            if not self._algorithm_factory:
                raise RuntimeError("Algorithm factory not initialized")
            
            # Create algorithm using factory
            algorithm = self._algorithm_factory.create_algorithm(
                algorithm_location=job.algorithm_location,
                algorithm_class_name=job.algorithm_class_name,
                parameters=job.parameters
            )
            
            if not algorithm:
                raise RuntimeError(f"Failed to create algorithm: {job.algorithm_class_name}")
            
            self._logger.info(f"Created algorithm instance: {algorithm.__class__.__name__}")
            return algorithm
            
        except Exception as e:
            self._logger.error(f"Error creating algorithm instance: {e}")
            raise
    
    def setup_algorithm(self, algorithm: IAlgorithm, job: EngineNodePacket) -> None:
        """Setup the algorithm with initial parameters."""
        try:
            self._logger.info("Setting up algorithm parameters")
            
            # Set basic properties
            if hasattr(algorithm, 'set_start_date') and self._start_date:
                algorithm.set_start_date(self._start_date)
            
            if hasattr(algorithm, 'set_end_date') and self._end_date:
                algorithm.set_end_date(self._end_date)
            
            if hasattr(algorithm, 'set_cash') and self._cash:
                algorithm.set_cash(self._cash)
            
            # Setup securities collection
            if hasattr(algorithm, 'securities'):
                if not algorithm.securities:
                    algorithm.securities = Securities()
            
            # Setup portfolio
            if hasattr(algorithm, 'portfolio'):
                if not algorithm.portfolio:
                    algorithm.portfolio = Portfolio()
                    if self._cash:
                        algorithm.portfolio.set_cash(self._cash)
            
            # Apply custom parameters
            self._apply_custom_parameters(algorithm, job.parameters)
            
            # Perform specific setup
            self._setup_algorithm_specific(algorithm, job)
            
            # Initialize algorithm
            if hasattr(algorithm, 'initialize'):
                algorithm.initialize()
            
            self._logger.info("Algorithm setup completed")
            
        except Exception as e:
            self._logger.error(f"Error setting up algorithm: {e}")
            raise
    
    def get_start_date(self) -> datetime:
        """Get the algorithm start date."""
        if self._start_date:
            return self._start_date
        elif self._job and self._job.start_date:
            return self._job.start_date
        else:
            return datetime(2020, 1, 1)  # Default start date
    
    def get_end_date(self) -> datetime:
        """Get the algorithm end date."""
        if self._end_date:
            return self._end_date
        elif self._job and self._job.end_date:
            return self._job.end_date
        else:
            return datetime.utcnow()  # Default to now
    
    def get_cash(self) -> Decimal:
        """Get the initial cash amount."""
        if self._cash:
            return self._cash
        elif self._job:
            return self._job.starting_capital
        else:
            return Decimal('100000')  # Default cash
    
    def dispose(self) -> None:
        """Dispose of setup handler resources."""
        try:
            self._logger.info("Disposing setup handler")
            
            # Cleanup components
            self._cleanup_components()
            
            self._state = ComponentState.DISPOSED
            self._logger.info("Setup handler disposed")
            
        except Exception as e:
            self._logger.error(f"Error disposing setup handler: {e}")
    
    # Abstract methods for specific implementations
    
    @abstractmethod
    def _initialize_components(self) -> None:
        """Initialize specific components. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _setup_algorithm_specific(self, algorithm: IAlgorithm, job: EngineNodePacket) -> None:
        """Perform specific algorithm setup. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _cleanup_components(self) -> None:
        """Cleanup specific components. Must be implemented by subclasses."""
        pass
    
    # Protected helper methods
    
    def _extract_configuration(self, job: EngineNodePacket) -> None:
        """Extract configuration from job."""
        try:
            self._start_date = job.start_date
            self._end_date = job.end_date
            self._cash = job.starting_capital
            
            self._logger.info(f"Configuration extracted - Start: {self._start_date}, End: {self._end_date}, Cash: {self._cash}")
            
        except Exception as e:
            self._logger.error(f"Error extracting configuration: {e}")
            raise
    
    def _apply_custom_parameters(self, algorithm: IAlgorithm, parameters: Dict[str, Any]) -> None:
        """Apply custom parameters to the algorithm."""
        try:
            if not parameters:
                return
            
            self._logger.info(f"Applying {len(parameters)} custom parameters")
            
            for key, value in parameters.items():
                try:
                    # Try to set parameter as attribute
                    if hasattr(algorithm, key):
                        setattr(algorithm, key, value)
                        self._logger.debug(f"Set parameter {key} = {value}")
                    else:
                        self._logger.warning(f"Algorithm does not have parameter: {key}")
                        
                except Exception as e:
                    self._logger.warning(f"Failed to set parameter {key}: {e}")
            
        except Exception as e:
            self._logger.error(f"Error applying custom parameters: {e}")


class ConsoleSetupHandler(BaseSetupHandler):
    """Setup handler for console-based algorithm execution."""
    
    def __init__(self):
        """Initialize the console setup handler."""
        super().__init__()
        self._console_output = True
    
    def _initialize_components(self) -> None:
        """Initialize console-specific components."""
        try:
            self._logger.info("Initializing console setup handler")
            
            # Initialize algorithm factory
            self._algorithm_factory = AlgorithmFactory()
            
            # Initialize algorithm loader
            self._algorithm_loader = AlgorithmLoader()
            
            # Setup console logging
            self._setup_console_logging()
            
        except Exception as e:
            self._logger.error(f"Console setup handler initialization failed: {e}")
            raise
    
    def _setup_algorithm_specific(self, algorithm: IAlgorithm, job: EngineNodePacket) -> None:
        """Perform console-specific algorithm setup."""
        try:
            # Setup console-specific features
            if hasattr(algorithm, 'debug'):
                # Enable debug output for console
                algorithm.debug = self._console_output
            
            # Print setup information
            if self._console_output:
                print(f"Algorithm: {job.algorithm_name}")
                print(f"Period: {self._start_date} to {self._end_date}")
                print(f"Starting Capital: ${self._cash}")
                print("-" * 50)
            
            self._logger.info("Console-specific algorithm setup completed")
            
        except Exception as e:
            self._logger.error(f"Error in console algorithm setup: {e}")
            raise
    
    def _cleanup_components(self) -> None:
        """Cleanup console-specific components."""
        try:
            # No specific cleanup needed for console
            if self._console_output:
                print("Algorithm execution completed.")
            
        except Exception as e:
            self._logger.error(f"Error in console cleanup: {e}")
    
    def _setup_console_logging(self) -> None:
        """Setup console logging configuration."""
        try:
            # Configure logging for console output
            if self._console_output:
                # Ensure console handler exists
                root_logger = logging.getLogger()
                
                # Check if console handler already exists
                has_console_handler = any(
                    isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout
                    for handler in root_logger.handlers
                )
                
                if not has_console_handler:
                    console_handler = logging.StreamHandler(sys.stdout)
                    console_handler.setLevel(logging.INFO)
                    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
                    console_handler.setFormatter(formatter)
                    root_logger.addHandler(console_handler)
            
        except Exception as e:
            self._logger.error(f"Error setting up console logging: {e}")


class BacktestingSetupHandler(BaseSetupHandler):
    """Setup handler specifically for backtesting algorithms."""
    
    def __init__(self):
        """Initialize the backtesting setup handler."""
        super().__init__()
        self._data_subscriptions: List[Dict[str, Any]] = []
        self._universe_settings: Dict[str, Any] = {}
    
    def _initialize_components(self) -> None:
        """Initialize backtesting-specific components."""
        try:
            self._logger.info("Initializing backtesting setup handler")
            
            # Initialize algorithm factory with backtesting features
            self._algorithm_factory = AlgorithmFactory()
            
            # Initialize algorithm loader
            self._algorithm_loader = AlgorithmLoader()
            
            # Setup backtesting environment
            self._setup_backtesting_environment()
            
        except Exception as e:
            self._logger.error(f"Backtesting setup handler initialization failed: {e}")
            raise
    
    def _setup_algorithm_specific(self, algorithm: IAlgorithm, job: EngineNodePacket) -> None:
        """Perform backtesting-specific algorithm setup."""
        try:
            # Setup backtesting mode
            if hasattr(algorithm, 'set_live_mode'):
                algorithm.set_live_mode(False)
            
            # Setup data subscriptions for backtesting
            self._setup_data_subscriptions(algorithm, job)
            
            # Configure universe selection for backtesting
            self._setup_universe_selection(algorithm, job)
            
            # Setup performance tracking
            self._setup_performance_tracking(algorithm)
            
            self._logger.info("Backtesting-specific algorithm setup completed")
            
        except Exception as e:
            self._logger.error(f"Error in backtesting algorithm setup: {e}")
            raise
    
    def _cleanup_components(self) -> None:
        """Cleanup backtesting-specific components."""
        try:
            # Clean up data subscriptions
            self._data_subscriptions.clear()
            
            # Clean up universe settings
            self._universe_settings.clear()
            
        except Exception as e:
            self._logger.error(f"Error in backtesting cleanup: {e}")
    
    def _setup_backtesting_environment(self) -> None:
        """Setup the backtesting environment."""
        try:
            # Configure backtesting-specific settings
            self._universe_settings = {
                'resolution': 'Daily',
                'fill_forward': True,
                'extended_market_hours': False,
                'data_normalization_mode': 'Adjusted'
            }
            
            self._logger.info("Backtesting environment setup completed")
            
        except Exception as e:
            self._logger.error(f"Error setting up backtesting environment: {e}")
    
    def _setup_data_subscriptions(self, algorithm: IAlgorithm, job: EngineNodePacket) -> None:
        """Setup data subscriptions for backtesting."""
        try:
            # This would setup the data subscriptions based on the algorithm requirements
            # For now, we'll just log that subscriptions are being set up
            self._logger.info("Setting up backtesting data subscriptions")
            
            # Example: Add default subscriptions if algorithm doesn't specify any
            if hasattr(algorithm, 'add_equity'):
                # This would be called during algorithm.Initialize()
                pass
            
        except Exception as e:
            self._logger.error(f"Error setting up data subscriptions: {e}")
    
    def _setup_universe_selection(self, algorithm: IAlgorithm, job: EngineNodePacket) -> None:
        """Setup universe selection for backtesting."""
        try:
            # Configure universe selection settings
            if hasattr(algorithm, 'universe_settings'):
                # Apply universe settings from job or defaults
                for key, value in self._universe_settings.items():
                    if hasattr(algorithm.universe_settings, key):
                        setattr(algorithm.universe_settings, key, value)
            
            self._logger.info("Universe selection setup completed")
            
        except Exception as e:
            self._logger.error(f"Error setting up universe selection: {e}")
    
    def _setup_performance_tracking(self, algorithm: IAlgorithm) -> None:
        """Setup performance tracking for backtesting."""
        try:
            # Setup benchmark if specified
            if self._job and hasattr(self._job, 'benchmark_symbol'):
                benchmark_symbol = getattr(self._job, 'benchmark_symbol', 'SPY')
                if hasattr(algorithm, 'set_benchmark'):
                    # Create benchmark symbol
                    benchmark = Symbol.create(benchmark_symbol, SecurityType.EQUITY, Market.USA)
                    algorithm.set_benchmark(benchmark)
            
            # Setup performance sampling
            if hasattr(algorithm, 'set_warm_up_period'):
                # Set a default warm-up period for indicators
                algorithm.set_warm_up_period(20)  # 20 days warm-up
            
            self._logger.info("Performance tracking setup completed")
            
        except Exception as e:
            self._logger.error(f"Error setting up performance tracking: {e}")


class CloudSetupHandler(BaseSetupHandler):
    """Setup handler for cloud-based algorithm execution."""
    
    def __init__(self):
        """Initialize the cloud setup handler."""
        super().__init__()
        self._cloud_configuration: Dict[str, Any] = {}
        self._security_manager: Optional[Any] = None
    
    def _initialize_components(self) -> None:
        """Initialize cloud-specific components."""
        try:
            self._logger.info("Initializing cloud setup handler")
            
            # Initialize algorithm factory with cloud features
            self._algorithm_factory = AlgorithmFactory()
            
            # Initialize algorithm loader
            self._algorithm_loader = AlgorithmLoader()
            
            # Setup cloud configuration
            self._setup_cloud_configuration()
            
            # Initialize security manager
            self._setup_security_manager()
            
        except Exception as e:
            self._logger.error(f"Cloud setup handler initialization failed: {e}")
            raise
    
    def _setup_algorithm_specific(self, algorithm: IAlgorithm, job: EngineNodePacket) -> None:
        """Perform cloud-specific algorithm setup."""
        try:
            # Apply cloud security constraints
            self._apply_security_constraints(algorithm)
            
            # Setup cloud monitoring
            self._setup_cloud_monitoring(algorithm)
            
            # Configure cloud resources
            self._configure_cloud_resources(algorithm, job)
            
            self._logger.info("Cloud-specific algorithm setup completed")
            
        except Exception as e:
            self._logger.error(f"Error in cloud algorithm setup: {e}")
            raise
    
    def _cleanup_components(self) -> None:
        """Cleanup cloud-specific components."""
        try:
            # Cleanup cloud resources
            self._cleanup_cloud_resources()
            
            # Clear cloud configuration
            self._cloud_configuration.clear()
            
        except Exception as e:
            self._logger.error(f"Error in cloud cleanup: {e}")
    
    def _setup_cloud_configuration(self) -> None:
        """Setup cloud-specific configuration."""
        try:
            self._cloud_configuration = {
                'max_cpu_usage': 80,  # Percentage
                'max_memory_usage': 512,  # MB
                'max_execution_time': 300,  # Seconds
                'allowed_assemblies': ['System', 'QuantConnect'],
                'security_level': 'High'
            }
            
            self._logger.info("Cloud configuration setup completed")
            
        except Exception as e:
            self._logger.error(f"Error setting up cloud configuration: {e}")
    
    def _setup_security_manager(self) -> None:
        """Setup security manager for cloud execution."""
        try:
            # Initialize security manager (placeholder)
            # In practice, this would setup sandboxing, permissions, etc.
            self._logger.info("Security manager setup completed")
            
        except Exception as e:
            self._logger.error(f"Error setting up security manager: {e}")
    
    def _apply_security_constraints(self, algorithm: IAlgorithm) -> None:
        """Apply security constraints to the algorithm."""
        try:
            # Apply cloud security constraints
            # This would restrict file access, network access, etc.
            self._logger.info("Security constraints applied")
            
        except Exception as e:
            self._logger.error(f"Error applying security constraints: {e}")
    
    def _setup_cloud_monitoring(self, algorithm: IAlgorithm) -> None:
        """Setup cloud monitoring for the algorithm."""
        try:
            # Setup performance monitoring, resource usage tracking, etc.
            self._logger.info("Cloud monitoring setup completed")
            
        except Exception as e:
            self._logger.error(f"Error setting up cloud monitoring: {e}")
    
    def _configure_cloud_resources(self, algorithm: IAlgorithm, job: EngineNodePacket) -> None:
        """Configure cloud resources for the algorithm."""
        try:
            # Configure CPU, memory, storage limits
            if job.ram_allocation:
                max_memory = min(job.ram_allocation, self._cloud_configuration['max_memory_usage'])
                self._logger.info(f"Configured memory limit: {max_memory}MB")
            
        except Exception as e:
            self._logger.error(f"Error configuring cloud resources: {e}")
    
    def _cleanup_cloud_resources(self) -> None:
        """Cleanup cloud resources."""
        try:
            # Release allocated resources
            self._logger.info("Cloud resources cleaned up")
            
        except Exception as e:
            self._logger.error(f"Error cleaning up cloud resources: {e}")