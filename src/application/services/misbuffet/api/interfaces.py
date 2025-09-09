"""
Extended API interfaces for QuantConnect Lean Python implementation.
These interfaces define contracts for various API communication components.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, AsyncGenerator, Callable
from decimal import Decimal
import asyncio


class IApiConnection(ABC):
    """
    Interface for API connection management.
    Handles low-level HTTP communication with QuantConnect servers.
    """
    
    @abstractmethod
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GET request to the specified endpoint."""
        pass
    
    @abstractmethod
    async def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a POST request to the specified endpoint."""
        pass
    
    @abstractmethod
    async def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a PUT request to the specified endpoint."""
        pass
    
    @abstractmethod
    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """Execute a DELETE request to the specified endpoint."""
        pass
    
    @abstractmethod
    def set_authentication(self, token: str, user_id: str) -> None:
        """Set authentication credentials for API requests."""
        pass


class IApiSerializer(ABC):
    """
    Interface for API data serialization and deserialization.
    Handles conversion between Python objects and JSON for API communication.
    """
    
    @abstractmethod
    def serialize(self, obj: Any) -> str:
        """Serialize a Python object to JSON string."""
        pass
    
    @abstractmethod
    def deserialize(self, json_str: str, target_type: type) -> Any:
        """Deserialize JSON string to Python object of specified type."""
        pass
    
    @abstractmethod
    def serialize_decimal(self, value: Decimal) -> str:
        """Serialize a Decimal value to string format."""
        pass
    
    @abstractmethod
    def deserialize_decimal(self, value: str) -> Decimal:
        """Deserialize string to Decimal value."""
        pass


class IAuthenticationProvider(ABC):
    """
    Interface for authentication providers.
    Manages different authentication methods (API key, OAuth2, etc.).
    """
    
    @abstractmethod
    async def authenticate(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Authenticate using provided credentials."""
        pass
    
    @abstractmethod
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an expired access token."""
        pass
    
    @abstractmethod
    def is_token_valid(self, token: str) -> bool:
        """Check if the provided token is valid."""
        pass
    
    @abstractmethod
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """Get the expiry time of the provided token."""
        pass


class IProjectManager(ABC):
    """
    Interface for project management operations.
    Handles CRUD operations for QuantConnect projects.
    """
    
    @abstractmethod
    async def create_project(self, name: str, language: str, description: str = "") -> 'Project':
        """Create a new project."""
        pass
    
    @abstractmethod
    async def get_project(self, project_id: int) -> 'Project':
        """Get project details by ID."""
        pass
    
    @abstractmethod
    async def update_project(self, project_id: int, **kwargs) -> 'Project':
        """Update project details."""
        pass
    
    @abstractmethod
    async def delete_project(self, project_id: int) -> bool:
        """Delete a project."""
        pass
    
    @abstractmethod
    async def list_projects(self) -> List['Project']:
        """List all projects for the authenticated user."""
        pass
    
    @abstractmethod
    async def add_file(self, project_id: int, name: str, content: str) -> 'ProjectFile':
        """Add a file to the project."""
        pass
    
    @abstractmethod
    async def update_file(self, project_id: int, name: str, content: str) -> 'ProjectFile':
        """Update a file in the project."""
        pass
    
    @abstractmethod
    async def delete_file(self, project_id: int, name: str) -> bool:
        """Delete a file from the project."""
        pass


class IBacktestManager(ABC):
    """
    Interface for backtest management operations.
    Handles backtest execution, monitoring, and result retrieval.
    """
    
    @abstractmethod
    async def create_backtest(self, project_id: int, compile_id: str, name: str) -> 'Backtest':
        """Create a new backtest."""
        pass
    
    @abstractmethod
    async def get_backtest(self, project_id: int, backtest_id: str) -> 'Backtest':
        """Get backtest details."""
        pass
    
    @abstractmethod
    async def list_backtests(self, project_id: int) -> List['Backtest']:
        """List all backtests for a project."""
        pass
    
    @abstractmethod
    async def delete_backtest(self, project_id: int, backtest_id: str) -> bool:
        """Delete a backtest."""
        pass
    
    @abstractmethod
    async def get_backtest_logs(self, project_id: int, backtest_id: str) -> List[str]:
        """Get backtest execution logs."""
        pass
    
    @abstractmethod
    async def get_backtest_results(self, project_id: int, backtest_id: str) -> 'BacktestResult':
        """Get backtest results and performance metrics."""
        pass


class ILiveAlgorithmManager(ABC):
    """
    Interface for live algorithm management.
    Handles deployment and monitoring of live trading algorithms.
    """
    
    @abstractmethod
    async def create_live_algorithm(self, project_id: int, compile_id: str, 
                                  node_id: str, brokerage: str) -> 'LiveAlgorithm':
        """Deploy a live trading algorithm."""
        pass
    
    @abstractmethod
    async def get_live_algorithm(self, project_id: int, deploy_id: str) -> 'LiveAlgorithm':
        """Get live algorithm details."""
        pass
    
    @abstractmethod
    async def list_live_algorithms(self, project_id: int) -> List['LiveAlgorithm']:
        """List all live algorithms for a project."""
        pass
    
    @abstractmethod
    async def stop_live_algorithm(self, project_id: int, deploy_id: str) -> bool:
        """Stop a live trading algorithm."""
        pass
    
    @abstractmethod
    async def get_live_logs(self, project_id: int, deploy_id: str) -> List[str]:
        """Get live algorithm logs."""
        pass
    
    @abstractmethod
    async def liquidate_live_algorithm(self, project_id: int, deploy_id: str) -> bool:
        """Liquidate all positions for a live algorithm."""
        pass


class IDataManager(ABC):
    """
    Interface for data management operations.
    Handles data uploads, downloads, and management through the API.
    """
    
    @abstractmethod
    async def list_data_links(self) -> List['DataLink']:
        """List available data links."""
        pass
    
    @abstractmethod
    async def get_data_prices(self, organization_id: str) -> Dict[str, Decimal]:
        """Get data pricing information."""
        pass
    
    @abstractmethod
    async def create_data_order(self, dataset_id: str, organization_id: str) -> 'DataOrder':
        """Create a data purchase order."""
        pass
    
    @abstractmethod
    async def list_data_orders(self) -> List['DataOrder']:
        """List data orders for the user."""
        pass


class INodeManager(ABC):
    """
    Interface for compute node management.
    Handles allocation and management of compute resources.
    """
    
    @abstractmethod
    async def list_nodes(self) -> List['Node']:
        """List available compute nodes."""
        pass
    
    @abstractmethod
    async def get_node(self, node_id: str) -> 'Node':
        """Get node details."""
        pass
    
    @abstractmethod
    async def create_node(self, node_type: str, organization_id: str) -> 'Node':
        """Create a new compute node."""
        pass
    
    @abstractmethod
    async def delete_node(self, node_id: str) -> bool:
        """Delete a compute node."""
        pass


class IApiWebSocketClient(ABC):
    """
    Interface for WebSocket-based real-time API communication.
    Handles streaming data and real-time updates.
    """
    
    @abstractmethod
    async def connect(self, url: str, headers: Optional[Dict[str, str]] = None) -> None:
        """Connect to WebSocket endpoint."""
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from WebSocket."""
        pass
    
    @abstractmethod
    async def send_message(self, message: Dict[str, Any]) -> None:
        """Send a message through WebSocket."""
        pass
    
    @abstractmethod
    async def listen(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Listen for incoming WebSocket messages."""
        pass
    
    @abstractmethod
    def add_message_handler(self, message_type: str, handler: Callable) -> None:
        """Add a handler for specific message types."""
        pass
    
    @abstractmethod
    def remove_message_handler(self, message_type: str) -> None:
        """Remove a message handler."""
        pass


class IApiRateLimiter(ABC):
    """
    Interface for API rate limiting.
    Manages request throttling to comply with API rate limits.
    """
    
    @abstractmethod
    async def acquire_permit(self, endpoint: str) -> None:
        """Acquire a permit to make an API request."""
        pass
    
    @abstractmethod
    def get_remaining_requests(self, endpoint: str) -> int:
        """Get the number of remaining requests for an endpoint."""
        pass
    
    @abstractmethod
    def get_reset_time(self, endpoint: str) -> Optional[datetime]:
        """Get the time when rate limit resets for an endpoint."""
        pass
    
    @abstractmethod
    def update_rate_limit_info(self, endpoint: str, headers: Dict[str, str]) -> None:
        """Update rate limit information from response headers."""
        pass


class IApiCache(ABC):
    """
    Interface for API response caching.
    Manages caching of API responses to reduce unnecessary requests.
    """
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get cached value by key."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set cached value with optional TTL."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete cached value."""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """Clear all cached values."""
        pass
    
    @abstractmethod
    def generate_cache_key(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> str:
        """Generate cache key for endpoint and parameters."""
        pass