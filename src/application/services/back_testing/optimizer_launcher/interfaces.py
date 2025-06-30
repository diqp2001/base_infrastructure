"""
QuantConnect Lean Optimizer.Launcher Interfaces

Defines the core interfaces for the optimizer launcher module including 
optimization target evaluation, worker management, and result coordination.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, AsyncIterator, Callable
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import asyncio

# Import from existing modules
from ..optimizer.interfaces import IOptimizer, IOptimizationTarget
from ..launcher.interfaces import LauncherConfiguration, ILauncher


class OptimizerLauncherMode(Enum):
    """Optimizer launcher execution modes."""
    LOCAL = "local"
    CLOUD = "cloud"
    DISTRIBUTED = "distributed"
    HYBRID = "hybrid"


class OptimizerLauncherStatus(Enum):
    """Optimizer launcher execution status."""
    INITIALIZING = "initializing"
    LOADING_CONFIG = "loading_config"
    STARTING_WORKERS = "starting_workers"
    OPTIMIZING = "optimizing"
    COLLECTING_RESULTS = "collecting_results"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkerStatus(Enum):
    """Individual worker node status."""
    IDLE = "idle"
    BUSY = "busy"
    STARTING = "starting"
    STOPPING = "stopping"
    FAILED = "failed"
    DISCONNECTED = "disconnected"


@dataclass
class OptimizerLauncherConfiguration:
    """Configuration for optimizer launcher execution."""
    
    # Basic optimization settings
    optimization_target: str
    algorithm_type_name: str
    algorithm_location: str
    parameter_file: str
    
    # Execution settings
    mode: OptimizerLauncherMode = OptimizerLauncherMode.LOCAL
    max_concurrent_backtests: int = 4
    worker_timeout: int = 3600  # seconds
    
    # Data and output settings
    data_folder: str = "data"
    output_folder: str = "output"
    results_file: str = "optimization_results.json"
    
    # Launcher configuration
    launcher_config: Optional[LauncherConfiguration] = None
    
    # Advanced settings
    enable_checkpointing: bool = True
    checkpoint_frequency: int = 50  # results
    fault_tolerance: bool = True
    result_caching: bool = True
    
    # Cloud/distributed settings
    cloud_provider: Optional[str] = None
    worker_image: Optional[str] = None
    resource_requirements: Dict[str, Any] = None
    
    # Custom configurations
    custom_config: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.resource_requirements is None:
            self.resource_requirements = {"cpu": 1, "memory": "2Gi"}
        if self.custom_config is None:
            self.custom_config = {}


class IOptimizerLauncher(ABC):
    """Main interface for the optimizer launcher."""
    
    @abstractmethod
    def initialize(self, config: OptimizerLauncherConfiguration) -> bool:
        """
        Initialize the optimizer launcher with given configuration.
        
        Args:
            config: Optimizer launcher configuration
            
        Returns:
            True if initialization successful
        """
        pass
    
    @abstractmethod
    async def run_optimization(self) -> 'OptimizationCampaignResult':
        """
        Run the optimization campaign.
        
        Returns:
            Campaign result with all optimization statistics
        """
        pass
    
    @abstractmethod
    def stop_optimization(self) -> bool:
        """
        Stop the optimization campaign gracefully.
        
        Returns:
            True if stop successful
        """
        pass
    
    @property
    @abstractmethod
    def status(self) -> OptimizerLauncherStatus:
        """Gets the current launcher status."""
        pass
    
    @property
    @abstractmethod
    def progress(self) -> float:
        """Gets the optimization progress (0.0 to 1.0)."""
        pass
    
    @abstractmethod
    async def get_live_results(self) -> List['OptimizationResult']:
        """Get current optimization results in real-time."""
        pass


class IOptimizerNodePacket(ABC):
    """Interface for optimization job packets sent to workers."""
    
    @property
    @abstractmethod
    def job_id(self) -> str:
        """Unique job identifier."""
        pass
    
    @property
    @abstractmethod
    def parameter_set(self) -> 'OptimizationParameterSet':
        """Parameter set to evaluate."""
        pass
    
    @property
    @abstractmethod
    def algorithm_config(self) -> Dict[str, Any]:
        """Algorithm configuration."""
        pass
    
    @property
    @abstractmethod
    def created_time(self) -> datetime:
        """Job creation timestamp."""
        pass
    
    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert packet to dictionary for serialization."""
        pass
    
    @abstractmethod
    def from_dict(self, data: Dict[str, Any]) -> 'IOptimizerNodePacket':
        """Create packet from dictionary."""
        pass


class IWorkerManager(ABC):
    """Interface for managing worker nodes."""
    
    @abstractmethod
    async def start_workers(self, count: int) -> bool:
        """
        Start the specified number of worker nodes.
        
        Args:
            count: Number of workers to start
            
        Returns:
            True if all workers started successfully
        """
        pass
    
    @abstractmethod
    async def stop_workers(self) -> bool:
        """
        Stop all worker nodes gracefully.
        
        Returns:
            True if all workers stopped successfully
        """
        pass
    
    @abstractmethod
    async def submit_job(self, packet: IOptimizerNodePacket) -> str:
        """
        Submit a job to an available worker.
        
        Args:
            packet: Job packet to submit
            
        Returns:
            Job ID for tracking
        """
        pass
    
    @abstractmethod
    async def get_job_result(self, job_id: str) -> Optional['OptimizationResult']:
        """
        Get result for a specific job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            Optimization result if available
        """
        pass
    
    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a specific job.
        
        Args:
            job_id: Job identifier
            
        Returns:
            True if cancellation successful
        """
        pass
    
    @abstractmethod
    def get_worker_count(self) -> int:
        """Get total number of workers."""
        pass
    
    @abstractmethod
    def get_active_workers(self) -> int:
        """Get number of active workers."""
        pass
    
    @abstractmethod
    def get_worker_status(self) -> Dict[str, WorkerStatus]:
        """Get status of all workers."""
        pass


class IResultCoordinator(ABC):
    """Interface for coordinating optimization results."""
    
    @abstractmethod
    async def register_result(self, result: 'OptimizationResult') -> None:
        """
        Register a new optimization result.
        
        Args:
            result: Result to register
        """
        pass
    
    @abstractmethod
    async def get_best_results(self, count: int = 10) -> List['OptimizationResult']:
        """
        Get the best optimization results.
        
        Args:
            count: Number of results to return
            
        Returns:
            List of best results
        """
        pass
    
    @abstractmethod
    async def get_all_results(self) -> List['OptimizationResult']:
        """Get all optimization results."""
        pass
    
    @abstractmethod
    async def export_results(self, file_path: str, format: str = "json") -> bool:
        """
        Export results to file.
        
        Args:
            file_path: Path to output file
            format: Export format (json, csv, excel)
            
        Returns:
            True if export successful
        """
        pass
    
    @abstractmethod
    def get_statistics(self) -> 'OptimizationStatistics':
        """Get optimization statistics."""
        pass


class ICheckpointManager(ABC):
    """Interface for managing optimization checkpoints."""
    
    @abstractmethod
    async def save_checkpoint(self, data: Dict[str, Any]) -> bool:
        """
        Save optimization checkpoint.
        
        Args:
            data: Checkpoint data
            
        Returns:
            True if save successful
        """
        pass
    
    @abstractmethod
    async def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """
        Load latest optimization checkpoint.
        
        Returns:
            Checkpoint data if available
        """
        pass
    
    @abstractmethod
    async def clear_checkpoints(self) -> bool:
        """
        Clear all checkpoints.
        
        Returns:
            True if clear successful
        """
        pass


class IOptimizationProgressReporter(ABC):
    """Interface for reporting optimization progress."""
    
    @abstractmethod
    def report_campaign_start(self, config: OptimizerLauncherConfiguration) -> None:
        """Report optimization campaign start."""
        pass
    
    @abstractmethod
    def report_progress_update(self, 
                              completed: int,
                              total: int,
                              best_fitness: float,
                              elapsed_time: float,
                              estimated_completion: Optional[datetime] = None) -> None:
        """Report progress update."""
        pass
    
    @abstractmethod
    def report_result_received(self, result: 'OptimizationResult') -> None:
        """Report new result received."""
        pass
    
    @abstractmethod
    def report_worker_status_change(self, worker_id: str, status: WorkerStatus) -> None:
        """Report worker status change."""
        pass
    
    @abstractmethod
    def report_campaign_completion(self, statistics: 'OptimizationStatistics') -> None:
        """Report campaign completion."""
        pass
    
    @abstractmethod
    def report_error(self, error: Exception, context: Dict[str, Any]) -> None:
        """Report error during optimization."""
        pass


class IDistributedOptimizationTarget(IOptimizationTarget):
    """Extended optimization target for distributed execution."""
    
    @abstractmethod
    async def evaluate_distributed(self, 
                                  packet: IOptimizerNodePacket,
                                  worker_id: str) -> 'OptimizationResult':
        """
        Evaluate parameter set in distributed environment.
        
        Args:
            packet: Job packet with parameters
            worker_id: Worker node identifier
            
        Returns:
            Optimization result
        """
        pass
    
    @abstractmethod
    def prepare_for_distribution(self) -> Dict[str, Any]:
        """Prepare target for distribution to workers."""
        pass


class IOptimizerLauncherFactory(ABC):
    """Factory interface for creating optimizer launcher instances."""
    
    @abstractmethod
    def create_launcher(self, 
                       mode: OptimizerLauncherMode,
                       config: OptimizerLauncherConfiguration) -> IOptimizerLauncher:
        """
        Create optimizer launcher instance.
        
        Args:
            mode: Launcher mode
            config: Configuration
            
        Returns:
            Optimizer launcher instance
        """
        pass
    
    @abstractmethod
    def get_supported_modes(self) -> List[OptimizerLauncherMode]:
        """Get list of supported launcher modes."""
        pass


# Exception classes for error handling
class OptimizerLauncherException(Exception):
    """Base exception for optimizer launcher operations."""
    
    def __init__(self, message: str, inner_exception: Optional[Exception] = None):
        super().__init__(message)
        self.inner_exception = inner_exception


class WorkerManagementException(OptimizerLauncherException):
    """Exception for worker management errors."""
    pass


class JobSubmissionException(OptimizerLauncherException):
    """Exception for job submission errors."""
    pass


class ResultCoordinationException(OptimizerLauncherException):
    """Exception for result coordination errors."""
    pass


class CheckpointException(OptimizerLauncherException):
    """Exception for checkpoint operations."""
    pass


class DistributedOptimizationException(OptimizerLauncherException):
    """Exception for distributed optimization errors."""
    pass