"""
QuantConnect Lean Launcher Main Implementation

Main launcher class that orchestrates the entire backtesting/live trading system
by coordinating configuration, handlers, and the engine.
"""

import sys
import os
import logging
import signal
import threading
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from .interfaces import (
    ILauncher,
    ILauncherLogger,
    LauncherConfiguration,
    LauncherStatus,
    LauncherException,
    EngineInitializationException,
    AlgorithmLoadException
)
from .configuration import ConfigurationProvider, ConfigurationValidator
from .command_line import CommandLineParser, CommandLineArgumentProcessor
from .handlers import HandlerFactory

# Import engine components
try:
    from ..engine.lean_engine import LeanEngine
    from ..engine.interfaces import IEngine
    from ..algorithm_factory.algorithm_factory import AlgorithmFactory
    from ..common.interfaces import IAlgorithm
except ImportError as e:
    logging.warning(f"Some engine modules not available: {e}")
    
    # Create placeholder classes
    class LeanEngine:
        def __init__(self, *args, **kwargs):
            pass
        
        def run(self, *args, **kwargs):
            return True
    
    class AlgorithmFactory:
        def create_algorithm_instance(self, *args, **kwargs):
            return None


class LauncherLogger(ILauncherLogger):
    """Launcher-specific logger implementation."""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self.start_time = None
        self.metrics = {}
    
    def log_initialization_start(self, config: LauncherConfiguration) -> None:
        """Log initialization start."""
        self.start_time = datetime.now()
        self.logger.info("=" * 80)
        self.logger.info("QuantConnect Lean Launcher Starting")
        self.logger.info("=" * 80)
        self.logger.info(f"Mode: {config.mode.value}")
        self.logger.info(f"Algorithm: {config.algorithm_type_name}")
        self.logger.info(f"Location: {config.algorithm_location}")
        self.logger.info(f"Data Folder: {config.data_folder}")
        self.logger.info(f"Environment: {config.environment}")
        self.logger.info(f"Live Mode: {config.live_mode}")
        self.logger.info(f"Debugging: {config.debugging}")
        self.logger.info("-" * 80)
    
    def log_initialization_complete(self) -> None:
        """Log initialization completion."""
        if self.start_time:
            elapsed = datetime.now() - self.start_time
            self.logger.info(f"Initialization completed in {elapsed.total_seconds():.2f} seconds")
        else:
            self.logger.info("Initialization completed")
    
    def log_execution_start(self) -> None:
        """Log execution start."""
        self.logger.info("Starting algorithm execution...")
        self.execution_start_time = datetime.now()
    
    def log_execution_complete(self, success: bool) -> None:
        """Log execution completion."""
        if hasattr(self, 'execution_start_time'):
            elapsed = datetime.now() - self.execution_start_time
            self.logger.info(f"Algorithm execution completed in {elapsed.total_seconds():.2f} seconds")
        
        if success:
            self.logger.info("Algorithm execution completed successfully")
        else:
            self.logger.error("Algorithm execution failed")
        
        self.logger.info("=" * 80)
        self.logger.info("QuantConnect Lean Launcher Finished")
        self.logger.info("=" * 80)
    
    def log_error(self, error: Exception, context: str = "") -> None:
        """Log error with context."""
        if context:
            self.logger.error(f"Error in {context}: {str(error)}")
        else:
            self.logger.error(f"Error: {str(error)}")
        
        if hasattr(error, 'inner_exception') and error.inner_exception:
            self.logger.error(f"Inner exception: {str(error.inner_exception)}")
    
    def log_performance_metrics(self, metrics: Dict[str, Any]) -> None:
        """Log performance metrics."""
        self.logger.info("Performance Metrics:")
        for key, value in metrics.items():
            self.logger.info(f"  {key}: {value}")


class Launcher(ILauncher):
    """Main launcher implementation."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.launcher_logger = LauncherLogger(self.logger)
        
        self._status = LauncherStatus.INITIALIZING
        self._config: Optional[LauncherConfiguration] = None
        self._system_handlers = None
        self._algorithm_handlers = None
        self._engine: Optional[IEngine] = None
        self._algorithm = None
        self._shutdown_event = threading.Event()
        
        # Setup signal handlers for graceful shutdown
        self._setup_signal_handlers()
    
    @property
    def status(self) -> LauncherStatus:
        """Gets the current launcher status."""
        return self._status
    
    def initialize(self, config: LauncherConfiguration) -> bool:
        """
        Initialize the launcher with given configuration.
        
        Args:
            config: Launcher configuration
            
        Returns:
            True if initialization successful
        """
        try:
            self._status = LauncherStatus.INITIALIZING
            self.launcher_logger.log_initialization_start(config)
            
            # Store configuration
            self._config = config
            
            # Validate configuration
            self._validate_configuration()
            
            # Setup logging
            self._setup_logging()
            
            # Create handlers
            self._create_handlers()
            
            # Initialize engine
            self._initialize_engine()
            
            # Load algorithm
            self._load_algorithm()
            
            self._status = LauncherStatus.RUNNING
            self.launcher_logger.log_initialization_complete()
            
            return True
            
        except Exception as e:
            self._status = LauncherStatus.FAILED
            self.launcher_logger.log_error(e, "initialization")
            return False
    
    def run(self) -> bool:
        """
        Run the launcher.
        
        Returns:
            True if execution successful
        """
        try:
            if self._status != LauncherStatus.RUNNING:
                raise LauncherException("Launcher not properly initialized")
            
            self._status = LauncherStatus.RUNNING
            self.launcher_logger.log_execution_start()
            
            # Run the engine
            success = self._run_engine()
            
            if success:
                self._status = LauncherStatus.COMPLETED
                self.launcher_logger.log_execution_complete(True)
            else:
                self._status = LauncherStatus.FAILED
                self.launcher_logger.log_execution_complete(False)
            
            return success
            
        except Exception as e:
            self._status = LauncherStatus.FAILED
            self.launcher_logger.log_error(e, "execution")
            return False
        finally:
            self._cleanup()
    
    def stop(self) -> bool:
        """
        Stop the launcher gracefully.
        
        Returns:
            True if stop successful
        """
        try:
            self.logger.info("Stopping launcher...")
            self._status = LauncherStatus.STOPPING
            
            # Signal shutdown
            self._shutdown_event.set()
            
            # Stop engine if running
            if self._engine:
                self._engine.stop()
            
            self._status = LauncherStatus.COMPLETED
            self.logger.info("Launcher stopped successfully")
            return True
            
        except Exception as e:
            self.launcher_logger.log_error(e, "shutdown")
            return False
    
    def _validate_configuration(self) -> None:
        """Validate the configuration."""
        validator = ConfigurationValidator(self.logger)
        validation_results = validator.validate_comprehensive(self._config)
        
        # Check for critical errors
        if validation_results["critical"]:
            error_msg = "Critical configuration errors:\n" + "\n".join(validation_results["critical"])
            raise LauncherException(error_msg)
        
        # Log warnings
        if validation_results["warnings"]:
            for warning in validation_results["warnings"]:
                self.logger.warning(f"Configuration warning: {warning}")
        
        # Log recommendations
        if validation_results["recommendations"]:
            for recommendation in validation_results["recommendations"]:
                self.logger.info(f"Configuration recommendation: {recommendation}")
    
    def _setup_logging(self) -> None:
        """Setup logging based on configuration."""
        if self._config.debugging:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO
        
        # Configure root logger
        logging.getLogger().setLevel(log_level)
        
        # Add file logging if not debugging
        if not self._config.debugging:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            file_handler = logging.FileHandler(log_dir / "launcher.log")
            file_handler.setLevel(log_level)
            file_handler.setFormatter(logging.Formatter(
                '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
            ))
            logging.getLogger().addHandler(file_handler)
    
    def _create_handlers(self) -> None:
        """Create system and algorithm handlers."""
        self._status = LauncherStatus.CREATING_HANDLERS
        
        handler_factory = HandlerFactory(self.logger)
        
        # Create system handlers
        self._system_handlers = handler_factory.create_system_handlers(self._config)
        
        # Create algorithm handlers
        self._algorithm_handlers = handler_factory.create_algorithm_handlers(self._config)
        
        self.logger.info("Handlers created successfully")
    
    def _initialize_engine(self) -> None:
        """Initialize the engine."""
        self._status = LauncherStatus.STARTING_ENGINE
        
        try:
            self._engine = LeanEngine(
                system_handlers=self._system_handlers,
                algorithm_handlers=self._algorithm_handlers,
                live_mode=self._config.live_mode,
                config=self._config
            )
            
            self.logger.info("Engine initialized successfully")
            
        except Exception as e:
            raise EngineInitializationException(f"Failed to initialize engine: {str(e)}", e)
    
    def _load_algorithm(self) -> None:
        """Load the algorithm."""
        try:
            algorithm_factory = AlgorithmFactory()
            self._algorithm = algorithm_factory.create_algorithm_instance(
                algorithm_type_name=self._config.algorithm_type_name,
                algorithm_location=self._config.algorithm_location
            )
            
            self.logger.info(f"Algorithm '{self._config.algorithm_type_name}' loaded successfully")
            
        except Exception as e:
            raise AlgorithmLoadException(f"Failed to load algorithm: {str(e)}", e)
    
    def _run_engine(self) -> bool:
        """Run the engine."""
        try:
            # Check for shutdown signal
            if self._shutdown_event.is_set():
                self.logger.info("Shutdown requested before engine start")
                return False
            
            # Start engine
            result = self._engine.run(
                algorithm=self._algorithm,
                algorithm_type_name=self._config.algorithm_type_name,
                algorithm_location=self._config.algorithm_location
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Engine execution failed: {str(e)}")
            return False
    
    def _cleanup(self) -> None:
        """Cleanup resources."""
        try:
            # Cleanup engine
            if self._engine:
                self._engine.dispose()
            
            # Cleanup handlers
            if self._system_handlers:
                # Cleanup system handlers if they have cleanup methods
                pass
            
            if self._algorithm_handlers:
                # Cleanup algorithm handlers if they have cleanup methods
                pass
            
            self.logger.info("Cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {str(e)}")
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)


def main(args: Optional[List[str]] = None) -> int:
    """
    Main entry point for the launcher.
    
    Args:
        args: Optional command-line arguments
        
    Returns:
        Exit code (0 for success, non-zero for failure)
    """
    try:
        # Parse command-line arguments
        parser = CommandLineParser()
        parsed_args = parser.parse_arguments(args or sys.argv[1:])
        
        # Setup basic logging
        log_level = parsed_args.get("log_level", logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        
        logger = logging.getLogger(__name__)
        
        # Load configuration
        config_provider = ConfigurationProvider(logger)
        
        if parsed_args.get("config"):
            config = config_provider.load_configuration(parsed_args["config"])
        else:
            # Create configuration from command-line arguments
            from .configuration import ConfigurationBuilder
            builder = ConfigurationBuilder()
            
            if parsed_args.get("algorithm_type_name"):
                builder.with_algorithm(
                    parsed_args["algorithm_type_name"],
                    parsed_args.get("algorithm_location", "")
                )
            
            if parsed_args.get("data_folder"):
                builder.with_data_folder(parsed_args["data_folder"])
            
            if parsed_args.get("environment"):
                builder.with_environment(parsed_args["environment"])
            
            if parsed_args.get("live_mode"):
                builder.with_live_mode(True)
            
            if parsed_args.get("debugging"):
                builder.with_debugging(True)
            
            config = builder.build()
        
        # Apply command-line overrides
        processor = CommandLineArgumentProcessor(logger)
        config_dict = {
            "algorithm-type-name": config.algorithm_type_name,
            "algorithm-location": config.algorithm_location,
            "data-folder": config.data_folder,
            "environment": config.environment,
            "live-mode": config.live_mode,
            "debugging": config.debugging
        }
        
        updated_config_dict = processor.apply_arguments_to_config(parsed_args, config_dict)
        updated_config = config_provider._create_launcher_configuration(updated_config_dict)
        
        # Handle special flags
        if parsed_args.get("validate_config"):
            validator = ConfigurationValidator(logger)
            validation_results = validator.validate_comprehensive(updated_config)
            
            if validation_results["critical"]:
                print("Configuration validation failed:")
                for error in validation_results["critical"]:
                    print(f"  ERROR: {error}")
                return 1
            
            if validation_results["warnings"]:
                print("Configuration warnings:")
                for warning in validation_results["warnings"]:
                    print(f"  WARNING: {warning}")
            
            if validation_results["recommendations"]:
                print("Configuration recommendations:")
                for recommendation in validation_results["recommendations"]:
                    print(f"  INFO: {recommendation}")
            
            print("Configuration validation passed")
            return 0
        
        # Create and run launcher
        launcher = Launcher(logger)
        
        if not launcher.initialize(updated_config):
            logger.error("Launcher initialization failed")
            return 1
        
        if not launcher.run():
            logger.error("Launcher execution failed")
            return 1
        
        return 0
        
    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt, shutting down...")
        return 1
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())