"""
Data models for API requests and responses.
These models represent the data structures used for communication with QuantConnect API.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal

from .enums import (
    ProjectLanguage, ProjectState, BacktestStatus, LiveAlgorithmStatus,
    CompileState, NodeType, NodeStatus, DataFormat, ApiResponseStatus,
    LogLevel, OptimizationStrategy
)


@dataclass
class ApiResponse:
    """Base API response model."""
    success: bool
    errors: List[str] = field(default_factory=list)
    status: ApiResponseStatus = ApiResponseStatus.SUCCESS
    
    def __post_init__(self):
        """Post-initialization validation."""
        if not self.success and not self.errors:
            self.errors = ["Unknown error occurred"]


@dataclass
class AuthenticationResponse(ApiResponse):
    """Authentication response model."""
    user_id: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    expires_in: Optional[int] = None
    token_type: Optional[str] = "Bearer"
    
    def is_authenticated(self) -> bool:
        """Check if authentication was successful."""
        return self.success and self.access_token is not None


@dataclass
class Project:
    """Project model."""
    project_id: int
    name: str
    created: datetime
    modified: datetime
    language: ProjectLanguage
    state: ProjectState = ProjectState.ACTIVE
    description: str = ""
    libraries: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure proper types."""
        if isinstance(self.language, str):
            self.language = ProjectLanguage(self.language)
        if isinstance(self.state, str):
            self.state = ProjectState(self.state)


@dataclass
class ProjectFile:
    """Project file model."""
    name: str
    content: str
    modified: datetime
    is_library: bool = False
    
    @property
    def extension(self) -> str:
        """Get file extension."""
        return self.name.split('.')[-1] if '.' in self.name else ""
    
    @property
    def is_main_file(self) -> bool:
        """Check if this is the main algorithm file."""
        return self.name.lower() in ['main.py', 'algorithm.py', 'main.cs']


@dataclass
class CreateProjectRequest:
    """Request model for creating a project."""
    name: str
    language: ProjectLanguage
    description: str = ""
    
    def __post_init__(self):
        """Ensure proper types."""
        if isinstance(self.language, str):
            self.language = ProjectLanguage(self.language)


@dataclass
class CompileResult:
    """Compilation result model."""
    compile_id: str
    state: CompileState
    logs: List[str] = field(default_factory=list)
    binary: Optional[str] = None
    started: Optional[datetime] = None
    completed: Optional[datetime] = None
    
    def __post_init__(self):
        """Ensure proper types."""
        if isinstance(self.state, str):
            self.state = CompileState(self.state)
    
    @property
    def is_successful(self) -> bool:
        """Check if compilation was successful."""
        return self.state == CompileState.BUILD_SUCCESS
    
    @property
    def duration(self) -> Optional[float]:
        """Get compilation duration in seconds."""
        if self.started and self.completed:
            return (self.completed - self.started).total_seconds()
        return None


@dataclass
class Backtest:
    """Backtest model."""
    project_id: int
    backtest_id: str
    name: str
    status: BacktestStatus
    created: datetime
    completed: Optional[datetime] = None
    progress: float = 0.0
    result: Optional['BacktestResult'] = None
    statistics: Dict[str, Any] = field(default_factory=dict)
    runtime_statistics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    
    def __post_init__(self):
        """Ensure proper types."""
        if isinstance(self.status, str):
            self.status = BacktestStatus(self.status)
    
    @property
    def is_completed(self) -> bool:
        """Check if backtest is completed."""
        return self.status in [BacktestStatus.COMPLETED, BacktestStatus.ERROR, 
                              BacktestStatus.CANCELLED, BacktestStatus.RUNTIME_ERROR]
    
    @property
    def duration(self) -> Optional[float]:
        """Get backtest duration in seconds."""
        if self.completed:
            return (self.completed - self.created).total_seconds()
        return None


@dataclass
class BacktestResult:
    """Backtest result model with performance metrics."""
    total_return: Decimal = Decimal('0')
    sharpe_ratio: Decimal = Decimal('0')
    sortino_ratio: Decimal = Decimal('0')
    alpha: Decimal = Decimal('0')
    beta: Decimal = Decimal('0')
    annual_variance: Decimal = Decimal('0')
    annual_standard_deviation: Decimal = Decimal('0')
    information_ratio: Decimal = Decimal('0')
    tracking_error: Decimal = Decimal('0')
    treynor_ratio: Decimal = Decimal('0')
    total_fees: Decimal = Decimal('0')
    estimated_strategy_capacity: Decimal = Decimal('0')
    lowest_capacity_asset: Optional[str] = None
    portfolio_turnover: Decimal = Decimal('0')
    
    # Drawdown metrics
    max_drawdown: Decimal = Decimal('0')
    drawdown_duration: int = 0
    
    # Trading metrics
    total_trades: int = 0
    average_win: Decimal = Decimal('0')
    average_loss: Decimal = Decimal('0')
    compounding_annual_return: Decimal = Decimal('0')
    win_rate: Decimal = Decimal('0')
    loss_rate: Decimal = Decimal('0')
    expectancy: Decimal = Decimal('0')
    
    # Additional statistics
    start_equity: Decimal = Decimal('100000')
    end_equity: Decimal = Decimal('100000')
    peak_equity: Decimal = Decimal('100000')
    
    # Chart data
    equity_curve: List[Dict[str, Any]] = field(default_factory=list)
    daily_returns: List[Dict[str, Any]] = field(default_factory=list)
    benchmark_curve: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Ensure all values are Decimal objects."""
        for field_name, field_value in self.__dict__.items():
            if isinstance(field_value, (int, float, str)) and 'Decimal' in str(type(self.__dataclass_fields__[field_name].type)):
                setattr(self, field_name, Decimal(str(field_value)))


@dataclass
class CreateBacktestRequest:
    """Request model for creating a backtest."""
    project_id: int
    compile_id: str
    name: str
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    initial_cash: Decimal = Decimal('100000')
    
    def __post_init__(self):
        """Ensure proper types."""
        if not isinstance(self.initial_cash, Decimal):
            self.initial_cash = Decimal(str(self.initial_cash))


@dataclass
class LiveAlgorithm:
    """Live algorithm model."""
    project_id: int
    deploy_id: str
    status: LiveAlgorithmStatus
    launched: datetime
    stopped: Optional[datetime] = None
    brokerage: str = ""
    subscription: str = ""
    server_type: str = ""
    server_id: str = ""
    base_live_algorithm_settings: Dict[str, Any] = field(default_factory=dict)
    live_holdings: List[Dict[str, Any]] = field(default_factory=list)
    cash: Decimal = Decimal('0')
    
    def __post_init__(self):
        """Ensure proper types."""
        if isinstance(self.status, str):
            self.status = LiveAlgorithmStatus(self.status)
        if not isinstance(self.cash, Decimal):
            self.cash = Decimal(str(self.cash))
    
    @property
    def is_running(self) -> bool:
        """Check if live algorithm is running."""
        return self.status == LiveAlgorithmStatus.RUNNING
    
    @property
    def duration(self) -> Optional[float]:
        """Get runtime duration in seconds."""
        end_time = self.stopped or datetime.utcnow()
        return (end_time - self.launched).total_seconds()


@dataclass
class CreateLiveAlgorithmRequest:
    """Request model for creating a live algorithm."""
    project_id: int
    compile_id: str
    server_type: str
    base_live_algorithm_settings: Dict[str, Any]
    version_id: int = -1
    
    def validate(self) -> List[str]:
        """Validate the request."""
        errors = []
        if not self.server_type:
            errors.append("Server type is required")
        if not self.base_live_algorithm_settings:
            errors.append("Live algorithm settings are required")
        return errors


@dataclass
class Node:
    """Compute node model."""
    id: str
    name: str
    type: NodeType
    status: NodeStatus
    cpu_count: int
    ram_gb: int
    assets: List[str] = field(default_factory=list)
    price: Decimal = Decimal('0')
    busy: bool = False
    
    def __post_init__(self):
        """Ensure proper types."""
        if isinstance(self.type, str):
            self.type = NodeType(self.type)
        if isinstance(self.status, str):
            self.status = NodeStatus(self.status)
        if not isinstance(self.price, Decimal):
            self.price = Decimal(str(self.price))


@dataclass
class DataLink:
    """Data link model."""
    id: int
    source: str
    name: str
    format: DataFormat
    price: Decimal
    description: str = ""
    url: str = ""
    
    def __post_init__(self):
        """Ensure proper types."""
        if isinstance(self.format, str):
            self.format = DataFormat(self.format)
        if not isinstance(self.price, Decimal):
            self.price = Decimal(str(self.price))


@dataclass
class DataOrder:
    """Data order model."""
    id: int
    data_link_id: int
    organization_id: str
    created: datetime
    price: Decimal
    status: str = "Pending"
    
    def __post_init__(self):
        """Ensure proper types."""
        if not isinstance(self.price, Decimal):
            self.price = Decimal(str(self.price))


@dataclass
class LogEntry:
    """Log entry model."""
    time: datetime
    level: LogLevel
    message: str
    algorithm_id: Optional[str] = None
    
    def __post_init__(self):
        """Ensure proper types."""
        if isinstance(self.level, str):
            self.level = LogLevel(self.level)


@dataclass
class Organization:
    """Organization model."""
    id: str
    name: str
    type: str
    owner_name: str
    owner_email: str
    data_agreement: bool = False
    disk_quota: int = 0
    node_quota: int = 0
    credit_balance: Decimal = Decimal('0')
    
    def __post_init__(self):
        """Ensure proper types."""
        if not isinstance(self.credit_balance, Decimal):
            self.credit_balance = Decimal(str(self.credit_balance))


@dataclass
class OptimizationRequest:
    """Optimization request model."""
    project_id: int
    compile_id: str
    name: str
    target: str
    target_direction: str  # "min" or "max"
    parameters: List[Dict[str, Any]]
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    strategy: OptimizationStrategy = OptimizationStrategy.GENETIC
    node_type: NodeType = NodeType.OPTIMIZATION
    criterion: Optional[str] = None
    
    def __post_init__(self):
        """Ensure proper types."""
        if isinstance(self.strategy, str):
            self.strategy = OptimizationStrategy(self.strategy)
        if isinstance(self.node_type, str):
            self.node_type = NodeType(self.node_type)


@dataclass
class OptimizationResult:
    """Optimization result model."""
    optimization_id: str
    project_id: int
    status: str
    parameters: List[Dict[str, Any]]
    statistics: Dict[str, Any] = field(default_factory=dict)
    backtests: List[Dict[str, Any]] = field(default_factory=list)
    created: Optional[datetime] = None
    completed: Optional[datetime] = None
    
    @property
    def is_completed(self) -> bool:
        """Check if optimization is completed."""
        return self.status.lower() in ['completed', 'cancelled', 'error']


@dataclass
class ApiError:
    """API error model."""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    
    def __str__(self) -> str:
        """String representation of the error."""
        if self.details:
            return f"{self.code}: {self.message} - {self.details}"
        return f"{self.code}: {self.message}"


@dataclass
class PaginatedResponse:
    """Paginated response model."""
    data: List[Any]
    total_count: int
    page: int = 1
    page_size: int = 50
    has_next: bool = False
    has_prev: bool = False
    
    @property
    def total_pages(self) -> int:
        """Calculate total number of pages."""
        return (self.total_count + self.page_size - 1) // self.page_size


@dataclass
class ApiConfiguration:
    """API configuration model."""
    base_url: str = "https://www.quantconnect.com/api/v2"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    rate_limit_requests: int = 100
    rate_limit_period: int = 60
    cache_enabled: bool = True
    cache_ttl: int = 300
    verify_ssl: bool = True
    
    def __post_init__(self):
        """Validate configuration."""
        if not self.base_url:
            raise ValueError("Base URL is required")
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")
        if self.max_retries < 0:
            raise ValueError("Max retries cannot be negative")