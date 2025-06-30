"""
QuantConnect Lean API Module for Python

This module provides a comprehensive Python implementation of the QuantConnect Lean API,
enabling communication with QuantConnect cloud services for project management,
algorithm deployment, backtesting, live trading, and data access.

Key Components:
    - Client Classes: Main API clients for different functionality areas
    - Authentication: API key and OAuth2 authentication providers
    - Models: Data transfer objects for API requests and responses
    - Serialization: JSON serialization/deserialization utilities
    - Error Handling: Comprehensive exception hierarchy
    - Interfaces: Abstract base classes defining contracts

Example Usage:
    ```python
    from .api import QuantConnectApiClient, ApiConfiguration
    
    # Create API client
    config = ApiConfiguration(
        base_url="https://www.quantconnect.com/api/v2",
        timeout=30
    )
    client = QuantConnectApiClient(config)
    
    # Authenticate
    await client.authenticate("api_key:api_secret")
    
    # Create a project
    project = await client.create_project("My Strategy", "Python")
    
    # Create a backtest
    backtest = await client.backtests.create_backtest(
        project['project_id'], "compile_id", "Test Backtest"
    )
    ```
"""

# Core client classes
from .clients import (
    QuantConnectApiClient,
    ApiConnection,
    ProjectManager,
    BacktestManager,
    LiveAlgorithmManager,
    DataManager,
    NodeManager
)

# Authentication
from .authentication import (
    AuthenticationManager,
    ApiKeyAuthenticationProvider,
    OAuth2AuthenticationProvider
)

# Configuration and models
from .models import (
    ApiConfiguration,
    ApiResponse,
    AuthenticationResponse,
    Project,
    ProjectFile,
    CreateProjectRequest,
    Backtest,
    BacktestResult,
    CreateBacktestRequest,
    LiveAlgorithm,
    CreateLiveAlgorithmRequest,
    Node,
    DataLink,
    DataOrder,
    LogEntry,
    Organization,
    OptimizationRequest,
    OptimizationResult,
    ApiError,
    PaginatedResponse
)

# Enumerations
from .enums import (
    ApiResponseStatus,
    ProjectLanguage,
    ProjectState,
    BacktestStatus,
    LiveAlgorithmStatus,
    CompileState,
    NodeType,
    NodeStatus,
    AuthenticationType,
    HttpMethod,
    ApiEndpoint,
    DataFormat,
    LogLevel,
    OptimizationStrategy
)

# Exceptions
from .exceptions import (
    ApiException,
    AuthenticationException,
    AuthorizationException,
    RateLimitException,
    QuotaExceededException,
    ValidationException,
    ResourceNotFoundException,
    ProjectNotFoundException,
    BacktestNotFoundException,
    LiveAlgorithmNotFoundException,
    CompilationException,
    BacktestException,
    LiveTradingException,
    NetworkException,
    TimeoutException,
    ConnectionException,
    SerializationException,
    ConfigurationException,
    CacheException,
    WebSocketException,
    OptimizationException
)

# Serialization utilities
from .serialization import (
    ApiSerializer,
    ApiResponseDeserializer,
    serialize_request_data,
    deserialize_response_data,
    serialize_for_cache,
    deserialize_from_cache,
    convert_dataclass_to_dict,
    safe_deserialize
)

# Interfaces (for extension and testing)
from .interfaces import (
    IApiConnection,
    IApiSerializer,
    IAuthenticationProvider,
    IProjectManager,
    IBacktestManager,
    ILiveAlgorithmManager,
    IDataManager,
    INodeManager,
    IApiWebSocketClient,
    IApiRateLimiter,
    IApiCache
)

# Version information
__version__ = "1.0.0"
__author__ = "QuantConnect Lean Python Team"
__description__ = "Python API client for QuantConnect Lean"

# Public API - explicitly define what gets imported with "from api import *"
__all__ = [
    # Core client classes
    "QuantConnectApiClient",
    "ApiConnection",
    "ProjectManager",
    "BacktestManager", 
    "LiveAlgorithmManager",
    "DataManager",
    "NodeManager",
    
    # Authentication
    "AuthenticationManager",
    "ApiKeyAuthenticationProvider",
    "OAuth2AuthenticationProvider",
    
    # Configuration and models
    "ApiConfiguration",
    "ApiResponse",
    "AuthenticationResponse",
    "Project",
    "ProjectFile",
    "CreateProjectRequest",
    "Backtest",
    "BacktestResult",
    "CreateBacktestRequest",
    "LiveAlgorithm",
    "CreateLiveAlgorithmRequest",
    "Node",
    "DataLink",
    "DataOrder",
    "LogEntry",
    "Organization",
    "OptimizationRequest",
    "OptimizationResult",
    "ApiError",
    "PaginatedResponse",
    
    # Enumerations
    "ApiResponseStatus",
    "ProjectLanguage",
    "ProjectState",
    "BacktestStatus",
    "LiveAlgorithmStatus",
    "CompileState",
    "NodeType",
    "NodeStatus",
    "AuthenticationType",
    "HttpMethod",
    "ApiEndpoint",
    "DataFormat",
    "LogLevel",
    "OptimizationStrategy",
    
    # Exceptions
    "ApiException",
    "AuthenticationException",
    "AuthorizationException",
    "RateLimitException",
    "QuotaExceededException",
    "ValidationException",
    "ResourceNotFoundException",
    "ProjectNotFoundException",
    "BacktestNotFoundException",
    "LiveAlgorithmNotFoundException",
    "CompilationException",
    "BacktestException",
    "LiveTradingException",
    "NetworkException",
    "TimeoutException",
    "ConnectionException",
    "SerializationException",
    "ConfigurationException",
    "CacheException",
    "WebSocketException",
    "OptimizationException",
    
    # Serialization utilities
    "ApiSerializer",
    "ApiResponseDeserializer",
    "serialize_request_data",
    "deserialize_response_data",
    "serialize_for_cache",
    "deserialize_from_cache",
    "convert_dataclass_to_dict",
    "safe_deserialize",
    
    # Interfaces
    "IApiConnection",
    "IApiSerializer",
    "IAuthenticationProvider",
    "IProjectManager",
    "IBacktestManager",
    "ILiveAlgorithmManager",
    "IDataManager",
    "INodeManager",
    "IApiWebSocketClient",
    "IApiRateLimiter",
    "IApiCache",
]

# Module metadata
__package_info__ = {
    "name": "quantconnect-lean-api",
    "version": __version__,
    "description": __description__,
    "author": __author__,
    "dependencies": [
        "aiohttp>=3.8.0",
        "python-dateutil>=2.8.0"
    ],
    "python_requires": ">=3.8",
    "keywords": ["quantconnect", "trading", "api", "backtesting", "finance"],
    "url": "https://github.com/QuantConnect/Lean",
    "documentation": "https://www.quantconnect.com/docs/v2/our-platform/api",
}

# Convenience functions for quick setup
def create_api_client(api_key: str = None, api_secret: str = None, 
                     base_url: str = None, **config_kwargs) -> QuantConnectApiClient:
    """
    Create a pre-configured QuantConnect API client.
    
    Args:
        api_key: API key for authentication
        api_secret: API secret for authentication
        base_url: Base URL for the API (defaults to production)
        **config_kwargs: Additional configuration parameters
    
    Returns:
        Configured QuantConnectApiClient instance
        
    Example:
        ```python
        client = create_api_client("your_key", "your_secret")
        await client.authenticate()
        ```
    """
    # Create configuration
    config_params = {
        "base_url": base_url or "https://www.quantconnect.com/api/v2",
        **config_kwargs
    }
    config = ApiConfiguration(**config_params)
    
    # Create client
    client = QuantConnectApiClient(config)
    
    # Set up authentication if credentials provided
    if api_key and api_secret:
        client.auth_manager.set_api_key_provider(api_key, api_secret)
    
    return client


def create_test_client(**config_kwargs) -> QuantConnectApiClient:
    """
    Create a test API client with mock configuration.
    
    Args:
        **config_kwargs: Configuration parameters for testing
        
    Returns:
        QuantConnectApiClient configured for testing
    """
    test_config = {
        "base_url": "https://test.api.quantconnect.com",
        "timeout": 10,
        "max_retries": 1,
        "verify_ssl": False,
        **config_kwargs
    }
    
    config = ApiConfiguration(**test_config)
    return QuantConnectApiClient(config)


# Logging configuration
import logging

def configure_api_logging(level: int = logging.INFO, 
                         format_string: str = None) -> None:
    """
    Configure logging for the API module.
    
    Args:
        level: Logging level (e.g., logging.INFO, logging.DEBUG)
        format_string: Custom log format string
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(level)
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        
        if format_string is None:
            format_string = (
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        formatter = logging.Formatter(format_string)
        handler.setFormatter(formatter)
        logger.addHandler(handler)


# Module initialization message
def _module_info():
    """Display module information."""
    return f"""
QuantConnect Lean API Python Module v{__version__}

A comprehensive Python client for QuantConnect API operations including:
• Project Management (create, read, update, delete projects)
• Algorithm Backtesting (run backtests, retrieve results)
• Live Trading (deploy algorithms, monitor performance)
• Data Management (access market data, manage subscriptions)
• Authentication (API key and OAuth2 support)
• Error Handling (comprehensive exception hierarchy)

For documentation and examples, visit:
https://www.quantconnect.com/docs/v2/our-platform/api

Quick Start:
    from api import create_api_client
    client = create_api_client("your_key", "your_secret")
    await client.authenticate()
"""

# Print info when module is imported in interactive mode
import sys
if hasattr(sys, 'ps1'):  # Interactive mode
    print(_module_info())