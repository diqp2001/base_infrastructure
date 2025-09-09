"""
Enums for the QuantConnect Lean Engine Python implementation.
Defines various enumeration types used throughout the engine.
"""

from enum import Enum, IntEnum, auto


class EngineType(Enum):
    """Types of trading engines available."""
    BACKTESTING = "Backtesting"
    LIVE_TRADING = "LiveTrading" 
    OPTIMIZATION = "Optimization"
    RESEARCH = "Research"


class HandlerType(Enum):
    """Types of handlers in the engine architecture."""
    DATA_FEED = "DataFeed"
    TRANSACTION = "Transaction"
    RESULT = "Result"
    SETUP = "Setup"
    REALTIME = "RealTime"
    ALGORITHM = "Algorithm"


class AlgorithmStatus(IntEnum):
    """Status of algorithm execution."""
    RUNNING = 0
    STOPPED = 1
    CANCELLED = 2
    DELETED = 3
    COMPLETED = 4
    ERROR = 5
    HISTORY_ONLY = 6
    LIQUIDATED = 7
    DEPLOYED = 8
    IN_QUEUE = 9


class EngineStatus(IntEnum):
    """Status of engine execution."""
    INITIALIZING = 0
    RUNNING = 1
    STOPPING = 2
    STOPPED = 3
    ERROR = 4
    DISPOSED = 5


class DataFeedMode(Enum):
    """Data feed operating modes."""
    FILE_SYSTEM = "FileSystem"
    LIVE = "Live"
    CUSTOM = "Custom"
    PAPER_TRADING = "PaperTrading"


class TransactionMode(Enum):
    """Transaction handler operating modes."""
    BACKTESTING = "Backtesting"
    LIVE = "Live"
    PAPER_TRADING = "PaperTrading"


class ResultMode(Enum):
    """Result handler operating modes."""
    BACKTESTING = "Backtesting"
    LIVE = "Live"
    OPTIMIZATION = "Optimization"
    RESEARCH = "Research"


class SetupMode(Enum):
    """Setup handler operating modes."""
    CONSOLE = "Console"
    CLOUD = "Cloud"
    LOCAL = "Local"
    CUSTOM = "Custom"


class RealTimeMode(Enum):
    """Real-time handler operating modes."""
    BACKTESTING = "Backtesting"
    LIVE = "Live"
    SIMULATION = "Simulation"


class ScheduleEventType(Enum):
    """Types of scheduled events."""
    MARKET_OPEN = "MarketOpen"
    MARKET_CLOSE = "MarketClose"
    CUSTOM = "Custom"
    DATE_RULE = "DateRule"
    TIME_RULE = "TimeRule"


class LogLevel(IntEnum):
    """Logging levels for engine components."""
    TRACE = 0
    DEBUG = 1
    INFO = 2
    WARN = 3
    ERROR = 4
    FATAL = 5


class ComponentState(Enum):
    """State of engine components."""
    CREATED = "Created"
    INITIALIZING = "Initializing"
    INITIALIZED = "Initialized"
    STARTING = "Starting"
    RUNNING = "Running"
    STOPPING = "Stopping"
    STOPPED = "Stopped"
    ERROR = "Error"
    DISPOSED = "Disposed"


class JobType(Enum):
    """Types of jobs that can be executed."""
    BACKTEST = "Backtest"
    LIVE = "Live"
    OPTIMIZATION = "Optimization"
    RESEARCH = "Research"


class PacketType(Enum):
    """Types of communication packets."""
    ALGORITHM_NODE_PACKET = "AlgorithmNodePacket"
    BACKTEST_NODE_PACKET = "BacktestNodePacket"
    LIVE_NODE_PACKET = "LiveNodePacket"
    OPTIMIZATION_NODE_PACKET = "OptimizationNodePacket"


class EngineMode(Enum):
    """Engine operating modes."""
    BACKTESTING = "Backtesting"
    LIVE_TRADING = "LiveTrading"
    PAPER_TRADING = "PaperTrading"
    OPTIMIZATION = "Optimization"
    RESEARCH = "Research"


class ProcessorArchitecture(Enum):
    """Processor architectures."""
    X86 = "x86"
    X64 = "x64"
    ARM = "ARM"
    ARM64 = "ARM64"


class Language(Enum):
    """Supported programming languages."""
    CSHARP = "C#"
    PYTHON = "Python"
    FSHARP = "F#"
    VB = "VisualBasic"
    JAVA = "Java"


class Environment(Enum):
    """Runtime environments."""
    BACKTESTING = "Backtesting"
    LIVE_TRADING = "LiveTrading"
    OPTIMIZATION = "Optimization"
    RESEARCH = "Research"
    LOCAL = "Local"
    CLOUD = "Cloud"


class ConnectionStatus(Enum):
    """Connection status for external services."""
    DISCONNECTED = "Disconnected"
    CONNECTING = "Connecting"
    CONNECTED = "Connected"
    DISCONNECTING = "Disconnecting"
    AUTHENTICATION_FAILED = "AuthenticationFailed"
    CONNECTION_LOST = "ConnectionLost"


class OrderDirection(IntEnum):
    """Direction of orders."""
    BUY = 0
    SELL = 1
    HOLD = 2


class FillGroupingMethod(Enum):
    """Methods for grouping order fills."""
    FILL_TO_FILL = "FillToFill"
    FLAT_TO_FLAT = "FlatToFlat"
    FLAT_TO_REDUCED = "FlatToReduced"


class InsightDirection(IntEnum):
    """Direction of algorithmic insights."""
    UP = 1
    FLAT = 0
    DOWN = -1


class InsightType(Enum):
    """Types of algorithmic insights."""
    PRICE = "Price"
    VOLATILITY = "Volatility"


class InsightScoreType(Enum):
    """Types of insight scoring."""
    DIRECTION = "Direction"
    MAGNITUDE = "Magnitude"


class BenchmarkType(Enum):
    """Types of performance benchmarks."""
    SECURITY = "Security"
    CUSTOM = "Custom"


class RiskMeasure(Enum):
    """Risk measurement types."""
    ALPHA = "Alpha"
    BETA = "Beta"
    ANNUAL_STANDARD_DEVIATION = "AnnualStandardDeviation"
    ANNUAL_VARIANCE = "AnnualVariance"
    INFORMATION_RATIO = "InformationRatio"
    TRACKING_ERROR = "TrackingError"
    TREYNOR_RATIO = "TreynorRatio"
    SHARPE_RATIO = "SharpeRatio"
    SORTINO_RATIO = "SortinoRatio"