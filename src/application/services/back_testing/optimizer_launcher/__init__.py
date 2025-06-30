"""
QuantConnect Lean Optimizer.Launcher Module

This module provides a comprehensive optimization launcher that orchestrates
distributed parameter optimization campaigns across multiple worker nodes.

Key Components:
- OptimizerLauncher: Main orchestrator for optimization campaigns
- Configuration: Advanced configuration management with multiple sources
- WorkerManager: Manages local, Docker, and cloud worker nodes
- ResultCoordinator: Coordinates results collection and analysis
- NodePacket: Job distribution packets for worker nodes

Example Usage:
    ```python
    from optimizer_launcher import (
        OptimizerLauncher,
        OptimizerLauncherConfiguration,
        OptimizerLauncherMode
    )
    
    # Create configuration
    config = OptimizerLauncherConfiguration(
        optimization_target="sharpe_ratio",
        algorithm_type_name="MyAlgorithm",
        algorithm_location="my_algorithm.py",
        parameter_file="parameters.json",
        mode=OptimizerLauncherMode.LOCAL,
        max_concurrent_backtests=4
    )
    
    # Create and run launcher
    launcher = OptimizerLauncher()
    launcher.initialize(config)
    result = await launcher.run_optimization()
    ```
"""

# Core interfaces
from .interfaces import (
    IOptimizerLauncher,
    IOptimizerNodePacket,
    IWorkerManager,
    IResultCoordinator,
    ICheckpointManager,
    IOptimizationProgressReporter,
    IDistributedOptimizationTarget,
    IOptimizerLauncherFactory,
    OptimizerLauncherMode,
    OptimizerLauncherStatus,
    WorkerStatus,
    OptimizerLauncherConfiguration,
    OptimizerLauncherException,
    WorkerManagementException,
    JobSubmissionException,
    ResultCoordinationException,
    CheckpointException,
    DistributedOptimizationException
)

# Configuration management
from .configuration import (
    OptimizerLauncherConfigurationBuilder,
    OptimizerLauncherConfigurationManager,
    OptimizerParameterConfig,
    OptimizerTargetConfig,
    WorkerConfig,
    CloudConfig,
    create_sample_configuration
)

# Node packet system
from .node_packet import (
    OptimizerNodePacket,
    NodePacketFactory,
    AlgorithmConfiguration,
    JobMetadata,
    ResourceRequirements
)

# Worker management
from .worker_manager import (
    LocalWorkerManager,
    DockerWorkerManager,
    WorkerManagerFactory,
    WorkerInfo
)

# Result coordination
from .result_coordinator import (
    ResultCoordinator,
    OptimizationCampaignResult,
    ProgressReporter
)

# Main launcher
from .optimizer_launcher import (
    OptimizerLauncher,
    OptimizerLauncherFactory
)

# Version information
__version__ = "1.0.0"
__author__ = "Claude Code Generator"

# Module metadata
__all__ = [
    # Core interfaces
    "IOptimizerLauncher",
    "IOptimizerNodePacket", 
    "IWorkerManager",
    "IResultCoordinator",
    "ICheckpointManager",
    "IOptimizationProgressReporter",
    "IDistributedOptimizationTarget",
    "IOptimizerLauncherFactory",
    
    # Enums and data classes
    "OptimizerLauncherMode",
    "OptimizerLauncherStatus",
    "WorkerStatus",
    "OptimizerLauncherConfiguration",
    
    # Exceptions
    "OptimizerLauncherException",
    "WorkerManagementException",
    "JobSubmissionException",
    "ResultCoordinationException",
    "CheckpointException",
    "DistributedOptimizationException",
    
    # Configuration
    "OptimizerLauncherConfigurationBuilder",
    "OptimizerLauncherConfigurationManager",
    "OptimizerParameterConfig",
    "OptimizerTargetConfig",
    "WorkerConfig",
    "CloudConfig",
    "create_sample_configuration",
    
    # Node packets
    "OptimizerNodePacket",
    "NodePacketFactory",
    "AlgorithmConfiguration",
    "JobMetadata",
    "ResourceRequirements",
    
    # Worker management
    "LocalWorkerManager",
    "DockerWorkerManager",
    "WorkerManagerFactory",
    "WorkerInfo",
    
    # Result coordination
    "ResultCoordinator",
    "OptimizationCampaignResult",
    "ProgressReporter",
    
    # Main components
    "OptimizerLauncher",
    "OptimizerLauncherFactory"
]


def get_version() -> str:
    """Get the current version of the optimizer launcher module."""
    return __version__


def create_local_launcher(max_workers: int = 4, 
                         output_folder: str = "output") -> OptimizerLauncher:
    """
    Convenience function to create a local optimizer launcher.
    
    Args:
        max_workers: Maximum number of worker processes
        output_folder: Output directory for results
        
    Returns:
        Configured OptimizerLauncher instance
    """
    return OptimizerLauncherFactory.create_launcher(
        mode=OptimizerLauncherMode.LOCAL
    )


def create_cloud_launcher(worker_image: str,
                         cloud_provider: str = "aws",
                         max_workers: int = 10) -> OptimizerLauncher:
    """
    Convenience function to create a cloud optimizer launcher.
    
    Args:
        worker_image: Docker image for worker nodes
        cloud_provider: Cloud provider (aws, azure, gcp)
        max_workers: Maximum number of worker instances
        
    Returns:
        Configured OptimizerLauncher instance
    """
    return OptimizerLauncherFactory.create_launcher(
        mode=OptimizerLauncherMode.CLOUD
    )


def load_configuration_from_file(config_path: str) -> OptimizerLauncherConfiguration:
    """
    Load optimizer launcher configuration from file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        OptimizerLauncherConfiguration instance
    """
    manager = OptimizerLauncherConfigurationManager()
    return manager.load_from_file(config_path)


def validate_configuration(config: OptimizerLauncherConfiguration) -> bool:
    """
    Validate optimizer launcher configuration.
    
    Args:
        config: Configuration to validate
        
    Returns:
        True if configuration is valid
        
    Raises:
        OptimizerLauncherException: If configuration is invalid
    """
    manager = OptimizerLauncherConfigurationManager()
    errors = manager.validate_configuration(config)
    
    if errors:
        error_msg = "; ".join(errors)
        raise OptimizerLauncherException(f"Configuration validation failed: {error_msg}")
    
    return True


# Utility functions for common operations
async def run_optimization_campaign(config: OptimizerLauncherConfiguration) -> OptimizationCampaignResult:
    """
    Run a complete optimization campaign.
    
    Args:
        config: Optimizer launcher configuration
        
    Returns:
        OptimizationCampaignResult with all results and statistics
    """
    launcher = OptimizerLauncher()
    
    if not launcher.initialize(config):
        raise OptimizerLauncherException("Failed to initialize optimizer launcher")
    
    try:
        return await launcher.run_optimization()
    except Exception as e:
        launcher.stop_optimization()
        raise OptimizerLauncherException(f"Optimization campaign failed: {e}")


def create_parameter_config(name: str,
                           param_type: str,
                           min_value: float = None,
                           max_value: float = None,
                           values: list = None) -> OptimizerParameterConfig:
    """
    Create an optimizer parameter configuration.
    
    Args:
        name: Parameter name
        param_type: Parameter type (int, float, bool, categorical, string)
        min_value: Minimum value for numeric parameters
        max_value: Maximum value for numeric parameters
        values: List of values for categorical parameters
        
    Returns:
        OptimizerParameterConfig instance
    """
    return OptimizerParameterConfig(
        name=name,
        type=param_type,
        min_value=min_value,
        max_value=max_value,
        values=values
    )


def create_target_config(name: str,
                        objectives: list,
                        maximize: bool = True,
                        weight: float = 1.0) -> OptimizerTargetConfig:
    """
    Create an optimizer target configuration.
    
    Args:
        name: Target name
        objectives: List of objective metrics
        maximize: Whether to maximize or minimize the objective
        weight: Weight for multi-objective optimization
        
    Returns:
        OptimizerTargetConfig instance
    """
    return OptimizerTargetConfig(
        name=name,
        objectives=objectives,
        maximize=maximize,
        weight=weight
    )


# Module documentation
__doc__ = """
QuantConnect Lean Optimizer.Launcher Module

This module provides a comprehensive distributed optimization framework that combines
optimization algorithms with distributed execution capabilities across multiple worker nodes.

## Architecture

The module follows a modular architecture with clear separation of concerns:

### Core Components

1. **OptimizerLauncher**: Main orchestrator that coordinates the entire optimization campaign
2. **Configuration Management**: Advanced configuration system with multiple sources
3. **Worker Management**: Handles local processes, Docker containers, and cloud instances
4. **Result Coordination**: Collects, aggregates, and analyzes optimization results
5. **Node Packets**: Job distribution system for worker coordination

### Execution Modes

- **Local Mode**: Uses local processes for parallel execution
- **Cloud Mode**: Leverages cloud instances for scalable execution
- **Distributed Mode**: Combines multiple execution environments
- **Hybrid Mode**: Optimized mix of local and cloud resources

### Key Features

- **Fault Tolerance**: Automatic job retry and error recovery
- **Progress Tracking**: Real-time optimization progress monitoring
- **Result Analysis**: Comprehensive statistics and parameter analysis
- **Checkpointing**: Automatic campaign state saving and recovery
- **Flexible Configuration**: JSON files, environment variables, and programmatic setup

## Usage Examples

### Basic Local Optimization

```python
from optimizer_launcher import *

# Create configuration
config = (OptimizerLauncherConfigurationBuilder()
         .with_algorithm("MyAlgorithm", "algorithm.py")
         .with_parameters("params.json")
         .with_mode(OptimizerLauncherMode.LOCAL)
         .with_concurrent_backtests(4)
         .build())

# Run optimization
launcher = OptimizerLauncher()
launcher.initialize(config)
result = await launcher.run_optimization()

print(f"Best fitness: {result.best_result.fitness_score}")
```

### Advanced Cloud Optimization

```python
# Cloud configuration
cloud_config = (OptimizerLauncherConfigurationBuilder()
               .with_algorithm("MyAlgorithm", "algorithm.py")
               .with_parameters("params.json")
               .with_mode(OptimizerLauncherMode.CLOUD)
               .with_concurrent_backtests(20)
               .with_cloud_config(CloudConfig(
                   provider="aws",
                   region="us-east-1",
                   instance_type="c5.xlarge",
                   image_name="my-optimizer:latest"
               ))
               .build())

# Run with progress monitoring
launcher = OptimizerLauncher()
launcher.initialize(cloud_config)

# Monitor progress
async def monitor_progress():
    while launcher.status != OptimizerLauncherStatus.COMPLETED:
        results = await launcher.get_live_results()
        print(f"Progress: {launcher.progress:.1%}")
        await asyncio.sleep(10)

# Run both tasks
await asyncio.gather(
    launcher.run_optimization(),
    monitor_progress()
)
```

### Configuration from File

```python
# Load from JSON configuration
config = load_configuration_from_file("optimization_config.json")
validate_configuration(config)

# Run optimization campaign
result = await run_optimization_campaign(config)

# Export results
await result.export_results("results.json", format="json")
await result.export_results("results.csv", format="csv")
```

## Configuration Schema

The module supports comprehensive configuration through JSON files:

```json
{
  "optimization_target": "sharpe_ratio",
  "algorithm_type_name": "MyAlgorithm",
  "algorithm_location": "algorithm.py",
  "parameter_file": "parameters.json",
  "mode": "local",
  "max_concurrent_backtests": 4,
  "data_folder": "data",
  "output_folder": "output",
  "enable_checkpointing": true,
  "checkpoint_frequency": 50,
  "fault_tolerance": true,
  "worker_config": {
    "worker_type": "local",
    "max_workers": 4,
    "timeout": 3600
  },
  "cloud_config": {
    "provider": "aws",
    "region": "us-east-1",
    "instance_type": "c5.xlarge",
    "image_name": "optimizer:latest"
  }
}
```

## Integration

The module integrates seamlessly with the existing DDD architecture:

- **Domain Layer**: Uses existing optimization interfaces and contracts
- **Application Layer**: Extends existing services with distributed capabilities  
- **Infrastructure Layer**: Leverages existing data and execution components

## Performance

The module is designed for high-performance optimization campaigns:

- **Concurrent Execution**: Multiple workers running in parallel
- **Efficient Communication**: Minimal overhead job distribution
- **Result Caching**: Intelligent result storage and retrieval
- **Resource Optimization**: Dynamic worker scaling based on demand

## Monitoring and Observability

Comprehensive monitoring capabilities:

- **Real-time Progress**: Live optimization metrics and statistics
- **Worker Health**: Individual worker status and performance tracking
- **Error Tracking**: Detailed error logging and recovery mechanisms
- **Performance Analytics**: Execution time analysis and optimization suggestions
"""