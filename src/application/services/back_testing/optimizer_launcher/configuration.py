"""
QuantConnect Lean Optimizer.Launcher Configuration

Provides configuration management for the optimizer launcher including
parameter loading, validation, and environment-specific settings.
"""

import json
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

from .interfaces import (
    OptimizerLauncherConfiguration, 
    OptimizerLauncherMode,
    OptimizerLauncherException
)
from ..launcher.interfaces import LauncherConfiguration, LauncherMode
from ..optimizer.enums import OptimizationType


@dataclass
class OptimizerParameterConfig:
    """Configuration for optimization parameters."""
    
    name: str
    type: str  # int, float, bool, categorical, string
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    values: Optional[List[Any]] = None  # For categorical parameters
    default_value: Optional[Any] = None


@dataclass
class OptimizerTargetConfig:
    """Configuration for optimization target."""
    
    name: str
    objectives: List[str]
    maximize: bool = True
    weight: float = 1.0
    constraints: Optional[List[str]] = None


@dataclass
class WorkerConfig:
    """Configuration for worker nodes."""
    
    worker_type: str = "local"  # local, docker, kubernetes, cloud
    max_workers: int = 4
    timeout: int = 3600
    resource_limits: Dict[str, Any] = None
    environment_variables: Dict[str, str] = None
    
    def __post_init__(self):
        if self.resource_limits is None:
            self.resource_limits = {"cpu": 1, "memory": "2Gi"}
        if self.environment_variables is None:
            self.environment_variables = {}


@dataclass
class CloudConfig:
    """Configuration for cloud execution."""
    
    provider: str  # aws, azure, gcp
    region: str
    instance_type: str
    image_name: str
    credentials_file: Optional[str] = None
    vpc_config: Optional[Dict[str, Any]] = None
    security_groups: Optional[List[str]] = None
    tags: Optional[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = {}


class OptimizerLauncherConfigurationBuilder:
    """Builder for creating optimizer launcher configurations."""
    
    def __init__(self):
        self._config = OptimizerLauncherConfiguration(
            optimization_target="sharpe_ratio",
            algorithm_type_name="",
            algorithm_location="",
            parameter_file=""
        )
        self._parameters: List[OptimizerParameterConfig] = []
        self._target_config: Optional[OptimizerTargetConfig] = None
        self._worker_config: Optional[WorkerConfig] = None
        self._cloud_config: Optional[CloudConfig] = None
    
    def with_algorithm(self, type_name: str, location: str) -> 'OptimizerLauncherConfigurationBuilder':
        """Set algorithm configuration."""
        self._config.algorithm_type_name = type_name
        self._config.algorithm_location = location
        return self
    
    def with_parameters(self, parameter_file: str) -> 'OptimizerLauncherConfigurationBuilder':
        """Set parameter configuration file."""
        self._config.parameter_file = parameter_file
        return self
    
    def with_mode(self, mode: OptimizerLauncherMode) -> 'OptimizerLauncherConfigurationBuilder':
        """Set execution mode."""
        self._config.mode = mode
        return self
    
    def with_concurrent_backtests(self, count: int) -> 'OptimizerLauncherConfigurationBuilder':
        """Set maximum concurrent backtests."""
        self._config.max_concurrent_backtests = count
        return self
    
    def with_data_folder(self, folder: str) -> 'OptimizerLauncherConfigurationBuilder':
        """Set data folder."""
        self._config.data_folder = folder
        return self
    
    def with_output_folder(self, folder: str) -> 'OptimizerLauncherConfigurationBuilder':
        """Set output folder."""
        self._config.output_folder = folder
        return self
    
    def with_target(self, target: OptimizerTargetConfig) -> 'OptimizerLauncherConfigurationBuilder':
        """Set optimization target configuration."""
        self._target_config = target
        self._config.optimization_target = target.name
        return self
    
    def with_worker_config(self, worker_config: WorkerConfig) -> 'OptimizerLauncherConfigurationBuilder':
        """Set worker configuration."""
        self._worker_config = worker_config
        self._config.max_concurrent_backtests = worker_config.max_workers
        return self
    
    def with_cloud_config(self, cloud_config: CloudConfig) -> 'OptimizerLauncherConfigurationBuilder':
        """Set cloud configuration."""
        self._cloud_config = cloud_config
        self._config.mode = OptimizerLauncherMode.CLOUD
        return self
    
    def with_checkpointing(self, enabled: bool, frequency: int = 50) -> 'OptimizerLauncherConfigurationBuilder':
        """Set checkpointing configuration."""
        self._config.enable_checkpointing = enabled
        self._config.checkpoint_frequency = frequency
        return self
    
    def with_fault_tolerance(self, enabled: bool) -> 'OptimizerLauncherConfigurationBuilder':
        """Set fault tolerance configuration."""
        self._config.fault_tolerance = enabled
        return self
    
    def with_launcher_config(self, launcher_config: LauncherConfiguration) -> 'OptimizerLauncherConfigurationBuilder':
        """Set launcher configuration."""
        self._config.launcher_config = launcher_config
        return self
    
    def build(self) -> OptimizerLauncherConfiguration:
        """Build the configuration."""
        # Store additional configurations in custom_config
        custom_config = self._config.custom_config or {}
        
        if self._target_config:
            custom_config['target_config'] = asdict(self._target_config)
        
        if self._worker_config:
            custom_config['worker_config'] = asdict(self._worker_config)
        
        if self._cloud_config:
            custom_config['cloud_config'] = asdict(self._cloud_config)
        
        custom_config['parameters'] = [asdict(p) for p in self._parameters]
        
        self._config.custom_config = custom_config
        return self._config


class OptimizerLauncherConfigurationManager:
    """Manager for loading and validating optimizer launcher configurations."""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
    
    def load_from_file(self, config_path: str) -> OptimizerLauncherConfiguration:
        """
        Load configuration from JSON file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Loaded configuration
            
        Raises:
            OptimizerLauncherException: If file cannot be loaded or parsed
        """
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                raise OptimizerLauncherException(f"Configuration file not found: {config_path}")
            
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            return self._create_configuration_from_dict(config_data)
        
        except json.JSONDecodeError as e:
            raise OptimizerLauncherException(f"Invalid JSON in configuration file: {e}")
        except Exception as e:
            raise OptimizerLauncherException(f"Error loading configuration: {e}")
    
    def load_from_environment(self) -> OptimizerLauncherConfiguration:
        """
        Load configuration from environment variables.
        
        Returns:
            Configuration loaded from environment
        """
        config_data = {
            'optimization_target': os.getenv('OPTIMIZER_TARGET', 'sharpe_ratio'),
            'algorithm_type_name': os.getenv('ALGORITHM_TYPE_NAME', ''),
            'algorithm_location': os.getenv('ALGORITHM_LOCATION', ''),
            'parameter_file': os.getenv('PARAMETER_FILE', ''),
            'mode': os.getenv('OPTIMIZER_MODE', 'local'),
            'max_concurrent_backtests': int(os.getenv('MAX_CONCURRENT_BACKTESTS', '4')),
            'data_folder': os.getenv('DATA_FOLDER', 'data'),
            'output_folder': os.getenv('OUTPUT_FOLDER', 'output'),
            'enable_checkpointing': os.getenv('ENABLE_CHECKPOINTING', 'true').lower() == 'true',
            'fault_tolerance': os.getenv('FAULT_TOLERANCE', 'true').lower() == 'true'
        }
        
        return self._create_configuration_from_dict(config_data)
    
    def _create_configuration_from_dict(self, config_data: Dict[str, Any]) -> OptimizerLauncherConfiguration:
        """Create configuration from dictionary data."""
        
        # Convert mode string to enum
        mode_str = config_data.get('mode', 'local')
        try:
            mode = OptimizerLauncherMode(mode_str)
        except ValueError:
            self.logger.warning(f"Invalid mode '{mode_str}', using LOCAL")
            mode = OptimizerLauncherMode.LOCAL
        
        # Create launcher configuration if provided
        launcher_config = None
        if 'launcher_config' in config_data:
            launcher_data = config_data['launcher_config']
            launcher_config = LauncherConfiguration(
                mode=LauncherMode(launcher_data.get('mode', 'backtesting')),
                algorithm_type_name=launcher_data.get('algorithm_type_name', ''),
                algorithm_location=launcher_data.get('algorithm_location', ''),
                data_folder=launcher_data.get('data_folder', 'data'),
                custom_config=launcher_data.get('custom_config', {})
            )
        
        # Create main configuration
        config = OptimizerLauncherConfiguration(
            optimization_target=config_data.get('optimization_target', 'sharpe_ratio'),
            algorithm_type_name=config_data.get('algorithm_type_name', ''),
            algorithm_location=config_data.get('algorithm_location', ''),
            parameter_file=config_data.get('parameter_file', ''),
            mode=mode,
            max_concurrent_backtests=config_data.get('max_concurrent_backtests', 4),
            worker_timeout=config_data.get('worker_timeout', 3600),
            data_folder=config_data.get('data_folder', 'data'),
            output_folder=config_data.get('output_folder', 'output'),
            results_file=config_data.get('results_file', 'optimization_results.json'),
            launcher_config=launcher_config,
            enable_checkpointing=config_data.get('enable_checkpointing', True),
            checkpoint_frequency=config_data.get('checkpoint_frequency', 50),
            fault_tolerance=config_data.get('fault_tolerance', True),
            result_caching=config_data.get('result_caching', True),
            cloud_provider=config_data.get('cloud_provider'),
            worker_image=config_data.get('worker_image'),
            resource_requirements=config_data.get('resource_requirements', {"cpu": 1, "memory": "2Gi"}),
            custom_config=config_data.get('custom_config', {})
        )
        
        return config
    
    def validate_configuration(self, config: OptimizerLauncherConfiguration) -> List[str]:
        """
        Validate configuration and return list of errors.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Validate required fields
        if not config.algorithm_type_name:
            errors.append("algorithm_type_name is required")
        
        if not config.algorithm_location:
            errors.append("algorithm_location is required")
        
        if not config.parameter_file:
            errors.append("parameter_file is required")
        
        # Validate algorithm location exists
        if config.algorithm_location and not Path(config.algorithm_location).exists():
            errors.append(f"Algorithm location does not exist: {config.algorithm_location}")
        
        # Validate parameter file exists
        if config.parameter_file and not Path(config.parameter_file).exists():
            errors.append(f"Parameter file does not exist: {config.parameter_file}")
        
        # Validate data folder exists
        if config.data_folder and not Path(config.data_folder).exists():
            errors.append(f"Data folder does not exist: {config.data_folder}")
        
        # Validate numeric values
        if config.max_concurrent_backtests <= 0:
            errors.append("max_concurrent_backtests must be greater than 0")
        
        if config.worker_timeout <= 0:
            errors.append("worker_timeout must be greater than 0")
        
        if config.checkpoint_frequency <= 0:
            errors.append("checkpoint_frequency must be greater than 0")
        
        # Validate cloud configuration if cloud mode
        if config.mode == OptimizerLauncherMode.CLOUD:
            if not config.cloud_provider:
                errors.append("cloud_provider is required for cloud mode")
            
            if not config.worker_image:
                errors.append("worker_image is required for cloud mode")
        
        # Validate launcher configuration
        if config.launcher_config:
            if not config.launcher_config.algorithm_type_name:
                errors.append("launcher_config.algorithm_type_name is required")
        
        return errors
    
    def save_configuration(self, config: OptimizerLauncherConfiguration, file_path: str) -> bool:
        """
        Save configuration to file.
        
        Args:
            config: Configuration to save
            file_path: Path to save file
            
        Returns:
            True if save successful
        """
        try:
            config_dict = asdict(config)
            
            # Convert enums to strings
            config_dict['mode'] = config.mode.value
            if config.launcher_config:
                config_dict['launcher_config']['mode'] = config.launcher_config.mode.value
            
            with open(file_path, 'w') as f:
                json.dump(config_dict, f, indent=2, default=str)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
    
    def merge_configurations(self, 
                           base_config: OptimizerLauncherConfiguration,
                           override_config: Dict[str, Any]) -> OptimizerLauncherConfiguration:
        """
        Merge base configuration with override values.
        
        Args:
            base_config: Base configuration
            override_config: Override values
            
        Returns:
            Merged configuration
        """
        config_dict = asdict(base_config)
        
        # Recursive merge function
        def merge_dicts(base_dict: Dict[str, Any], override_dict: Dict[str, Any]) -> Dict[str, Any]:
            for key, value in override_dict.items():
                if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                    base_dict[key] = merge_dicts(base_dict[key], value)
                else:
                    base_dict[key] = value
            return base_dict
        
        merged_dict = merge_dicts(config_dict, override_config)
        return self._create_configuration_from_dict(merged_dict)
    
    def get_default_configuration(self) -> OptimizerLauncherConfiguration:
        """Get default configuration."""
        return OptimizerLauncherConfiguration(
            optimization_target="sharpe_ratio",
            algorithm_type_name="SampleAlgorithm",
            algorithm_location="algorithm.py",
            parameter_file="parameters.json",
            mode=OptimizerLauncherMode.LOCAL,
            max_concurrent_backtests=4,
            worker_timeout=3600,
            data_folder="data",
            output_folder="output",
            results_file="optimization_results.json",
            enable_checkpointing=True,
            checkpoint_frequency=50,
            fault_tolerance=True,
            result_caching=True
        )


def create_sample_configuration() -> OptimizerLauncherConfiguration:
    """Create a sample configuration for testing."""
    return (OptimizerLauncherConfigurationBuilder()
            .with_algorithm("SampleAlgorithm", "algorithm.py")
            .with_parameters("parameters.json")
            .with_mode(OptimizerLauncherMode.LOCAL)
            .with_concurrent_backtests(4)
            .with_data_folder("data")
            .with_output_folder("output")
            .with_target(OptimizerTargetConfig(
                name="sharpe_ratio",
                objectives=["sharpe_ratio"],
                maximize=True
            ))
            .with_worker_config(WorkerConfig(
                worker_type="local",
                max_workers=4,
                timeout=3600
            ))
            .with_checkpointing(True, 50)
            .with_fault_tolerance(True)
            .build())