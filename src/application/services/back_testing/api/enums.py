"""
API-specific enumerations for the QuantConnect Lean Python implementation.
"""

from enum import Enum, IntEnum


class ApiResponseStatus(Enum):
    """API response status codes."""
    SUCCESS = "Success"
    ERROR = "Error"
    AUTHENTICATION_ERROR = "AuthenticationError"
    RATE_LIMIT_EXCEEDED = "RateLimitExceeded"
    QUOTA_EXCEEDED = "QuotaExceeded"
    INVALID_REQUEST = "InvalidRequest"
    NOT_FOUND = "NotFound"
    INTERNAL_ERROR = "InternalError"


class ProjectLanguage(Enum):
    """Programming languages supported for projects."""
    PYTHON = "Py"
    CSHARP = "C#"
    FSHARP = "F#"
    VISUAL_BASIC = "VB"
    JAVA = "Java"


class ProjectState(Enum):
    """Project states."""
    ACTIVE = "Active"
    ARCHIVED = "Archived"
    DELETED = "Deleted"


class BacktestStatus(Enum):
    """Backtest execution status."""
    CREATED = "Created"
    QUEUED = "Queued"
    RUNNING = "Running"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
    ERROR = "Error"
    RUNTIME_ERROR = "RuntimeError"
    STOPPED = "Stopped"
    DELETED = "Deleted"


class LiveAlgorithmStatus(Enum):
    """Live algorithm deployment status."""
    CREATED = "Created"
    DEPLOYING = "Deploying"
    DEPLOYED = "Deployed"
    RUNNING = "Running"
    STOPPED = "Stopped"
    ERROR = "Error"
    LIQUIDATED = "Liquidated"
    DELETED = "Deleted"


class CompileState(Enum):
    """Algorithm compilation states."""
    IN_QUEUE = "InQueue"
    BUILDING = "Building"
    BUILD_SUCCESS = "BuildSuccess"
    BUILD_ERROR = "BuildError"


class NodeType(Enum):
    """Compute node types."""
    BACKTEST = "B"
    RESEARCH = "R"
    LIVE = "L"
    OPTIMIZATION = "O"


class NodeStatus(Enum):
    """Node status."""
    BUSY = "Busy"
    IDLE = "Idle"
    OFFLINE = "Offline"
    TERMINATED = "Terminated"


class OrganizationProduct(Enum):
    """Organization products."""
    PROFESSIONAL = "Professional"
    TEAM = "Team"
    ENTERPRISE = "Enterprise"


class SecurityMasterType(Enum):
    """Security master types."""
    EQUITY = "Equity"
    FOREX = "Forex"
    CFD = "Cfd"
    FUTURE = "Future"
    OPTION = "Option"
    COMMODITY = "Commodity"
    CRYPTO = "Crypto"


class DataFormat(Enum):
    """Data format types."""
    CSV = "csv"
    JSON = "json"
    LEAN = "lean"
    QUANTCONNECT = "quantconnect"


class SubscriptionType(Enum):
    """Data subscription types."""
    TRADE = "Trade"
    QUOTE = "Quote"
    OPEN_INTEREST = "OpenInterest"
    FUNDAMENTAL = "Fundamental"


class Resolution(Enum):
    """Data resolution types."""
    TICK = "Tick"
    SECOND = "Second"
    MINUTE = "Minute"
    HOUR = "Hour"
    DAILY = "Daily"


class DataLinkStatus(Enum):
    """Data link status."""
    ACTIVE = "Active"
    INACTIVE = "Inactive"
    PENDING = "Pending"
    EXPIRED = "Expired"


class ApiEndpoint(Enum):
    """API endpoint paths."""
    # Authentication
    AUTHENTICATE = "/authenticate"
    
    # Projects
    PROJECTS_LIST = "/projects/read"
    PROJECTS_CREATE = "/projects/create"
    PROJECTS_READ = "/projects/{projectId}/read"
    PROJECTS_UPDATE = "/projects/{projectId}/update"
    PROJECTS_DELETE = "/projects/{projectId}/delete"
    
    # Files
    FILES_CREATE = "/files/{projectId}/create"
    FILES_READ = "/files/{projectId}/read"
    FILES_UPDATE = "/files/{projectId}/update"
    FILES_DELETE = "/files/{projectId}/delete"
    
    # Compile
    COMPILE_CREATE = "/compile/{projectId}/create"
    COMPILE_READ = "/compile/{projectId}/{compileId}/read"
    
    # Backtests
    BACKTESTS_CREATE = "/backtests/{projectId}/create"
    BACKTESTS_READ = "/backtests/{projectId}/{backtestId}/read"
    BACKTESTS_UPDATE = "/backtests/{projectId}/{backtestId}/update"
    BACKTESTS_DELETE = "/backtests/{projectId}/{backtestId}/delete"
    BACKTESTS_LIST = "/backtests/{projectId}/read"
    
    # Live Algorithms
    LIVE_CREATE = "/live/{projectId}/create"
    LIVE_READ = "/live/{projectId}/{deployId}/read"
    LIVE_LIST = "/live/{projectId}/read"
    LIVE_STOP = "/live/{projectId}/{deployId}/stop"
    LIVE_LIQUIDATE = "/live/{projectId}/{deployId}/liquidate"
    
    # Data
    DATA_LINKS = "/data/list"
    DATA_PRICES = "/data/prices/{organizationId}"
    DATA_ORDER_CREATE = "/data/order/create"
    DATA_ORDER_LIST = "/data/order/list"
    
    # Nodes
    NODES_LIST = "/nodes/read"
    NODES_CREATE = "/nodes/create"
    NODES_READ = "/nodes/{nodeId}/read"
    NODES_DELETE = "/nodes/{nodeId}/delete"
    
    # Logs
    LOGS_READ = "/logs/{projectId}/{algorithmId}/read"
    
    # Organizations
    ORGANIZATIONS_READ = "/organizations/read"


class HttpMethod(Enum):
    """HTTP methods."""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class AuthenticationType(Enum):
    """Authentication types."""
    API_KEY = "ApiKey"
    OAUTH2 = "OAuth2"
    BEARER_TOKEN = "BearerToken"


class CacheStrategy(Enum):
    """Cache strategies."""
    NO_CACHE = "NoCache"
    CACHE_FIRST = "CacheFirst"
    NETWORK_FIRST = "NetworkFirst"
    CACHE_ONLY = "CacheOnly"
    NETWORK_ONLY = "NetworkOnly"


class RateLimitScope(Enum):
    """Rate limit scopes."""
    GLOBAL = "Global"
    ENDPOINT = "Endpoint"
    USER = "User"
    ORGANIZATION = "Organization"


class WebSocketMessageType(Enum):
    """WebSocket message types."""
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    DATA = "data"
    STATUS = "status"
    ERROR = "error"
    HEARTBEAT = "heartbeat"


class LogLevel(Enum):
    """Log levels."""
    TRACE = "Trace"
    DEBUG = "Debug"
    INFO = "Info"
    WARN = "Warn"
    ERROR = "Error"
    FATAL = "Fatal"


class OptimizationStrategy(Enum):
    """Optimization strategies."""
    GENETIC = "Genetic"
    GRID_SEARCH = "GridSearch"
    RANDOM_SEARCH = "RandomSearch"
    BAYESIAN = "Bayesian"


class QuantConnectPackage(Enum):
    """QuantConnect package types."""
    LEAN = "Lean"
    RESEARCH = "Research"
    PROFESSIONAL = "Professional"
    INSTITUTIONAL = "Institutional"


class MarketDataType(Enum):
    """Market data types."""
    TRADE_BARS = "TradeBars"
    QUOTE_BARS = "QuoteBars"
    TICKS = "Ticks"
    OPTION_CHAINS = "OptionChains"
    FUTURES_CHAINS = "FuturesChains"
    FUNDAMENTAL = "Fundamental"
    ALTERNATIVE = "Alternative"