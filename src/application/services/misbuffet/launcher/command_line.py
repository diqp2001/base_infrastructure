"""
QuantConnect Lean Launcher Command Line Parser

Handles command-line argument parsing with comprehensive options
and validation for the launcher.
"""

import argparse
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging

from .interfaces import ICommandLineParser, LauncherMode, ConfigurationException


class CommandLineParser(ICommandLineParser):
    """Command-line argument parser for the launcher."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self._parser = self._create_parser()
    
    def parse_arguments(self, args: List[str]) -> Dict[str, Any]:
        """
        Parse command-line arguments.
        
        Args:
            args: Command-line arguments
            
        Returns:
            Parsed arguments dictionary
        """
        try:
            parsed_args = self._parser.parse_args(args)
            
            # Convert to dictionary and process
            result = vars(parsed_args)
            
            # Post-process arguments
            self._post_process_arguments(result)
            
            # Validate arguments
            self._validate_arguments(result)
            
            self.logger.debug(f"Parsed {len(result)} command-line arguments")
            return result
            
        except SystemExit as e:
            # Handle argparse system exit
            if e.code == 0:
                # Help was requested
                sys.exit(0)
            else:
                raise ConfigurationException("Invalid command-line arguments")
        except Exception as e:
            raise ConfigurationException(f"Failed to parse command-line arguments: {str(e)}")
    
    def get_help_text(self) -> str:
        """
        Get help text for command-line usage.
        
        Returns:
            Help text string
        """
        return self._parser.format_help()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create the argument parser with all options."""
        parser = argparse.ArgumentParser(
            description="QuantConnect Lean Launcher - Launch backtesting and live trading algorithms",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Run a backtest with default configuration
  python launcher.py --algorithm-type-name MyAlgorithm --algorithm-location ./MyAlgorithm.py
  
  # Run with custom configuration file
  python launcher.py --config ./config.json
  
  # Run in live trading mode
  python launcher.py --algorithm-type-name MyAlgorithm --algorithm-location ./MyAlgorithm.py --live-mode
  
  # Run with debugging enabled
  python launcher.py --algorithm-type-name MyAlgorithm --algorithm-location ./MyAlgorithm.py --debugging
            """
        )
        
        # Configuration options
        config_group = parser.add_argument_group("Configuration")
        config_group.add_argument(
            "--config", "-c",
            type=str,
            help="Path to JSON configuration file"
        )
        
        # Algorithm options
        algorithm_group = parser.add_argument_group("Algorithm")
        algorithm_group.add_argument(
            "--algorithm-type-name",
            type=str,
            help="Name of the algorithm class to run"
        )
        algorithm_group.add_argument(
            "--algorithm-location",
            type=str,
            help="Path to the algorithm file or assembly"
        )
        
        # Data options
        data_group = parser.add_argument_group("Data")
        data_group.add_argument(
            "--data-folder",
            type=str,
            help="Path to the data folder"
        )
        
        # Execution options
        execution_group = parser.add_argument_group("Execution")
        execution_group.add_argument(
            "--environment",
            type=str,
            choices=["backtesting", "live", "optimization", "research"],
            help="Execution environment"
        )
        execution_group.add_argument(
            "--live-mode",
            action="store_true",
            help="Enable live trading mode"
        )
        execution_group.add_argument(
            "--debugging",
            action="store_true",
            help="Enable debugging mode"
        )
        
        # Handler options
        handler_group = parser.add_argument_group("Handlers")
        handler_group.add_argument(
            "--log-handler",
            type=str,
            help="Log handler type"
        )
        handler_group.add_argument(
            "--messaging-handler",
            type=str,
            help="Messaging handler type"
        )
        handler_group.add_argument(
            "--job-queue-handler",
            type=str,
            help="Job queue handler type"
        )
        handler_group.add_argument(
            "--api-handler",
            type=str,
            help="API handler type"
        )
        
        # Performance options
        performance_group = parser.add_argument_group("Performance")
        performance_group.add_argument(
            "--maximum-data-points-per-chart-series",
            type=int,
            help="Maximum data points per chart series"
        )
        performance_group.add_argument(
            "--maximum-chart-series",
            type=int,
            help="Maximum number of chart series"
        )
        performance_group.add_argument(
            "--show-missing-data-logs",
            action="store_true",
            help="Show missing data logs"
        )
        performance_group.add_argument(
            "--no-missing-data-logs",
            action="store_true",
            help="Hide missing data logs"
        )
        
        # Utility options
        utility_group = parser.add_argument_group("Utility")
        utility_group.add_argument(
            "--validate-config",
            action="store_true",
            help="Validate configuration and exit"
        )
        utility_group.add_argument(
            "--version",
            action="version",
            version="QuantConnect Lean Launcher 1.0.0"
        )
        utility_group.add_argument(
            "--verbose", "-v",
            action="count",
            default=0,
            help="Increase verbosity level (use -v, -vv, -vvv)"
        )
        utility_group.add_argument(
            "--quiet", "-q",
            action="store_true",
            help="Suppress non-error output"
        )
        
        return parser
    
    def _post_process_arguments(self, args: Dict[str, Any]) -> None:
        """Post-process parsed arguments."""
        
        # Handle conflicting options
        if args.get("show_missing_data_logs") and args.get("no_missing_data_logs"):
            raise ConfigurationException("Cannot specify both --show-missing-data-logs and --no-missing-data-logs")
        
        # Set show_missing_data_logs based on flags
        if args.get("no_missing_data_logs"):
            args["show_missing_data_logs"] = False
        elif args.get("show_missing_data_logs"):
            args["show_missing_data_logs"] = True
        
        # Remove temporary flags
        args.pop("no_missing_data_logs", None)
        
        # Normalize paths
        for path_key in ["config", "algorithm_location", "data_folder"]:
            if args.get(path_key):
                args[path_key] = str(Path(args[path_key]).resolve())
        
        # Set verbosity level
        if args.get("quiet"):
            args["log_level"] = logging.ERROR
        elif args.get("verbose") == 1:
            args["log_level"] = logging.INFO
        elif args.get("verbose") >= 2:
            args["log_level"] = logging.DEBUG
        else:
            args["log_level"] = logging.WARNING
    
    def _validate_arguments(self, args: Dict[str, Any]) -> None:
        """Validate parsed arguments."""
        
        # Validate required arguments when not using config file
        if not args.get("config"):
            if not args.get("algorithm_type_name"):
                raise ConfigurationException("algorithm-type-name is required when not using config file")
            if not args.get("algorithm_location"):
                raise ConfigurationException("algorithm-location is required when not using config file")
        
        # Validate file paths
        if args.get("config"):
            config_path = Path(args["config"])
            if not config_path.exists():
                raise ConfigurationException(f"Configuration file not found: {config_path}")
            if not config_path.is_file():
                raise ConfigurationException(f"Configuration path is not a file: {config_path}")
        
        if args.get("algorithm_location"):
            algorithm_path = Path(args["algorithm_location"])
            if not algorithm_path.exists():
                self.logger.warning(f"Algorithm file not found: {algorithm_path}")
        
        if args.get("data_folder"):
            data_path = Path(args["data_folder"])
            if not data_path.exists():
                self.logger.warning(f"Data folder not found: {data_path}")
        
        # Validate numeric constraints
        if args.get("maximum_data_points_per_chart_series") is not None:
            if args["maximum_data_points_per_chart_series"] <= 0:
                raise ConfigurationException("maximum-data-points-per-chart-series must be positive")
        
        if args.get("maximum_chart_series") is not None:
            if args["maximum_chart_series"] <= 0:
                raise ConfigurationException("maximum-chart-series must be positive")


class CommandLineArgumentProcessor:
    """Processes command-line arguments and applies them to configuration."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def apply_arguments_to_config(self, args: Dict[str, Any], config_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply command-line arguments to configuration data.
        
        Args:
            args: Parsed command-line arguments
            config_data: Configuration data dictionary
            
        Returns:
            Updated configuration data
        """
        # Mapping from command-line arguments to configuration keys
        arg_to_config_mapping = {
            "algorithm_type_name": "algorithm-type-name",
            "algorithm_location": "algorithm-location",
            "data_folder": "data-folder",
            "environment": "environment",
            "live_mode": "live-mode",
            "debugging": "debugging",
            "log_handler": "log-handler",
            "messaging_handler": "messaging-handler",
            "job_queue_handler": "job-queue-handler",
            "api_handler": "api-handler",
            "maximum_data_points_per_chart_series": "maximum-data-points-per-chart-series",
            "maximum_chart_series": "maximum-chart-series",
            "show_missing_data_logs": "show-missing-data-logs"
        }
        
        updated_config = config_data.copy()
        applied_count = 0
        
        for arg_key, config_key in arg_to_config_mapping.items():
            if args.get(arg_key) is not None:
                updated_config[config_key] = args[arg_key]
                applied_count += 1
        
        if applied_count > 0:
            self.logger.debug(f"Applied {applied_count} command-line arguments to configuration")
        
        return updated_config
    
    def create_config_override(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create configuration override dictionary from command-line arguments.
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            Configuration override dictionary
        """
        processor = CommandLineArgumentProcessor(self.logger)
        return processor.apply_arguments_to_config(args, {})


def create_argument_parser() -> CommandLineParser:
    """Create a configured command-line argument parser."""
    return CommandLineParser()


def parse_command_line(args: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Parse command-line arguments.
    
    Args:
        args: Optional command-line arguments (uses sys.argv if None)
        
    Returns:
        Parsed arguments dictionary
    """
    if args is None:
        args = sys.argv[1:]
    
    parser = create_argument_parser()
    return parser.parse_arguments(args)