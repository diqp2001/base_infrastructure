"""
Engine node packet for QuantConnect Lean Engine Python implementation.
Configuration and communication packets for engine execution.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from pathlib import Path

from .enums import (
    JobType, PacketType, Language, Environment, EngineMode,
    ProcessorArchitecture, LogLevel
)


@dataclass
class BaseNodePacket:
    """Base class for all node packets."""
    type: PacketType
    user_id: int
    project_id: int
    session_id: str
    user_token: str = ""
    channel: str = ""
    version: str = "1.0.0"
    created: datetime = field(default_factory=datetime.utcnow)
    ram_allocation: int = 1024  # MB
    language: Language = Language.PYTHON
    environment: Environment = Environment.BACKTESTING


@dataclass
class EngineNodePacket(BaseNodePacket):
    """
    Configuration packet for engine execution.
    Contains all parameters needed to run an algorithm.
    """
    
    # Algorithm Configuration
    algorithm_id: str = ""
    algorithm_name: str = ""
    algorithm_location: str = ""
    algorithm_class_name: str = ""
    
    # Time Configuration
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    
    # Capital Configuration
    starting_capital: Decimal = Decimal('100000')
    currency: str = "USD"
    
    # Engine Configuration
    engine_mode: EngineMode = EngineMode.BACKTESTING
    log_level: LogLevel = LogLevel.INFO
    
    # Data Configuration
    data_folder: str = "./data"
    results_folder: str = "./results"
    cache_location: str = "./cache"
    
    # Performance Configuration
    max_runtime_minutes: int = 0  # 0 = unlimited
    timeout_minutes: int = 10
    
    # Handler Configuration
    data_feed_handler: str = "FileSystemDataFeed"
    transaction_handler: str = "BacktestingTransactionHandler"
    result_handler: str = "BacktestingResultHandler"
    setup_handler: str = "ConsoleSetupHandler"
    realtime_handler: str = "BacktestingRealTimeHandler"
    algorithm_handler: str = "AlgorithmHandler"
    
    # Custom Parameters
    parameters: Dict[str, Any] = field(default_factory=dict)
    controls: Dict[str, Any] = field(default_factory=dict)
    
    # Security Master
    security_master: Dict[str, Any] = field(default_factory=dict)
    
    # Debugging
    debugging: bool = False
    debug_port: int = 0
    
    def __post_init__(self):
        """Post-initialization processing."""
        super().__init__()
        
        # Set default dates if not provided
        if self.start_date is None:
            self.start_date = datetime(2020, 1, 1)
        if self.end_date is None:
            self.end_date = datetime.utcnow()
        
        # Ensure data folders exist
        Path(self.data_folder).mkdir(parents=True, exist_ok=True)
        Path(self.results_folder).mkdir(parents=True, exist_ok=True)
        Path(self.cache_location).mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> bool:
        """Validate the packet configuration."""
        errors = []
        
        if not self.algorithm_id:
            errors.append("Algorithm ID is required")
        if not self.algorithm_location:
            errors.append("Algorithm location is required")
        if not self.algorithm_class_name:
            errors.append("Algorithm class name is required")
        if self.start_date >= self.end_date:
            errors.append("Start date must be before end date")
        if self.starting_capital <= 0:
            errors.append("Starting capital must be positive")
        
        if errors:
            raise ValueError(f"Invalid packet configuration: {'; '.join(errors)}")
        
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert packet to dictionary."""
        return {
            'type': self.type.value,
            'userId': self.user_id,
            'projectId': self.project_id,
            'sessionId': self.session_id,
            'userToken': self.user_token,
            'channel': self.channel,
            'version': self.version,
            'created': self.created.isoformat(),
            'ramAllocation': self.ram_allocation,
            'language': self.language.value,
            'environment': self.environment.value,
            'algorithmId': self.algorithm_id,
            'algorithmName': self.algorithm_name,
            'algorithmLocation': self.algorithm_location,
            'algorithmClassName': self.algorithm_class_name,
            'startDate': self.start_date.isoformat() if self.start_date else None,
            'endDate': self.end_date.isoformat() if self.end_date else None,
            'startingCapital': float(self.starting_capital),
            'currency': self.currency,
            'engineMode': self.engine_mode.value,
            'logLevel': self.log_level.value,
            'dataFolder': self.data_folder,
            'resultsFolder': self.results_folder,
            'cacheLocation': self.cache_location,
            'maxRuntimeMinutes': self.max_runtime_minutes,
            'timeoutMinutes': self.timeout_minutes,
            'dataFeedHandler': self.data_feed_handler,
            'transactionHandler': self.transaction_handler,
            'resultHandler': self.result_handler,
            'setupHandler': self.setup_handler,
            'realtimeHandler': self.realtime_handler,
            'algorithmHandler': self.algorithm_handler,
            'parameters': self.parameters,
            'controls': self.controls,
            'securityMaster': self.security_master,
            'debugging': self.debugging,
            'debugPort': self.debug_port,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EngineNodePacket':
        """Create packet from dictionary."""
        packet = cls(
            type=PacketType(data.get('type', PacketType.ALGORITHM_NODE_PACKET.value)),
            user_id=data.get('userId', 0),
            project_id=data.get('projectId', 0),
            session_id=data.get('sessionId', ''),
            user_token=data.get('userToken', ''),
            channel=data.get('channel', ''),
            version=data.get('version', '1.0.0'),
            ram_allocation=data.get('ramAllocation', 1024),
            language=Language(data.get('language', Language.PYTHON.value)),
            environment=Environment(data.get('environment', Environment.BACKTESTING.value)),
            algorithm_id=data.get('algorithmId', ''),
            algorithm_name=data.get('algorithmName', ''),
            algorithm_location=data.get('algorithmLocation', ''),
            algorithm_class_name=data.get('algorithmClassName', ''),
            starting_capital=Decimal(str(data.get('startingCapital', '100000'))),
            currency=data.get('currency', 'USD'),
            engine_mode=EngineMode(data.get('engineMode', EngineMode.BACKTESTING.value)),
            log_level=LogLevel(data.get('logLevel', LogLevel.INFO.value)),
            data_folder=data.get('dataFolder', './data'),
            results_folder=data.get('resultsFolder', './results'),
            cache_location=data.get('cacheLocation', './cache'),
            max_runtime_minutes=data.get('maxRuntimeMinutes', 0),
            timeout_minutes=data.get('timeoutMinutes', 10),
            data_feed_handler=data.get('dataFeedHandler', 'FileSystemDataFeed'),
            transaction_handler=data.get('transactionHandler', 'BacktestingTransactionHandler'),
            result_handler=data.get('resultHandler', 'BacktestingResultHandler'),
            setup_handler=data.get('setupHandler', 'ConsoleSetupHandler'),
            realtime_handler=data.get('realtimeHandler', 'BacktestingRealTimeHandler'),
            algorithm_handler=data.get('algorithmHandler', 'AlgorithmHandler'),
            parameters=data.get('parameters', {}),
            controls=data.get('controls', {}),
            security_master=data.get('securityMaster', {}),
            debugging=data.get('debugging', False),
            debug_port=data.get('debugPort', 0),
        )
        
        # Parse dates
        if data.get('created'):
            packet.created = datetime.fromisoformat(data['created'])
        if data.get('startDate'):
            packet.start_date = datetime.fromisoformat(data['startDate'])
        if data.get('endDate'):
            packet.end_date = datetime.fromisoformat(data['endDate'])
        
        return packet


@dataclass
class BacktestNodePacket(EngineNodePacket):
    """Specialized packet for backtesting jobs."""
    
    # Backtesting-specific configuration
    benchmark_symbol: str = "SPY"
    backtest_name: str = ""
    backtest_note: str = ""
    
    # Data options
    automatic_indicators: bool = True
    fill_forward: bool = True
    
    # Optimization
    optimization_target: str = "SharpeRatio"
    optimization_target_direction: str = "max"
    
    def __post_init__(self):
        super().__post_init__()
        self.type = PacketType.BACKTEST_NODE_PACKET
        self.engine_mode = EngineMode.BACKTESTING


@dataclass 
class LiveNodePacket(EngineNodePacket):
    """Specialized packet for live trading jobs."""
    
    # Live trading configuration
    brokerage: str = "Paper"
    data_queue_handler: str = "Paper"
    
    # Account information
    account_id: str = ""
    account_key: str = ""
    account_secret: str = ""
    
    # Risk management
    daily_max_loss: Optional[Decimal] = None
    position_size_limit: Optional[Decimal] = None
    
    def __post_init__(self):
        super().__post_init__()
        self.type = PacketType.LIVE_NODE_PACKET
        self.engine_mode = EngineMode.LIVE_TRADING


@dataclass
class OptimizationNodePacket(EngineNodePacket):
    """Specialized packet for optimization jobs."""
    
    # Optimization configuration
    optimization_strategy: str = "GridSearch"
    optimization_target: str = "SharpeRatio"
    optimization_target_direction: str = "max"
    
    # Parameter ranges
    parameter_ranges: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Constraints
    max_iterations: int = 100
    parallel_nodes: int = 1
    
    def __post_init__(self):
        super().__post_init__()
        self.type = PacketType.OPTIMIZATION_NODE_PACKET
        self.engine_mode = EngineMode.OPTIMIZATION