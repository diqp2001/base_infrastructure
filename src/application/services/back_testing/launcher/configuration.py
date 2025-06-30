"""
QuantConnect Lean Launcher Configuration System

Handles configuration loading from JSON files, environment variables,
and command-line arguments with proper validation and error handling.
"""

import json
import os
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
import logging
from dataclasses import asdict

from .interfaces import (
    IConfigurationProvider,
    LauncherConfiguration,
    LauncherMode,
    ConfigurationException
)


class ConfigurationProvider(IConfigurationProvider):
    """Configuration provider that loads from multiple sources."""
    
    DEFAULT_CONFIG = {
        "environment": "backtesting",
        "algorithm-type-name": "BasicTemplateAlgorithm",
        "algorithm-location": "",
        "data-folder": "./data/",
        "log-handler": "ConsoleLogHandler",
        "messaging-handler": "NullMessagingHandler",
        "job-queue-handler": "JobQueue",
        "api-handler": "Api",
        "live-mode": False,
        "debugging": False,
        "show-missing-data-logs": True,
        "maximum-data-points-per-chart-series": 4000,
        "maximum-chart-series": 30
    }
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def load_configuration(self, config_path: Optional[str] = None) -> LauncherConfiguration:
        """
        Load configuration from multiple sources with proper precedence.
        
        Precedence (highest to lowest):
        1. Command-line arguments
        2. Environment variables  
        3. JSON configuration file
        4. Default configuration
        
        Args:
            config_path: Optional path to JSON configuration file
            
        Returns:
            LauncherConfiguration instance
        """
        try:
            # Start with default configuration
            config_data = self.DEFAULT_CONFIG.copy()
            
            # Load from JSON file if provided
            if config_path:
                file_config = self._load_json_config(config_path)
                config_data.update(file_config)
            
            # Override with environment variables
            env_config = self._load_environment_config()
            config_data.update(env_config)
            
            # Convert to LauncherConfiguration
            launcher_config = self._create_launcher_configuration(config_data)
            
            self.logger.info(f"Configuration loaded successfully from {config_path or 'defaults'}")
            return launcher_config
            
        except Exception as e:
            raise ConfigurationException(f"Failed to load configuration: {str(e)}", e)
    
    def validate_configuration(self, config: LauncherConfiguration) -> List[str]:
        """
        Validate configuration and return list of validation errors.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Validate algorithm settings
        if not config.algorithm_type_name:
            errors.append("Algorithm type name is required")
        
        if not config.algorithm_location:
            errors.append("Algorithm location is required")
        
        # Validate data folder
        if not config.data_folder:
            errors.append("Data folder is required")
        elif not Path(config.data_folder).exists():
            self.logger.warning(f"Data folder does not exist: {config.data_folder}")
        
        # Validate mode-specific requirements
        if config.mode == LauncherMode.LIVE_TRADING:
            if not config.live_mode:
                errors.append("Live mode must be enabled for live trading")
        
        # Validate numeric constraints
        if config.maximum_data_points_per_chart_series <= 0:
            errors.append("Maximum data points per chart series must be positive")
        
        if config.maximum_chart_series <= 0:
            errors.append("Maximum chart series must be positive")
        
        return errors
    
    def _load_json_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            self.logger.debug(f"Loaded JSON configuration from {config_path}")
            return config_data
            
        except json.JSONDecodeError as e:
            raise ConfigurationException(f"Invalid JSON in configuration file {config_path}: {str(e)}")
        except Exception as e:
            raise ConfigurationException(f"Failed to load configuration file {config_path}: {str(e)}")
    
    def _load_environment_config(self) -> Dict[str, Any]:
        """Load configuration from environment variables."""
        env_config = {}
        
        # Map environment variables to configuration keys
        env_mappings = {
            "LEAN_ALGORITHM_TYPE_NAME": "algorithm-type-name",
            "LEAN_ALGORITHM_LOCATION": "algorithm-location",
            "LEAN_DATA_FOLDER": "data-folder",
            "LEAN_ENVIRONMENT": "environment",
            "LEAN_LIVE_MODE": "live-mode",
            "LEAN_DEBUGGING": "debugging",
            "LEAN_LOG_HANDLER": "log-handler",
            "LEAN_MESSAGING_HANDLER": "messaging-handler",
            "LEAN_JOB_QUEUE_HANDLER": "job-queue-handler",
            "LEAN_API_HANDLER": "api-handler"
        }
        
        for env_var, config_key in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Convert string values to appropriate types
                if config_key in ["live-mode", "debugging", "show-missing-data-logs"]:
                    env_config[config_key] = value.lower() in ('true', '1', 'yes', 'on')
                elif config_key in ["maximum-data-points-per-chart-series", "maximum-chart-series"]:
                    try:
                        env_config[config_key] = int(value)
                    except ValueError:
                        self.logger.warning(f"Invalid integer value for {env_var}: {value}")
                else:
                    env_config[config_key] = value
        
        if env_config:
            self.logger.debug(f"Loaded {len(env_config)} configuration values from environment")
        
        return env_config
    
    def _create_launcher_configuration(self, config_data: Dict[str, Any]) -> LauncherConfiguration:
        """Create LauncherConfiguration from configuration dictionary."""
        try:
            # Determine launcher mode
            environment = config_data.get("environment", "backtesting").lower()
            live_mode = config_data.get("live-mode", False)
            
            if live_mode or environment == "live":
                mode = LauncherMode.LIVE_TRADING
            elif environment == "optimization":
                mode = LauncherMode.OPTIMIZATION
            elif environment == "research":
                mode = LauncherMode.RESEARCH
            else:
                mode = LauncherMode.BACKTESTING
            
            return LauncherConfiguration(
                mode=mode,
                algorithm_type_name=config_data.get("algorithm-type-name", ""),
                algorithm_location=config_data.get("algorithm-location", ""),
                data_folder=config_data.get("data-folder", "./data/"),
                environment=config_data.get("environment", "backtesting"),
                live_mode=config_data.get("live-mode", False),
                log_handler=config_data.get("log-handler", "ConsoleLogHandler"),
                messaging_handler=config_data.get("messaging-handler", "NullMessagingHandler"),
                job_queue_handler=config_data.get("job-queue-handler", "JobQueue"),
                api_handler=config_data.get("api-handler", "Api"),
                debugging=config_data.get("debugging", False),
                show_missing_data_logs=config_data.get("show-missing-data-logs", True),
                maximum_data_points_per_chart_series=config_data.get("maximum-data-points-per-chart-series", 4000),
                maximum_chart_series=config_data.get("maximum-chart-series", 30),
                custom_config={k: v for k, v in config_data.items() 
                             if k not in self._get_known_config_keys()}
            )
            
        except Exception as e:
            raise ConfigurationException(f"Failed to create launcher configuration: {str(e)}")
    
    def _get_known_config_keys(self) -> set:
        """Get set of known configuration keys."""
        return {
            "environment", "algorithm-type-name", "algorithm-location", "data-folder",
            "live-mode", "log-handler", "messaging-handler", "job-queue-handler",
            "api-handler", "debugging", "show-missing-data-logs",
            "maximum-data-points-per-chart-series", "maximum-chart-series"
        }
    
    def save_configuration(self, config: LauncherConfiguration, output_path: str) -> None:
        """
        Save configuration to JSON file.
        
        Args:
            config: Configuration to save
            output_path: Path to output JSON file
        """
        try:
            # Convert to dictionary format suitable for JSON
            config_dict = {
                "environment": config.environment,
                "algorithm-type-name": config.algorithm_type_name,
                "algorithm-location": config.algorithm_location,
                "data-folder": config.data_folder,
                "live-mode": config.live_mode,
                "log-handler": config.log_handler,
                "messaging-handler": config.messaging_handler,
                "job-queue-handler": config.job_queue_handler,
                "api-handler": config.api_handler,
                "debugging": config.debugging,
                "show-missing-data-logs": config.show_missing_data_logs,
                "maximum-data-points-per-chart-series": config.maximum_data_points_per_chart_series,
                "maximum-chart-series": config.maximum_chart_series
            }
            
            # Add custom configuration
            config_dict.update(config.custom_config)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Configuration saved to {output_path}")
            
        except Exception as e:
            raise ConfigurationException(f"Failed to save configuration to {output_path}: {str(e)}")


class ConfigurationBuilder:
    """Builder for creating LauncherConfiguration instances."""
    
    def __init__(self):
        self._config_data = {}
    
    def with_algorithm(self, type_name: str, location: str) -> 'ConfigurationBuilder':
        """Set algorithm configuration."""
        self._config_data["algorithm-type-name"] = type_name
        self._config_data["algorithm-location"] = location
        return self
    
    def with_data_folder(self, folder: str) -> 'ConfigurationBuilder':
        """Set data folder."""
        self._config_data["data-folder"] = folder
        return self
    
    def with_environment(self, environment: str) -> 'ConfigurationBuilder':
        """Set environment."""
        self._config_data["environment"] = environment
        return self
    
    def with_live_mode(self, live_mode: bool = True) -> 'ConfigurationBuilder':
        """Enable/disable live mode."""
        self._config_data["live-mode"] = live_mode
        return self
    
    def with_debugging(self, debugging: bool = True) -> 'ConfigurationBuilder':
        """Enable/disable debugging."""
        self._config_data["debugging"] = debugging
        return self
    
    def with_handlers(self, log_handler: str = None, messaging_handler: str = None,
                     job_queue_handler: str = None, api_handler: str = None) -> 'ConfigurationBuilder':
        """Set handler configurations."""
        if log_handler:
            self._config_data["log-handler"] = log_handler
        if messaging_handler:
            self._config_data["messaging-handler"] = messaging_handler
        if job_queue_handler:
            self._config_data["job-queue-handler"] = job_queue_handler
        if api_handler:
            self._config_data["api-handler"] = api_handler
        return self
    
    def with_custom_config(self, key: str, value: Any) -> 'ConfigurationBuilder':
        """Add custom configuration."""
        self._config_data[key] = value
        return self
    
    def build(self) -> LauncherConfiguration:
        """Build the LauncherConfiguration."""
        provider = ConfigurationProvider()
        
        # Merge with defaults
        config_data = provider.DEFAULT_CONFIG.copy()
        config_data.update(self._config_data)
        
        return provider._create_launcher_configuration(config_data)


class ConfigurationValidator:
    """Advanced configuration validator with detailed error reporting."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def validate_comprehensive(self, config: LauncherConfiguration) -> Dict[str, List[str]]:
        """
        Perform comprehensive validation with categorized errors.
        
        Returns:
            Dictionary with error categories and lists of errors
        """
        validation_results = {
            "critical": [],
            "warnings": [],
            "recommendations": []
        }
        
        # Critical validations
        self._validate_critical_settings(config, validation_results["critical"])
        
        # Warning validations
        self._validate_warning_settings(config, validation_results["warnings"])
        
        # Recommendations
        self._validate_recommendations(config, validation_results["recommendations"])
        
        return validation_results
    
    def _validate_critical_settings(self, config: LauncherConfiguration, errors: List[str]) -> None:
        """Validate critical settings that prevent execution."""
        if not config.algorithm_type_name:
            errors.append("algorithm-type-name is required")
        
        if not config.algorithm_location:
            errors.append("algorithm-location is required")
        
        if not config.data_folder:
            errors.append("data-folder is required")
    
    def _validate_warning_settings(self, config: LauncherConfiguration, warnings: List[str]) -> None:
        """Validate settings that might cause issues."""
        if not Path(config.data_folder).exists():
            warnings.append(f"Data folder does not exist: {config.data_folder}")
        
        if config.maximum_data_points_per_chart_series > 10000:
            warnings.append("Very high maximum data points per chart series may impact performance")
        
        if config.maximum_chart_series > 100:
            warnings.append("Very high maximum chart series may impact performance")
    
    def _validate_recommendations(self, config: LauncherConfiguration, recommendations: List[str]) -> None:
        """Provide configuration recommendations."""
        if config.mode == LauncherMode.LIVE_TRADING and config.debugging:
            recommendations.append("Consider disabling debugging in live trading for performance")
        
        if not config.show_missing_data_logs and config.debugging:
            recommendations.append("Consider enabling missing data logs when debugging")