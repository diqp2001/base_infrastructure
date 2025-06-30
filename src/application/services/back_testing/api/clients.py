"""
API client implementations for QuantConnect Lean.
Main classes for communicating with QuantConnect API endpoints.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import aiohttp
from aiohttp import ClientTimeout, ClientError
from urllib.parse import urljoin

from ..common.interfaces import IApi
from .interfaces import (
    IApiConnection, IProjectManager, IBacktestManager, ILiveAlgorithmManager,
    IDataManager, INodeManager, IApiRateLimiter, IApiCache
)
from .models import (
    ApiConfiguration, Project, ProjectFile, CreateProjectRequest,
    Backtest, CreateBacktestRequest, BacktestResult, LiveAlgorithm,
    CreateLiveAlgorithmRequest, Node, DataLink, DataOrder, LogEntry,
    Organization, OptimizationRequest, OptimizationResult, AuthenticationResponse
)
from .enums import ApiEndpoint, HttpMethod, BacktestStatus, LiveAlgorithmStatus
from .exceptions import (
    ApiException, AuthenticationException, RateLimitException,
    NetworkException, TimeoutException, ConnectionException,
    create_exception_from_response, is_retryable_exception, get_retry_delay
)
from .authentication import AuthenticationManager
from .serialization import ApiSerializer, ApiResponseDeserializer


class ApiConnection(IApiConnection):
    """
    Low-level HTTP connection handler for QuantConnect API.
    Manages HTTP requests, authentication, retries, and error handling.
    """
    
    def __init__(self, config: ApiConfiguration, auth_manager: AuthenticationManager,
                 rate_limiter: Optional[IApiRateLimiter] = None,
                 cache: Optional[IApiCache] = None):
        """Initialize API connection."""
        self.config = config
        self.auth_manager = auth_manager
        self.rate_limiter = rate_limiter
        self.cache = cache
        self.serializer = ApiSerializer()
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(__name__)
        
        # Configure timeout
        self.timeout = ClientTimeout(total=config.timeout)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self):
        """Ensure aiohttp session is created."""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(verify_ssl=self.config.verify_ssl)
            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=self.timeout,
                headers={'User-Agent': 'QuantConnect-Lean-Python-API/1.0'}
            )
    
    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None
    
    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GET request."""
        return await self._make_request(HttpMethod.GET, endpoint, params=params)
    
    async def post(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a POST request."""
        return await self._make_request(HttpMethod.POST, endpoint, data=data)
    
    async def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a PUT request."""
        return await self._make_request(HttpMethod.PUT, endpoint, data=data)
    
    async def delete(self, endpoint: str) -> Dict[str, Any]:
        """Execute a DELETE request."""
        return await self._make_request(HttpMethod.DELETE, endpoint)
    
    def set_authentication(self, token: str, user_id: str) -> None:
        """Set authentication credentials."""
        # This is handled by the auth_manager
        pass
    
    async def _make_request(self, method: HttpMethod, endpoint: str,
                          params: Optional[Dict[str, Any]] = None,
                          data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make HTTP request with retries and error handling."""
        await self._ensure_session()
        
        url = urljoin(self.config.base_url, endpoint.lstrip('/'))
        
        # Apply rate limiting
        if self.rate_limiter:
            await self.rate_limiter.acquire_permit(endpoint)
        
        # Check cache for GET requests
        if method == HttpMethod.GET and self.cache:
            cache_key = self.cache.generate_cache_key(endpoint, params)
            cached_result = await self.cache.get(cache_key)
            if cached_result:
                self.logger.debug(f"Cache hit for {url}")
                return cached_result
        
        # Prepare request
        headers = await self._get_headers()
        request_data = None
        
        if data:
            request_data = self.serializer.serialize(data)
            headers['Content-Type'] = 'application/json'
        
        # Execute request with retries
        last_exception = None
        for attempt in range(self.config.max_retries + 1):
            try:
                self.logger.debug(f"Making {method.value} request to {url} (attempt {attempt + 1})")
                
                async with self.session.request(
                    method.value,
                    url,
                    headers=headers,
                    params=params,
                    data=request_data
                ) as response:
                    # Update rate limit info
                    if self.rate_limiter and response.headers:
                        self.rate_limiter.update_rate_limit_info(endpoint, dict(response.headers))
                    
                    # Handle response
                    response_data = await self._handle_response(response)
                    
                    # Cache GET responses
                    if method == HttpMethod.GET and self.cache and response.status == 200:
                        cache_key = self.cache.generate_cache_key(endpoint, params)
                        await self.cache.set(cache_key, response_data, self.config.cache_ttl)
                    
                    return response_data
                    
            except Exception as e:
                last_exception = e
                
                if not is_retryable_exception(e) or attempt == self.config.max_retries:
                    break
                
                # Calculate retry delay
                delay = get_retry_delay(e) * (2 ** attempt)  # Exponential backoff
                self.logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {delay}s: {str(e)}")
                await asyncio.sleep(delay)
        
        # All retries exhausted
        if last_exception:
            if isinstance(last_exception, ApiException):
                raise last_exception
            else:
                raise NetworkException("Request failed after all retries", last_exception)
        else:
            raise NetworkException("Request failed for unknown reason")
    
    async def _get_headers(self) -> Dict[str, str]:
        """Get request headers including authentication."""
        headers = {
            'Accept': 'application/json',
        }
        
        if self.auth_manager.is_authenticated():
            try:
                auth_headers = self.auth_manager.get_auth_headers()
                headers.update(auth_headers)
            except AuthenticationException:
                # Try to get a fresh token
                try:
                    await self.auth_manager.get_valid_token()
                    auth_headers = self.auth_manager.get_auth_headers()
                    headers.update(auth_headers)
                except Exception as e:
                    raise AuthenticationException(f"Failed to get valid authentication: {str(e)}")
        
        return headers
    
    async def _handle_response(self, response: aiohttp.ClientResponse) -> Dict[str, Any]:
        """Handle HTTP response and convert to dict."""
        try:
            response_text = await response.text()
            
            # Handle successful responses
            if 200 <= response.status < 300:
                if response_text:
                    return self.serializer.deserialize(response_text, dict)
                else:
                    return {'success': True}
            
            # Handle error responses
            error_data = {}
            if response_text:
                try:
                    error_data = self.serializer.deserialize(response_text, dict)
                except Exception:
                    error_data = {'message': response_text}
            
            # Create appropriate exception
            exception = create_exception_from_response(response.status, error_data)
            raise exception
            
        except ClientError as e:
            raise NetworkException(f"Network error: {str(e)}", e)
        except asyncio.TimeoutError as e:
            raise TimeoutException("Request timeout", self.config.timeout, e)


class QuantConnectApiClient(IApi):
    """
    Main QuantConnect API client implementing all API functionality.
    Provides high-level interface for all QuantConnect API operations.
    """
    
    def __init__(self, config: Optional[ApiConfiguration] = None,
                 connection: Optional[IApiConnection] = None,
                 auth_manager: Optional[AuthenticationManager] = None):
        """Initialize API client."""
        self.config = config or ApiConfiguration()
        self.auth_manager = auth_manager or AuthenticationManager(self.config)
        self.connection = connection or ApiConnection(self.config, self.auth_manager)
        self.deserializer = ApiResponseDeserializer()
        self.logger = logging.getLogger(__name__)
        
        # Initialize managers
        self._project_manager: Optional[ProjectManager] = None
        self._backtest_manager: Optional[BacktestManager] = None
        self._live_manager: Optional[LiveAlgorithmManager] = None
        self._data_manager: Optional[DataManager] = None
        self._node_manager: Optional[NodeManager] = None
    
    @property
    def projects(self) -> 'ProjectManager':
        """Get project manager."""
        if not self._project_manager:
            self._project_manager = ProjectManager(self.connection, self.deserializer)
        return self._project_manager
    
    @property
    def backtests(self) -> 'BacktestManager':
        """Get backtest manager."""
        if not self._backtest_manager:
            self._backtest_manager = BacktestManager(self.connection, self.deserializer)
        return self._backtest_manager
    
    @property
    def live(self) -> 'LiveAlgorithmManager':
        """Get live algorithm manager."""
        if not self._live_manager:
            self._live_manager = LiveAlgorithmManager(self.connection, self.deserializer)
        return self._live_manager
    
    @property
    def data(self) -> 'DataManager':
        """Get data manager."""
        if not self._data_manager:
            self._data_manager = DataManager(self.connection, self.deserializer)
        return self._data_manager
    
    @property
    def nodes(self) -> 'NodeManager':
        """Get node manager."""
        if not self._node_manager:
            self._node_manager = NodeManager(self.connection, self.deserializer)
        return self._node_manager
    
    async def authenticate(self, token: str) -> bool:
        """Authenticate with API using token."""
        try:
            # Parse token to extract credentials
            credentials = {'token': token}
            
            # Try API key authentication first
            if ':' in token:
                parts = token.split(':', 1)
                if len(parts) == 2:
                    credentials = {'api_key': parts[0], 'api_secret': parts[1]}
                    self.auth_manager.set_api_key_provider(parts[0], parts[1])
                    response = await self.auth_manager.authenticate(
                        self.auth_manager.get_current_auth_type() or 'API_KEY', credentials
                    )
                    return response.is_authenticated()
            
            return False
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {str(e)}")
            return False
    
    async def create_project(self, name: str, language: str) -> Dict[str, Any]:
        """Create a new project."""
        return await self.projects.create_project(name, language)
    
    async def read_project(self, project_id: int) -> Dict[str, Any]:
        """Read project details."""
        project = await self.projects.get_project(project_id)
        return {
            'project_id': project.project_id,
            'name': project.name,
            'language': project.language.value,
            'created': project.created.isoformat(),
            'modified': project.modified.isoformat(),
            'description': project.description
        }
    
    async def update_project(self, project_id: int, **kwargs) -> Dict[str, Any]:
        """Update project details."""
        project = await self.projects.update_project(project_id, **kwargs)
        return {
            'project_id': project.project_id,
            'name': project.name,
            'language': project.language.value,
            'description': project.description
        }
    
    async def delete_project(self, project_id: int) -> bool:
        """Delete a project."""
        return await self.projects.delete_project(project_id)
    
    async def close(self):
        """Close the API client and clean up resources."""
        if hasattr(self.connection, 'close'):
            await self.connection.close()


class ProjectManager(IProjectManager):
    """Manager for project operations."""
    
    def __init__(self, connection: IApiConnection, deserializer: ApiResponseDeserializer):
        self.connection = connection
        self.deserializer = deserializer
    
    async def create_project(self, name: str, language: str, description: str = "") -> Project:
        """Create a new project."""
        request_data = {
            'name': name,
            'language': language,
            'description': description
        }
        
        response = await self.connection.post(ApiEndpoint.PROJECTS_CREATE.value, request_data)
        return self.deserializer.deserialize_response(str(response), Project)
    
    async def get_project(self, project_id: int) -> Project:
        """Get project details."""
        endpoint = ApiEndpoint.PROJECTS_READ.value.format(projectId=project_id)
        response = await self.connection.get(endpoint)
        return self.deserializer.deserialize_response(str(response), Project)
    
    async def update_project(self, project_id: int, **kwargs) -> Project:
        """Update project details."""
        endpoint = ApiEndpoint.PROJECTS_UPDATE.value.format(projectId=project_id)
        response = await self.connection.put(endpoint, kwargs)
        return self.deserializer.deserialize_response(str(response), Project)
    
    async def delete_project(self, project_id: int) -> bool:
        """Delete a project."""
        endpoint = ApiEndpoint.PROJECTS_DELETE.value.format(projectId=project_id)
        response = await self.connection.delete(endpoint)
        return response.get('success', False)
    
    async def list_projects(self) -> List[Project]:
        """List all projects."""
        response = await self.connection.get(ApiEndpoint.PROJECTS_LIST.value)
        return self.deserializer.deserialize_list_response(str(response), Project)
    
    async def add_file(self, project_id: int, name: str, content: str) -> ProjectFile:
        """Add a file to project."""
        endpoint = ApiEndpoint.FILES_CREATE.value.format(projectId=project_id)
        request_data = {'name': name, 'content': content}
        response = await self.connection.post(endpoint, request_data)
        return self.deserializer.deserialize_response(str(response), ProjectFile)
    
    async def update_file(self, project_id: int, name: str, content: str) -> ProjectFile:
        """Update a file in project."""
        endpoint = ApiEndpoint.FILES_UPDATE.value.format(projectId=project_id)
        request_data = {'name': name, 'content': content}
        response = await self.connection.put(endpoint, request_data)
        return self.deserializer.deserialize_response(str(response), ProjectFile)
    
    async def delete_file(self, project_id: int, name: str) -> bool:
        """Delete a file from project."""
        endpoint = ApiEndpoint.FILES_DELETE.value.format(projectId=project_id)
        params = {'name': name}
        response = await self.connection.delete(endpoint)
        return response.get('success', False)


class BacktestManager(IBacktestManager):
    """Manager for backtest operations."""
    
    def __init__(self, connection: IApiConnection, deserializer: ApiResponseDeserializer):
        self.connection = connection
        self.deserializer = deserializer
    
    async def create_backtest(self, project_id: int, compile_id: str, name: str) -> Backtest:
        """Create a new backtest."""
        endpoint = ApiEndpoint.BACKTESTS_CREATE.value.format(projectId=project_id)
        request_data = {
            'compileId': compile_id,
            'backtestName': name
        }
        response = await self.connection.post(endpoint, request_data)
        return self.deserializer.deserialize_response(str(response), Backtest)
    
    async def get_backtest(self, project_id: int, backtest_id: str) -> Backtest:
        """Get backtest details."""
        endpoint = ApiEndpoint.BACKTESTS_READ.value.format(
            projectId=project_id, backtestId=backtest_id
        )
        response = await self.connection.get(endpoint)
        return self.deserializer.deserialize_response(str(response), Backtest)
    
    async def list_backtests(self, project_id: int) -> List[Backtest]:
        """List all backtests for a project."""
        endpoint = ApiEndpoint.BACKTESTS_LIST.value.format(projectId=project_id)
        response = await self.connection.get(endpoint)
        return self.deserializer.deserialize_list_response(str(response), Backtest)
    
    async def delete_backtest(self, project_id: int, backtest_id: str) -> bool:
        """Delete a backtest."""
        endpoint = ApiEndpoint.BACKTESTS_DELETE.value.format(
            projectId=project_id, backtestId=backtest_id
        )
        response = await self.connection.delete(endpoint)
        return response.get('success', False)
    
    async def get_backtest_logs(self, project_id: int, backtest_id: str) -> List[str]:
        """Get backtest logs."""
        endpoint = ApiEndpoint.LOGS_READ.value.format(
            projectId=project_id, algorithmId=backtest_id
        )
        response = await self.connection.get(endpoint)
        return response.get('logs', [])
    
    async def get_backtest_results(self, project_id: int, backtest_id: str) -> BacktestResult:
        """Get backtest results."""
        backtest = await self.get_backtest(project_id, backtest_id)
        if backtest.result:
            return backtest.result
        else:
            # Return empty result if not available
            return BacktestResult()


class LiveAlgorithmManager(ILiveAlgorithmManager):
    """Manager for live algorithm operations."""
    
    def __init__(self, connection: IApiConnection, deserializer: ApiResponseDeserializer):
        self.connection = connection
        self.deserializer = deserializer
    
    async def create_live_algorithm(self, project_id: int, compile_id: str, 
                                  node_id: str, brokerage: str) -> LiveAlgorithm:
        """Deploy a live algorithm."""
        endpoint = ApiEndpoint.LIVE_CREATE.value.format(projectId=project_id)
        request_data = {
            'compileId': compile_id,
            'nodeId': node_id,
            'brokerage': brokerage
        }
        response = await self.connection.post(endpoint, request_data)
        return self.deserializer.deserialize_response(str(response), LiveAlgorithm)
    
    async def get_live_algorithm(self, project_id: int, deploy_id: str) -> LiveAlgorithm:
        """Get live algorithm details."""
        endpoint = ApiEndpoint.LIVE_READ.value.format(
            projectId=project_id, deployId=deploy_id
        )
        response = await self.connection.get(endpoint)
        return self.deserializer.deserialize_response(str(response), LiveAlgorithm)
    
    async def list_live_algorithms(self, project_id: int) -> List[LiveAlgorithm]:
        """List live algorithms."""
        endpoint = ApiEndpoint.LIVE_LIST.value.format(projectId=project_id)
        response = await self.connection.get(endpoint)
        return self.deserializer.deserialize_list_response(str(response), LiveAlgorithm)
    
    async def stop_live_algorithm(self, project_id: int, deploy_id: str) -> bool:
        """Stop a live algorithm."""
        endpoint = ApiEndpoint.LIVE_STOP.value.format(
            projectId=project_id, deployId=deploy_id
        )
        response = await self.connection.post(endpoint)
        return response.get('success', False)
    
    async def get_live_logs(self, project_id: int, deploy_id: str) -> List[str]:
        """Get live algorithm logs."""
        endpoint = ApiEndpoint.LOGS_READ.value.format(
            projectId=project_id, algorithmId=deploy_id
        )
        response = await self.connection.get(endpoint)
        return response.get('logs', [])
    
    async def liquidate_live_algorithm(self, project_id: int, deploy_id: str) -> bool:
        """Liquidate live algorithm positions."""
        endpoint = ApiEndpoint.LIVE_LIQUIDATE.value.format(
            projectId=project_id, deployId=deploy_id
        )
        response = await self.connection.post(endpoint)
        return response.get('success', False)


class DataManager(IDataManager):
    """Manager for data operations."""
    
    def __init__(self, connection: IApiConnection, deserializer: ApiResponseDeserializer):
        self.connection = connection
        self.deserializer = deserializer
    
    async def list_data_links(self) -> List[DataLink]:
        """List available data links."""
        response = await self.connection.get(ApiEndpoint.DATA_LINKS.value)
        return self.deserializer.deserialize_list_response(str(response), DataLink)
    
    async def get_data_prices(self, organization_id: str) -> Dict[str, Any]:
        """Get data pricing."""
        endpoint = ApiEndpoint.DATA_PRICES.value.format(organizationId=organization_id)
        response = await self.connection.get(endpoint)
        return response
    
    async def create_data_order(self, dataset_id: str, organization_id: str) -> DataOrder:
        """Create data order."""
        request_data = {
            'datasetId': dataset_id,
            'organizationId': organization_id
        }
        response = await self.connection.post(ApiEndpoint.DATA_ORDER_CREATE.value, request_data)
        return self.deserializer.deserialize_response(str(response), DataOrder)
    
    async def list_data_orders(self) -> List[DataOrder]:
        """List data orders."""
        response = await self.connection.get(ApiEndpoint.DATA_ORDER_LIST.value)
        return self.deserializer.deserialize_list_response(str(response), DataOrder)


class NodeManager(INodeManager):
    """Manager for compute node operations."""
    
    def __init__(self, connection: IApiConnection, deserializer: ApiResponseDeserializer):
        self.connection = connection
        self.deserializer = deserializer
    
    async def list_nodes(self) -> List[Node]:
        """List compute nodes."""
        response = await self.connection.get(ApiEndpoint.NODES_LIST.value)
        return self.deserializer.deserialize_list_response(str(response), Node)
    
    async def get_node(self, node_id: str) -> Node:
        """Get node details."""
        endpoint = ApiEndpoint.NODES_READ.value.format(nodeId=node_id)
        response = await self.connection.get(endpoint)
        return self.deserializer.deserialize_response(str(response), Node)
    
    async def create_node(self, node_type: str, organization_id: str) -> Node:
        """Create compute node."""
        request_data = {
            'nodeType': node_type,
            'organizationId': organization_id
        }
        response = await self.connection.post(ApiEndpoint.NODES_CREATE.value, request_data)
        return self.deserializer.deserialize_response(str(response), Node)
    
    async def delete_node(self, node_id: str) -> bool:
        """Delete compute node."""
        endpoint = ApiEndpoint.NODES_DELETE.value.format(nodeId=node_id)
        response = await self.connection.delete(endpoint)
        return response.get('success', False)