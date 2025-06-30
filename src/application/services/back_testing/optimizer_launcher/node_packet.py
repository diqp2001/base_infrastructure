"""
QuantConnect Lean Optimizer.Launcher Node Packet

Defines the job packets that are distributed to worker nodes for execution.
Contains parameter sets, algorithm configuration, and job metadata.
"""

import json
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, asdict, field

from .interfaces import IOptimizerNodePacket
from ..optimizer.parameter_management import OptimizationParameterSet
from ..common.enums import SecurityType, Resolution


@dataclass
class JobMetadata:
    """Metadata for optimization jobs."""
    
    job_id: str
    campaign_id: str
    created_time: datetime
    priority: int = 0
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 3600
    tags: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.job_id:
            self.job_id = str(uuid.uuid4())
        if not self.created_time:
            self.created_time = datetime.now(timezone.utc)


@dataclass
class AlgorithmConfiguration:
    """Configuration for algorithm execution."""
    
    algorithm_type_name: str
    algorithm_location: str
    start_date: str
    end_date: str
    initial_cash: float = 100000.0
    
    # Data configuration
    data_folder: str = "data"
    resolution: Resolution = Resolution.DAILY
    security_types: List[SecurityType] = field(default_factory=lambda: [SecurityType.EQUITY])
    
    # Execution configuration
    environment: str = "backtesting"
    live_mode: bool = False
    
    # Custom settings
    custom_config: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary with proper enum handling."""
        result = asdict(self)
        result['resolution'] = self.resolution.value if hasattr(self.resolution, 'value') else str(self.resolution)
        result['security_types'] = [st.value if hasattr(st, 'value') else str(st) for st in self.security_types]
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlgorithmConfiguration':
        """Create from dictionary with proper enum handling."""
        # Handle enum conversion
        if 'resolution' in data:
            if isinstance(data['resolution'], str):
                try:
                    data['resolution'] = Resolution(data['resolution'])
                except (ValueError, AttributeError):
                    data['resolution'] = Resolution.DAILY
        
        if 'security_types' in data:
            security_types = []
            for st in data['security_types']:
                if isinstance(st, str):
                    try:
                        security_types.append(SecurityType(st))
                    except (ValueError, AttributeError):
                        security_types.append(SecurityType.EQUITY)
                else:
                    security_types.append(st)
            data['security_types'] = security_types
        
        return cls(**data)


@dataclass
class ResourceRequirements:
    """Resource requirements for job execution."""
    
    cpu_cores: float = 1.0
    memory_mb: int = 2048
    disk_mb: int = 1024
    network_mb: int = 100
    gpu_required: bool = False
    gpu_memory_mb: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResourceRequirements':
        """Create from dictionary."""
        return cls(**data)


class OptimizerNodePacket(IOptimizerNodePacket):
    """
    Job packet containing optimization parameters and configuration 
    that is sent to worker nodes for execution.
    """
    
    def __init__(self, 
                 parameter_set: OptimizationParameterSet,
                 algorithm_config: AlgorithmConfiguration,
                 job_metadata: Optional[JobMetadata] = None,
                 resource_requirements: Optional[ResourceRequirements] = None):
        """
        Initialize optimizer node packet.
        
        Args:
            parameter_set: Parameters to optimize
            algorithm_config: Algorithm configuration
            job_metadata: Job metadata (generated if not provided)
            resource_requirements: Resource requirements (default if not provided)
        """
        self._parameter_set = parameter_set
        self._algorithm_config = algorithm_config
        self._job_metadata = job_metadata or JobMetadata(
            job_id=str(uuid.uuid4()),
            campaign_id="default",
            created_time=datetime.now(timezone.utc)
        )
        self._resource_requirements = resource_requirements or ResourceRequirements()
        
        # Execution tracking
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None
        self._worker_id: Optional[str] = None
        self._status: str = "pending"
        self._error_message: Optional[str] = None
    
    @property
    def job_id(self) -> str:
        """Unique job identifier."""
        return self._job_metadata.job_id
    
    @property
    def campaign_id(self) -> str:
        """Campaign identifier."""
        return self._job_metadata.campaign_id
    
    @property
    def parameter_set(self) -> OptimizationParameterSet:
        """Parameter set to evaluate."""
        return self._parameter_set
    
    @property
    def algorithm_config(self) -> Dict[str, Any]:
        """Algorithm configuration."""
        return self._algorithm_config.to_dict()
    
    @property
    def created_time(self) -> datetime:
        """Job creation timestamp."""
        return self._job_metadata.created_time
    
    @property
    def metadata(self) -> JobMetadata:
        """Job metadata."""
        return self._job_metadata
    
    @property
    def resource_requirements(self) -> ResourceRequirements:
        """Resource requirements."""
        return self._resource_requirements
    
    @property
    def start_time(self) -> Optional[datetime]:
        """Job start time."""
        return self._start_time
    
    @property
    def end_time(self) -> Optional[datetime]:
        """Job end time."""
        return self._end_time
    
    @property
    def duration(self) -> Optional[float]:
        """Job duration in seconds."""
        if self._start_time and self._end_time:
            return (self._end_time - self._start_time).total_seconds()
        return None
    
    @property
    def worker_id(self) -> Optional[str]:
        """Worker ID executing the job."""
        return self._worker_id
    
    @property
    def status(self) -> str:
        """Current job status."""
        return self._status
    
    @property
    def error_message(self) -> Optional[str]:
        """Error message if job failed."""
        return self._error_message
    
    def start_execution(self, worker_id: str) -> None:
        """Mark job as started."""
        self._worker_id = worker_id
        self._start_time = datetime.now(timezone.utc)
        self._status = "running"
    
    def complete_execution(self) -> None:
        """Mark job as completed."""
        self._end_time = datetime.now(timezone.utc)
        self._status = "completed"
    
    def fail_execution(self, error_message: str) -> None:
        """Mark job as failed."""
        self._end_time = datetime.now(timezone.utc)
        self._status = "failed"
        self._error_message = error_message
    
    def can_retry(self) -> bool:
        """Check if job can be retried."""
        return (self._status == "failed" and 
                self._job_metadata.retry_count < self._job_metadata.max_retries)
    
    def increment_retry(self) -> None:
        """Increment retry count."""
        self._job_metadata.retry_count += 1
        self._status = "pending"
        self._error_message = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert packet to dictionary for serialization."""
        return {
            "job_metadata": {
                "job_id": self._job_metadata.job_id,
                "campaign_id": self._job_metadata.campaign_id,
                "created_time": self._job_metadata.created_time.isoformat(),
                "priority": self._job_metadata.priority,
                "retry_count": self._job_metadata.retry_count,
                "max_retries": self._job_metadata.max_retries,
                "timeout_seconds": self._job_metadata.timeout_seconds,
                "tags": self._job_metadata.tags
            },
            "parameter_set": self._parameter_set.to_dict(),
            "algorithm_config": self._algorithm_config.to_dict(),
            "resource_requirements": self._resource_requirements.to_dict(),
            "execution_info": {
                "start_time": self._start_time.isoformat() if self._start_time else None,
                "end_time": self._end_time.isoformat() if self._end_time else None,
                "worker_id": self._worker_id,
                "status": self._status,
                "error_message": self._error_message
            }
        }
    
    def from_dict(self, data: Dict[str, Any]) -> 'OptimizerNodePacket':
        """Create packet from dictionary."""
        # Create job metadata
        metadata_data = data["job_metadata"]
        job_metadata = JobMetadata(
            job_id=metadata_data["job_id"],
            campaign_id=metadata_data["campaign_id"],
            created_time=datetime.fromisoformat(metadata_data["created_time"]),
            priority=metadata_data.get("priority", 0),
            retry_count=metadata_data.get("retry_count", 0),
            max_retries=metadata_data.get("max_retries", 3),
            timeout_seconds=metadata_data.get("timeout_seconds", 3600),
            tags=metadata_data.get("tags", {})
        )
        
        # Create parameter set
        parameter_set = OptimizationParameterSet.from_dict(data["parameter_set"])
        
        # Create algorithm config
        algorithm_config = AlgorithmConfiguration.from_dict(data["algorithm_config"])
        
        # Create resource requirements
        resource_requirements = ResourceRequirements.from_dict(data["resource_requirements"])
        
        # Create packet
        packet = OptimizerNodePacket(
            parameter_set=parameter_set,
            algorithm_config=algorithm_config,
            job_metadata=job_metadata,
            resource_requirements=resource_requirements
        )
        
        # Set execution info
        exec_info = data.get("execution_info", {})
        if exec_info.get("start_time"):
            packet._start_time = datetime.fromisoformat(exec_info["start_time"])
        if exec_info.get("end_time"):
            packet._end_time = datetime.fromisoformat(exec_info["end_time"])
        packet._worker_id = exec_info.get("worker_id")
        packet._status = exec_info.get("status", "pending")
        packet._error_message = exec_info.get("error_message")
        
        return packet
    
    def to_json(self) -> str:
        """Convert packet to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'OptimizerNodePacket':
        """Create packet from JSON string."""
        data = json.loads(json_str)
        return cls().from_dict(data)
    
    def clone(self) -> 'OptimizerNodePacket':
        """Create a copy of the packet."""
        return self.from_dict(self.to_dict())
    
    def __str__(self) -> str:
        """String representation."""
        return (f"OptimizerNodePacket(job_id={self.job_id}, "
                f"campaign_id={self.campaign_id}, "
                f"status={self.status}, "
                f"parameters={len(self.parameter_set.parameters)})")
    
    def __repr__(self) -> str:
        """Detailed representation."""
        return (f"OptimizerNodePacket(job_id={self.job_id}, "
                f"campaign_id={self.campaign_id}, "
                f"status={self.status}, "
                f"worker_id={self.worker_id}, "
                f"created_time={self.created_time}, "
                f"parameters={self.parameter_set})")


class NodePacketFactory:
    """Factory for creating optimizer node packets."""
    
    @staticmethod
    def create_packet(parameter_set: OptimizationParameterSet,
                      algorithm_config: AlgorithmConfiguration,
                      campaign_id: str = "default",
                      priority: int = 0,
                      timeout_seconds: int = 3600,
                      tags: Optional[Dict[str, str]] = None) -> OptimizerNodePacket:
        """
        Create a new optimizer node packet.
        
        Args:
            parameter_set: Parameters to optimize
            algorithm_config: Algorithm configuration
            campaign_id: Campaign identifier
            priority: Job priority
            timeout_seconds: Job timeout
            tags: Additional tags
            
        Returns:
            New optimizer node packet
        """
        job_metadata = JobMetadata(
            job_id=str(uuid.uuid4()),
            campaign_id=campaign_id,
            created_time=datetime.now(timezone.utc),
            priority=priority,
            timeout_seconds=timeout_seconds,
            tags=tags or {}
        )
        
        return OptimizerNodePacket(
            parameter_set=parameter_set,
            algorithm_config=algorithm_config,
            job_metadata=job_metadata
        )
    
    @staticmethod
    def create_batch_packets(parameter_sets: List[OptimizationParameterSet],
                            algorithm_config: AlgorithmConfiguration,
                            campaign_id: str = "default",
                            base_priority: int = 0) -> List[OptimizerNodePacket]:
        """
        Create a batch of optimizer node packets.
        
        Args:
            parameter_sets: List of parameter sets
            algorithm_config: Algorithm configuration
            campaign_id: Campaign identifier
            base_priority: Base priority for jobs
            
        Returns:
            List of optimizer node packets
        """
        packets = []
        for i, parameter_set in enumerate(parameter_sets):
            packet = NodePacketFactory.create_packet(
                parameter_set=parameter_set,
                algorithm_config=algorithm_config,
                campaign_id=campaign_id,
                priority=base_priority + i
            )
            packets.append(packet)
        
        return packets
    
    @staticmethod
    def create_retry_packet(original_packet: OptimizerNodePacket) -> OptimizerNodePacket:
        """
        Create a retry packet from an original packet.
        
        Args:
            original_packet: Original packet to retry
            
        Returns:
            New retry packet
        """
        if not original_packet.can_retry():
            raise ValueError("Packet cannot be retried")
        
        # Clone the packet and increment retry count
        retry_packet = original_packet.clone()
        retry_packet.increment_retry()
        
        return retry_packet