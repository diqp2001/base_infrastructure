"""
Algorithm node packet for algorithm configuration and deployment.
"""

from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from decimal import Decimal

from ..common.enums import Language, AlgorithmStatus, BrokerageEnvironment


@dataclass
class AlgorithmNodePacket:
    """
    Configuration packet for algorithm deployment and execution.
    Contains all necessary information to run an algorithm.
    """
    
    # Basic identification
    algorithm_id: str
    algorithm_name: str
    user_id: str = ""
    project_id: str = ""
    
    # Algorithm source
    algorithm_file_path: Optional[str] = None
    source_code: Optional[str] = None
    language: Language = Language.PYTHON
    
    # Execution configuration
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    starting_capital: Decimal = field(default=Decimal('100000'))
    
    # Environment settings
    environment: BrokerageEnvironment = BrokerageEnvironment.PAPER
    brokerage: str = "Simulation"
    data_provider: str = "FileSystem"
    
    # Algorithm parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Execution settings
    live_mode: bool = False
    paper_trading: bool = True
    automatic_restart: bool = False
    
    # Resource limits
    max_memory_mb: int = 1024
    max_cpu_percent: float = 50.0
    timeout_minutes: int = 0  # 0 = no timeout
    
    # Data settings
    data_folder: str = "data"
    universe_selection: Optional[str] = None
    benchmark: str = "SPY"
    
    # Risk management
    max_drawdown_percent: float = 20.0
    daily_loss_limit: Optional[Decimal] = None
    
    # Monitoring
    status: AlgorithmStatus = AlgorithmStatus.INITIALIZING
    created_time: datetime = field(default_factory=datetime.utcnow)
    deployed_time: Optional[datetime] = None
    completed_time: Optional[datetime] = None
    
    # Output settings
    output_folder: str = "output"
    generate_charts: bool = True
    generate_statistics: bool = True
    
    # Dependencies
    required_packages: List[str] = field(default_factory=list)
    custom_libraries: List[str] = field(default_factory=list)
    
    # Debug settings
    debug_mode: bool = False
    log_level: str = "INFO"
    
    def __post_init__(self):
        """Post-initialization validation and setup."""
        # Ensure starting_capital is Decimal
        if not isinstance(self.starting_capital, Decimal):
            self.starting_capital = Decimal(str(self.starting_capital))
        
        # Validate daily_loss_limit
        if self.daily_loss_limit is not None and not isinstance(self.daily_loss_limit, Decimal):
            self.daily_loss_limit = Decimal(str(self.daily_loss_limit))
        
        # Set default end date if not provided
        if self.start_date and not self.end_date:
            self.end_date = datetime.utcnow()
        
        # Validate date range
        if self.start_date and self.end_date and self.start_date >= self.end_date:
            raise ValueError("Start date must be before end date")
    
    def validate(self) -> List[str]:
        """
        Validate the packet configuration.
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Required fields
        if not self.algorithm_id:
            errors.append("Algorithm ID is required")
        
        if not self.algorithm_name:
            errors.append("Algorithm name is required")
        
        # Algorithm source
        if not self.algorithm_file_path and not self.source_code:
            errors.append("Either algorithm_file_path or source_code must be provided")
        
        # Date validation
        if self.start_date and self.end_date:
            if self.start_date >= self.end_date:
                errors.append("Start date must be before end date")
        
        # Capital validation
        if self.starting_capital <= 0:
            errors.append("Starting capital must be positive")
        
        # Resource limits
        if self.max_memory_mb <= 0:
            errors.append("Max memory must be positive")
        
        if self.max_cpu_percent <= 0 or self.max_cpu_percent > 100:
            errors.append("Max CPU percent must be between 0 and 100")
        
        if self.timeout_minutes < 0:
            errors.append("Timeout minutes cannot be negative")
        
        # Risk management
        if self.max_drawdown_percent <= 0 or self.max_drawdown_percent > 100:
            errors.append("Max drawdown percent must be between 0 and 100")
        
        if self.daily_loss_limit is not None and self.daily_loss_limit <= 0:
            errors.append("Daily loss limit must be positive")
        
        return errors
    
    def is_valid(self) -> bool:
        """Check if the packet is valid."""
        return len(self.validate()) == 0
    
    def set_parameter(self, key: str, value: Any):
        """Set an algorithm parameter."""
        self.parameters[key] = value
    
    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Get an algorithm parameter."""
        return self.parameters.get(key, default)
    
    def remove_parameter(self, key: str) -> bool:
        """Remove an algorithm parameter."""
        if key in self.parameters:
            del self.parameters[key]
            return True
        return False
    
    def add_required_package(self, package: str):
        """Add a required package."""
        if package not in self.required_packages:
            self.required_packages.append(package)
    
    def add_custom_library(self, library_path: str):
        """Add a custom library path."""
        if library_path not in self.custom_libraries:
            self.custom_libraries.append(library_path)
    
    def get_runtime_duration(self) -> Optional[float]:
        """Get runtime duration in seconds."""
        if self.deployed_time and self.completed_time:
            return (self.completed_time - self.deployed_time).total_seconds()
        elif self.deployed_time:
            return (datetime.utcnow() - self.deployed_time).total_seconds()
        return None
    
    def get_backtest_duration(self) -> Optional[float]:
        """Get backtest period duration in days."""
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert packet to dictionary."""
        return {
            'algorithm_id': self.algorithm_id,
            'algorithm_name': self.algorithm_name,
            'user_id': self.user_id,
            'project_id': self.project_id,
            'algorithm_file_path': self.algorithm_file_path,
            'source_code': self.source_code,
            'language': self.language.value,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'starting_capital': str(self.starting_capital),
            'environment': self.environment.value,
            'brokerage': self.brokerage,
            'data_provider': self.data_provider,
            'parameters': self.parameters,
            'live_mode': self.live_mode,
            'paper_trading': self.paper_trading,
            'automatic_restart': self.automatic_restart,
            'max_memory_mb': self.max_memory_mb,
            'max_cpu_percent': self.max_cpu_percent,
            'timeout_minutes': self.timeout_minutes,
            'data_folder': self.data_folder,
            'universe_selection': self.universe_selection,
            'benchmark': self.benchmark,
            'max_drawdown_percent': self.max_drawdown_percent,
            'daily_loss_limit': str(self.daily_loss_limit) if self.daily_loss_limit else None,
            'status': self.status.value,
            'created_time': self.created_time.isoformat(),
            'deployed_time': self.deployed_time.isoformat() if self.deployed_time else None,
            'completed_time': self.completed_time.isoformat() if self.completed_time else None,
            'output_folder': self.output_folder,
            'generate_charts': self.generate_charts,
            'generate_statistics': self.generate_statistics,
            'required_packages': self.required_packages,
            'custom_libraries': self.custom_libraries,
            'debug_mode': self.debug_mode,
            'log_level': self.log_level
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlgorithmNodePacket':
        """Create packet from dictionary."""
        # Parse dates
        start_date = None
        if data.get('start_date'):
            start_date = datetime.fromisoformat(data['start_date'])
        
        end_date = None
        if data.get('end_date'):
            end_date = datetime.fromisoformat(data['end_date'])
        
        created_time = datetime.utcnow()
        if data.get('created_time'):
            created_time = datetime.fromisoformat(data['created_time'])
        
        deployed_time = None
        if data.get('deployed_time'):
            deployed_time = datetime.fromisoformat(data['deployed_time'])
        
        completed_time = None
        if data.get('completed_time'):
            completed_time = datetime.fromisoformat(data['completed_time'])
        
        # Parse enums
        language = Language.PYTHON
        if data.get('language'):
            language = Language(data['language'])
        
        environment = BrokerageEnvironment.PAPER
        if data.get('environment'):
            environment = BrokerageEnvironment(data['environment'])
        
        status = AlgorithmStatus.INITIALIZING
        if data.get('status'):
            status = AlgorithmStatus(data['status'])
        
        # Parse decimals
        starting_capital = Decimal(str(data.get('starting_capital', '100000')))
        
        daily_loss_limit = None
        if data.get('daily_loss_limit'):
            daily_loss_limit = Decimal(str(data['daily_loss_limit']))
        
        return cls(
            algorithm_id=data['algorithm_id'],
            algorithm_name=data['algorithm_name'],
            user_id=data.get('user_id', ''),
            project_id=data.get('project_id', ''),
            algorithm_file_path=data.get('algorithm_file_path'),
            source_code=data.get('source_code'),
            language=language,
            start_date=start_date,
            end_date=end_date,
            starting_capital=starting_capital,
            environment=environment,
            brokerage=data.get('brokerage', 'Simulation'),
            data_provider=data.get('data_provider', 'FileSystem'),
            parameters=data.get('parameters', {}),
            live_mode=data.get('live_mode', False),
            paper_trading=data.get('paper_trading', True),
            automatic_restart=data.get('automatic_restart', False),
            max_memory_mb=data.get('max_memory_mb', 1024),
            max_cpu_percent=data.get('max_cpu_percent', 50.0),
            timeout_minutes=data.get('timeout_minutes', 0),
            data_folder=data.get('data_folder', 'data'),
            universe_selection=data.get('universe_selection'),
            benchmark=data.get('benchmark', 'SPY'),
            max_drawdown_percent=data.get('max_drawdown_percent', 20.0),
            daily_loss_limit=daily_loss_limit,
            status=status,
            created_time=created_time,
            deployed_time=deployed_time,
            completed_time=completed_time,
            output_folder=data.get('output_folder', 'output'),
            generate_charts=data.get('generate_charts', True),
            generate_statistics=data.get('generate_statistics', True),
            required_packages=data.get('required_packages', []),
            custom_libraries=data.get('custom_libraries', []),
            debug_mode=data.get('debug_mode', False),
            log_level=data.get('log_level', 'INFO')
        )
    
    def clone(self) -> 'AlgorithmNodePacket':
        """Create a copy of this packet."""
        return AlgorithmNodePacket.from_dict(self.to_dict())
    
    def __str__(self) -> str:
        """String representation of the packet."""
        return (f"AlgorithmNodePacket(id={self.algorithm_id}, "
                f"name={self.algorithm_name}, status={self.status.value})")


class AlgorithmPacketBuilder:
    """
    Builder for creating algorithm node packets.
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset the builder."""
        self._algorithm_id = ""
        self._algorithm_name = ""
        self._user_id = ""
        self._project_id = ""
        self._algorithm_file_path = None
        self._source_code = None
        self._language = Language.PYTHON
        self._start_date = None
        self._end_date = None
        self._starting_capital = Decimal('100000')
        self._parameters = {}
        self._live_mode = False
        self._debug_mode = False
        return self
    
    def algorithm_id(self, algorithm_id: str):
        """Set algorithm ID."""
        self._algorithm_id = algorithm_id
        return self
    
    def algorithm_name(self, name: str):
        """Set algorithm name."""
        self._algorithm_name = name
        return self
    
    def user_id(self, user_id: str):
        """Set user ID."""
        self._user_id = user_id
        return self
    
    def project_id(self, project_id: str):
        """Set project ID."""
        self._project_id = project_id
        return self
    
    def source_file(self, file_path: str):
        """Set source file path."""
        self._algorithm_file_path = file_path
        return self
    
    def source_code(self, code: str):
        """Set source code."""
        self._source_code = code
        return self
    
    def language(self, language: Language):
        """Set programming language."""
        self._language = language
        return self
    
    def date_range(self, start_date: datetime, end_date: datetime):
        """Set date range."""
        self._start_date = start_date
        self._end_date = end_date
        return self
    
    def starting_capital(self, capital: float):
        """Set starting capital."""
        self._starting_capital = Decimal(str(capital))
        return self
    
    def parameter(self, key: str, value: Any):
        """Add algorithm parameter."""
        self._parameters[key] = value
        return self
    
    def live_mode(self, live: bool = True):
        """Set live mode."""
        self._live_mode = live
        return self
    
    def debug_mode(self, debug: bool = True):
        """Set debug mode."""
        self._debug_mode = debug
        return self
    
    def build(self) -> AlgorithmNodePacket:
        """Build the algorithm node packet."""
        if not self._algorithm_id:
            raise ValueError("Algorithm ID is required")
        
        if not self._algorithm_name:
            raise ValueError("Algorithm name is required")
        
        packet = AlgorithmNodePacket(
            algorithm_id=self._algorithm_id,
            algorithm_name=self._algorithm_name,
            user_id=self._user_id,
            project_id=self._project_id,
            algorithm_file_path=self._algorithm_file_path,
            source_code=self._source_code,
            language=self._language,
            start_date=self._start_date,
            end_date=self._end_date,
            starting_capital=self._starting_capital,
            parameters=self._parameters.copy(),
            live_mode=self._live_mode,
            debug_mode=self._debug_mode
        )
        
        return packet