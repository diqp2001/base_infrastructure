"""
QuantConnect Lean Launcher Module

This module provides the main launcher functionality for the QuantConnect Lean
backtesting and live trading system. It handles configuration management,
command-line parsing, handler coordination, and engine orchestration.

Main Components:
- Launcher: Main orchestrator class
- ConfigurationProvider: Configuration loading and validation
- CommandLineParser: Command-line argument parsing
- HandlerFactory: Handler creation and management
- LauncherConfiguration: Configuration data structure

Usage:
    # Basic usage with command-line arguments
    from src.application.services.back_testing.launcher import main
    exit_code = main()
    
    # Programmatic usage
    from src.application.services.back_testing.launcher import Launcher, ConfigurationBuilder
    
    config = (ConfigurationBuilder()
             .with_algorithm("MyAlgorithm", "./my_algorithm.py")
             .with_data_folder("./data")
             .build())
    
    launcher = Launcher()
    launcher.initialize(config)
    launcher.run()
"""

# Core interfaces and data structures
from .interfaces import (
    # Main interfaces
    ILauncher,
    IConfigurationProvider,
    IHandlerFactory,
    ICommandLineParser,
    ILauncherLogger,
    ILauncherSystemHandlers,
    ILauncherAlgorithmHandlers,
    
    # Data structures
    LauncherConfiguration,
    LauncherMode,
    LauncherStatus,
    
    # Exceptions
    LauncherException,
    ConfigurationException,
    HandlerCreationException,
    EngineInitializationException,
    AlgorithmLoadException
)

# Configuration management
from .configuration import (
    ConfigurationProvider,
    ConfigurationBuilder,
    ConfigurationValidator
)

# Command-line processing
from .command_line import (
    CommandLineParser,
    CommandLineArgumentProcessor,
    create_argument_parser,
    parse_command_line
)

# Handler management
from .handlers import (
    HandlerFactory,
    LauncherSystemHandlers,
    LauncherAlgorithmHandlers
)

# Main launcher implementation
from .launcher import (
    Launcher,
    LauncherLogger,
    main
)

# Public API exports
__all__ = [
    # Main entry points
    "main",
    "Launcher",
    "LauncherLogger",
    
    # Configuration
    "LauncherConfiguration",
    "ConfigurationProvider",
    "ConfigurationBuilder",
    "ConfigurationValidator",
    
    # Command-line processing
    "CommandLineParser",
    "CommandLineArgumentProcessor",
    "create_argument_parser",
    "parse_command_line",
    
    # Handler management
    "HandlerFactory",
    "LauncherSystemHandlers",
    "LauncherAlgorithmHandlers",
    
    # Interfaces
    "ILauncher",
    "IConfigurationProvider",
    "IHandlerFactory",
    "ICommandLineParser",
    "ILauncherLogger",
    "ILauncherSystemHandlers",
    "ILauncherAlgorithmHandlers",
    
    # Enums
    "LauncherMode",
    "LauncherStatus",
    
    # Exceptions
    "LauncherException",
    "ConfigurationException",
    "HandlerCreationException",
    "EngineInitializationException",
    "AlgorithmLoadException"
]

# Version information
__version__ = "1.0.0"
__author__ = "QuantConnect Lean Launcher Team"
__description__ = "QuantConnect Lean Launcher for backtesting and live trading"

# Module metadata
__package_name__ = "launcher"
__package_description__ = "Main launcher module for QuantConnect Lean engine"

# Convenience functions for common use cases
def create_backtest_launcher(algorithm_name: str, algorithm_location: str, data_folder: str = "./data") -> Launcher:
    """
    Create a launcher configured for backtesting.
    
    Args:
        algorithm_name: Name of the algorithm class
        algorithm_location: Path to the algorithm file
        data_folder: Path to data folder
        
    Returns:
        Configured Launcher instance
    """
    config = (ConfigurationBuilder()
             .with_algorithm(algorithm_name, algorithm_location)
             .with_data_folder(data_folder)
             .with_environment("backtesting")
             .build())
    
    launcher = Launcher()
    return launcher


def create_live_launcher(algorithm_name: str, algorithm_location: str, data_folder: str = "./data") -> Launcher:
    """
    Create a launcher configured for live trading.
    
    Args:
        algorithm_name: Name of the algorithm class
        algorithm_location: Path to the algorithm file
        data_folder: Path to data folder
        
    Returns:
        Configured Launcher instance
    """
    config = (ConfigurationBuilder()
             .with_algorithm(algorithm_name, algorithm_location)
             .with_data_folder(data_folder)
             .with_environment("live")
             .with_live_mode(True)
             .build())
    
    launcher = Launcher()
    return launcher


def validate_launcher_config(config_file: str = None, **kwargs) -> dict:
    """
    Validate launcher configuration.
    
    Args:
        config_file: Optional path to configuration file
        **kwargs: Configuration overrides
        
    Returns:
        Validation results dictionary
    """
    provider = ConfigurationProvider()
    
    if config_file:
        config = provider.load_configuration(config_file)
    else:
        builder = ConfigurationBuilder()
        for key, value in kwargs.items():
            builder.with_custom_config(key, value)
        config = builder.build()
    
    validator = ConfigurationValidator()
    return validator.validate_comprehensive(config)


def quick_backtest(algorithm_name: str, algorithm_location: str, **config_overrides) -> bool:
    """
    Quick backtesting utility function.
    
    Args:
        algorithm_name: Name of the algorithm class
        algorithm_location: Path to the algorithm file
        **config_overrides: Additional configuration options
        
    Returns:
        True if backtest successful
    """
    try:
        # Create configuration
        builder = (ConfigurationBuilder()
                  .with_algorithm(algorithm_name, algorithm_location)
                  .with_environment("backtesting"))
        
        for key, value in config_overrides.items():
            builder.with_custom_config(key, value)
        
        config = builder.build()
        
        # Run launcher
        launcher = Launcher()
        if not launcher.initialize(config):
            return False
        
        return launcher.run()
        
    except Exception:
        return False


def quick_live_trade(algorithm_name: str, algorithm_location: str, **config_overrides) -> bool:
    """
    Quick live trading utility function.
    
    Args:
        algorithm_name: Name of the algorithm class
        algorithm_location: Path to the algorithm file
        **config_overrides: Additional configuration options
        
    Returns:
        True if live trading started successfully
    """
    try:
        # Create configuration
        builder = (ConfigurationBuilder()
                  .with_algorithm(algorithm_name, algorithm_location)
                  .with_environment("live")
                  .with_live_mode(True))
        
        for key, value in config_overrides.items():
            builder.with_custom_config(key, value)
        
        config = builder.build()
        
        # Run launcher
        launcher = Launcher()
        if not launcher.initialize(config):
            return False
        
        return launcher.run()
        
    except Exception:
        return False


# Integration helpers
def get_launcher_version() -> str:
    """Get the launcher version."""
    return __version__


def get_supported_modes() -> list:
    """Get list of supported launcher modes."""
    return [mode.value for mode in LauncherMode]


def get_available_handlers() -> dict:
    """Get dictionary of available handler types."""
    return {
        "log_handlers": ["ConsoleLogHandler", "FileLogHandler"],
        "messaging_handlers": ["NullMessagingHandler", "StreamingMessagingHandler"],
        "data_feeds": ["FileSystemDataFeed", "LiveDataFeed", "BacktestingDataFeed"],
        "transaction_handlers": ["BacktestingTransactionHandler", "BrokerageTransactionHandler"],
        "result_handlers": ["BacktestingResultHandler", "LiveTradingResultHandler"]
    }


# Documentation and help
def print_launcher_help():
    """Print comprehensive launcher help."""
    parser = CommandLineParser()
    print(parser.get_help_text())
    
    print("\nAdditional Information:")
    print(f"Version: {__version__}")
    print(f"Supported modes: {', '.join(get_supported_modes())}")
    print("\nFor more information, visit the QuantConnect documentation.")


# Module initialization
def _setup_module_logging():
    """Setup module-level logging."""
    import logging
    logger = logging.getLogger(__name__)
    logger.addHandler(logging.NullHandler())


# Initialize the module
_setup_module_logging()