"""
API-specific exceptions for error handling.
These exceptions provide structured error handling for API operations.
"""

from typing import Optional, Dict, Any


class ApiException(Exception):
    """Base exception for all API-related errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, 
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_data = response_data or {}
    
    def __str__(self) -> str:
        """String representation of the exception."""
        if self.status_code:
            return f"HTTP {self.status_code}: {self.message}"
        return self.message


class AuthenticationException(ApiException):
    """Exception raised when authentication fails."""
    
    def __init__(self, message: str = "Authentication failed", 
                 status_code: Optional[int] = 401, 
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code, response_data)


class AuthorizationException(ApiException):
    """Exception raised when authorization fails (insufficient permissions)."""
    
    def __init__(self, message: str = "Access denied", 
                 status_code: Optional[int] = 403, 
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code, response_data)


class RateLimitException(ApiException):
    """Exception raised when API rate limit is exceeded."""
    
    def __init__(self, message: str = "Rate limit exceeded", 
                 status_code: Optional[int] = 429,
                 retry_after: Optional[int] = None,
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code, response_data)
        self.retry_after = retry_after
    
    def __str__(self) -> str:
        """String representation with retry information."""
        base_str = super().__str__()
        if self.retry_after:
            return f"{base_str} (retry after {self.retry_after} seconds)"
        return base_str


class QuotaExceededException(ApiException):
    """Exception raised when usage quota is exceeded."""
    
    def __init__(self, message: str = "Usage quota exceeded", 
                 status_code: Optional[int] = 402,
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code, response_data)


class ValidationException(ApiException):
    """Exception raised when request validation fails."""
    
    def __init__(self, message: str, validation_errors: Optional[Dict[str, Any]] = None,
                 status_code: Optional[int] = 400,
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code, response_data)
        self.validation_errors = validation_errors or {}
    
    def __str__(self) -> str:
        """String representation with validation details."""
        base_str = super().__str__()
        if self.validation_errors:
            errors_str = ", ".join([f"{k}: {v}" for k, v in self.validation_errors.items()])
            return f"{base_str} (Validation errors: {errors_str})"
        return base_str


class ResourceNotFoundException(ApiException):
    """Exception raised when a requested resource is not found."""
    
    def __init__(self, resource_type: str, resource_id: str = "", 
                 status_code: Optional[int] = 404,
                 response_data: Optional[Dict[str, Any]] = None):
        message = f"{resource_type} not found"
        if resource_id:
            message += f" (ID: {resource_id})"
        super().__init__(message, status_code, response_data)
        self.resource_type = resource_type
        self.resource_id = resource_id


class ProjectNotFoundException(ResourceNotFoundException):
    """Exception raised when a project is not found."""
    
    def __init__(self, project_id: str, 
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__("Project", project_id, 404, response_data)


class BacktestNotFoundException(ResourceNotFoundException):
    """Exception raised when a backtest is not found."""
    
    def __init__(self, backtest_id: str, 
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__("Backtest", backtest_id, 404, response_data)


class LiveAlgorithmNotFoundException(ResourceNotFoundException):
    """Exception raised when a live algorithm is not found."""
    
    def __init__(self, deploy_id: str, 
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__("Live Algorithm", deploy_id, 404, response_data)


class CompilationException(ApiException):
    """Exception raised when algorithm compilation fails."""
    
    def __init__(self, message: str = "Compilation failed", 
                 compile_logs: Optional[list] = None,
                 status_code: Optional[int] = 400,
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code, response_data)
        self.compile_logs = compile_logs or []
    
    def __str__(self) -> str:
        """String representation with compilation logs."""
        base_str = super().__str__()
        if self.compile_logs:
            logs_str = "\n".join(self.compile_logs[-5:])  # Show last 5 log entries
            return f"{base_str}\nCompilation logs:\n{logs_str}"
        return base_str


class BacktestException(ApiException):
    """Exception raised when backtest execution fails."""
    
    def __init__(self, message: str = "Backtest execution failed", 
                 backtest_id: Optional[str] = None,
                 error_logs: Optional[list] = None,
                 status_code: Optional[int] = 500,
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code, response_data)
        self.backtest_id = backtest_id
        self.error_logs = error_logs or []
    
    def __str__(self) -> str:
        """String representation with error details."""
        base_str = super().__str__()
        if self.backtest_id:
            base_str += f" (Backtest ID: {self.backtest_id})"
        if self.error_logs:
            logs_str = "\n".join(self.error_logs[-3:])  # Show last 3 error logs
            return f"{base_str}\nError logs:\n{logs_str}"
        return base_str


class LiveTradingException(ApiException):
    """Exception raised when live trading operations fail."""
    
    def __init__(self, message: str = "Live trading operation failed", 
                 deploy_id: Optional[str] = None,
                 status_code: Optional[int] = 500,
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code, response_data)
        self.deploy_id = deploy_id
    
    def __str__(self) -> str:
        """String representation with deployment details."""
        base_str = super().__str__()
        if self.deploy_id:
            base_str += f" (Deploy ID: {self.deploy_id})"
        return base_str


class NetworkException(ApiException):
    """Exception raised for network-related errors."""
    
    def __init__(self, message: str = "Network error occurred", 
                 original_exception: Optional[Exception] = None,
                 status_code: Optional[int] = None,
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code, response_data)
        self.original_exception = original_exception
    
    def __str__(self) -> str:
        """String representation with original exception details."""
        base_str = super().__str__()
        if self.original_exception:
            return f"{base_str} (Original: {str(self.original_exception)})"
        return base_str


class TimeoutException(NetworkException):
    """Exception raised when API request times out."""
    
    def __init__(self, message: str = "Request timeout", 
                 timeout_seconds: Optional[float] = None,
                 original_exception: Optional[Exception] = None):
        super().__init__(message, original_exception, 408)
        self.timeout_seconds = timeout_seconds
    
    def __str__(self) -> str:
        """String representation with timeout details."""
        base_str = super().__str__()
        if self.timeout_seconds:
            return f"{base_str} (Timeout: {self.timeout_seconds}s)"
        return base_str


class ConnectionException(NetworkException):
    """Exception raised when connection to API fails."""
    
    def __init__(self, message: str = "Connection failed", 
                 original_exception: Optional[Exception] = None):
        super().__init__(message, original_exception, 503)


class SerializationException(ApiException):
    """Exception raised when data serialization/deserialization fails."""
    
    def __init__(self, message: str = "Serialization error", 
                 data: Optional[Any] = None,
                 original_exception: Optional[Exception] = None):
        super().__init__(message, 500)
        self.data = data
        self.original_exception = original_exception
    
    def __str__(self) -> str:
        """String representation with serialization details."""
        base_str = super().__str__()
        if self.original_exception:
            base_str += f" (Original: {str(self.original_exception)})"
        return base_str


class ConfigurationException(ApiException):
    """Exception raised when API configuration is invalid."""
    
    def __init__(self, message: str = "Invalid configuration", 
                 config_key: Optional[str] = None):
        super().__init__(message, 500)
        self.config_key = config_key
    
    def __str__(self) -> str:
        """String representation with configuration details."""
        base_str = super().__str__()
        if self.config_key:
            return f"{base_str} (Config key: {self.config_key})"
        return base_str


class CacheException(ApiException):
    """Exception raised when cache operations fail."""
    
    def __init__(self, message: str = "Cache operation failed", 
                 cache_key: Optional[str] = None,
                 original_exception: Optional[Exception] = None):
        super().__init__(message, 500)
        self.cache_key = cache_key
        self.original_exception = original_exception
    
    def __str__(self) -> str:
        """String representation with cache details."""
        base_str = super().__str__()
        details = []
        if self.cache_key:
            details.append(f"Key: {self.cache_key}")
        if self.original_exception:
            details.append(f"Original: {str(self.original_exception)}")
        if details:
            return f"{base_str} ({', '.join(details)})"
        return base_str


class WebSocketException(ApiException):
    """Exception raised for WebSocket-related errors."""
    
    def __init__(self, message: str = "WebSocket error", 
                 connection_url: Optional[str] = None,
                 original_exception: Optional[Exception] = None):
        super().__init__(message, 500)
        self.connection_url = connection_url
        self.original_exception = original_exception
    
    def __str__(self) -> str:
        """String representation with WebSocket details."""
        base_str = super().__str__()
        details = []
        if self.connection_url:
            details.append(f"URL: {self.connection_url}")
        if self.original_exception:
            details.append(f"Original: {str(self.original_exception)}")
        if details:
            return f"{base_str} ({', '.join(details)})"
        return base_str


class OptimizationException(ApiException):
    """Exception raised when optimization operations fail."""
    
    def __init__(self, message: str = "Optimization failed", 
                 optimization_id: Optional[str] = None,
                 status_code: Optional[int] = 500,
                 response_data: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code, response_data)
        self.optimization_id = optimization_id
    
    def __str__(self) -> str:
        """String representation with optimization details."""
        base_str = super().__str__()
        if self.optimization_id:
            base_str += f" (Optimization ID: {self.optimization_id})"
        return base_str


# Utility functions for exception handling

def create_exception_from_response(status_code: int, response_data: Dict[str, Any]) -> ApiException:
    """Create appropriate exception based on status code and response data."""
    message = response_data.get('message', 'Unknown error')
    
    if status_code == 400:
        return ValidationException(message, response_data.get('errors'), status_code, response_data)
    elif status_code == 401:
        return AuthenticationException(message, status_code, response_data)
    elif status_code == 403:
        return AuthorizationException(message, status_code, response_data)
    elif status_code == 404:
        return ResourceNotFoundException("Resource", "", status_code, response_data)
    elif status_code == 408:
        return TimeoutException(message)
    elif status_code == 429:
        retry_after = response_data.get('retry_after')
        return RateLimitException(message, status_code, retry_after, response_data)
    elif status_code == 402:
        return QuotaExceededException(message, status_code, response_data)
    elif status_code >= 500:
        return ApiException(message, status_code, response_data)
    else:
        return ApiException(message, status_code, response_data)


def is_retryable_exception(exception: Exception) -> bool:
    """Check if an exception indicates a retryable error."""
    if isinstance(exception, (NetworkException, TimeoutException, ConnectionException)):
        return True
    if isinstance(exception, ApiException) and exception.status_code:
        # Retry on server errors and rate limits
        return exception.status_code >= 500 or exception.status_code == 429
    return False


def get_retry_delay(exception: Exception) -> float:
    """Get suggested retry delay based on exception type."""
    if isinstance(exception, RateLimitException) and exception.retry_after:
        return float(exception.retry_after)
    elif isinstance(exception, ApiException) and exception.status_code == 429:
        return 60.0  # Default rate limit retry delay
    elif isinstance(exception, NetworkException):
        return 5.0   # Network error retry delay
    else:
        return 1.0   # Default retry delay