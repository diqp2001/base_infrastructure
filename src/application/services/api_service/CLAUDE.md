# ApiService

## Overview

The `ApiService` provides a comprehensive HTTP client abstraction for integrating with external REST APIs and web services. It offers a unified interface for API communication with built-in authentication, error handling, file operations, pagination support, and session management.

## Responsibilities

### HTTP Client Operations
- **HTTP Methods**: Support for GET, POST, PUT, DELETE operations with consistent interface
- **Session Management**: Persistent connection handling with automatic header management
- **Request/Response Handling**: JSON parsing, error handling, and response validation
- **Timeout Management**: Configurable timeouts with proper exception handling

### Authentication Support
- **Bearer Token**: OAuth 2.0 and API token authentication
- **Basic Auth**: Username/password authentication
- **API Key**: Custom header-based API key authentication
- **Header Management**: Dynamic header addition/removal during runtime

### File Operations
- **File Upload**: Multipart form upload with additional form data support
- **File Download**: Streaming download with chunked processing for large files
- **Progress Handling**: Support for monitoring file transfer progress
- **Error Recovery**: Robust error handling for file operation failures

### Advanced Features
- **Pagination**: Automatic pagination handling for large datasets
- **Health Checks**: API availability and status monitoring
- **Context Management**: Python context manager support for resource cleanup
- **Response Formats**: Support for JSON and text responses

## Architecture

### Service Design
```python
class ApiService:
    def __init__(self, api_url: str, headers: Dict[str, str] = None, timeout: int = 30):
        self.api_url = api_url.rstrip('/')
        self.session = requests.Session()
        self.timeout = timeout
```

### Session-Based Architecture
- **Persistent Connections**: Reuses HTTP connections for better performance
- **Header Management**: Centralized header management across all requests
- **Authentication State**: Maintains authentication state throughout session lifecycle
- **Resource Cleanup**: Proper session cleanup and resource management

## Key Features

### 1. Unified HTTP Interface
```python
# Initialize service
api = ApiService("https://api.example.com", timeout=60)

# Set authentication
api.set_authentication('bearer', token='your-jwt-token')

# Make requests
data = api.fetch_data('/users/123')
result = api.post_data('/users', {'name': 'John', 'email': 'john@example.com'})
api.put_data('/users/123', {'name': 'John Updated'})
api.delete_resource('/users/123')
```

### 2. Multiple Authentication Methods
```python
# Bearer token authentication
api.set_authentication('bearer', token='jwt-token-here')

# Basic authentication  
api.set_authentication('basic', username='user', password='pass')

# API key authentication
api.set_authentication('api_key', api_key='key123', key_header='X-API-Key')
```

### 3. File Operations
```python
# Upload file
response = api.upload_file(
    endpoint='/upload',
    file_path='/path/to/file.pdf',
    file_field='document',
    additional_data={'category': 'report', 'public': True}
)

# Download file
success = api.download_file(
    endpoint='/files/report.pdf',
    save_path='/downloads/report.pdf',
    params={'version': 'latest'}
)
```

### 4. Pagination Support
```python
# Fetch all paginated data
all_users = api.paginated_fetch(
    endpoint='/users',
    params={'status': 'active'},
    page_param='page',
    per_page_param='limit',
    max_pages=10
)
```

## Usage Patterns

### REST API Integration
```python
class UserApiClient:
    def __init__(self, api_base_url: str, api_key: str):
        self.api = ApiService(api_base_url)
        self.api.set_authentication('api_key', api_key=api_key)
    
    def get_user(self, user_id: int):
        return self.api.fetch_data(f'/users/{user_id}')
    
    def create_user(self, user_data: dict):
        return self.api.post_data('/users', user_data)
    
    def update_user(self, user_id: int, updates: dict):
        return self.api.put_data(f'/users/{user_id}', updates)
    
    def delete_user(self, user_id: int):
        return self.api.delete_resource(f'/users/{user_id}')
```

### Data Provider Integration
```python
class MarketDataProvider:
    def __init__(self):
        self.api = ApiService("https://api.marketdata.com")
        self.api.set_authentication('bearer', token=os.getenv('MARKET_API_TOKEN'))
    
    def get_stock_price(self, symbol: str):
        return self.api.fetch_data(f'/stocks/{symbol}/price')
    
    def get_historical_data(self, symbol: str, days: int = 30):
        return self.api.fetch_data(f'/stocks/{symbol}/history', 
                                 params={'days': days})
    
    def get_all_stocks(self):
        return self.api.paginated_fetch('/stocks', max_pages=50)
```

### File Management Service
```python
class DocumentService:
    def __init__(self, document_api_url: str):
        self.api = ApiService(document_api_url)
    
    def upload_document(self, file_path: str, metadata: dict = None):
        return self.api.upload_file(
            endpoint='/documents',
            file_path=file_path,
            additional_data=metadata or {}
        )
    
    def download_document(self, doc_id: str, save_path: str):
        return self.api.download_file(
            endpoint=f'/documents/{doc_id}/download',
            save_path=save_path
        )
```

### Context Manager Usage
```python
# Automatic resource cleanup
with ApiService("https://api.example.com") as api:
    api.set_authentication('bearer', token='token')
    data = api.fetch_data('/endpoint')
    # Session automatically closed on exit
```

## Authentication Methods

### Bearer Token Authentication
- **JWT Tokens**: OAuth 2.0 and JSON Web Token support
- **API Tokens**: Simple token-based authentication
- **Header Format**: `Authorization: Bearer <token>`

### Basic Authentication
- **Username/Password**: HTTP Basic Auth support
- **Base64 Encoding**: Automatic credential encoding
- **Header Format**: `Authorization: Basic <encoded-credentials>`

### API Key Authentication
- **Custom Headers**: Configurable header names (default: X-API-Key)
- **Query Parameters**: Support for API keys in URL parameters
- **Multiple Keys**: Support for multiple simultaneous API keys

## Error Handling

### HTTP Error Management
```python
# Automatic status code checking
response = api.fetch_data('/endpoint')
if response is None:
    # Handle request failure
    pass
```

### Exception Categories
- **Connection Errors**: Network connectivity issues, DNS resolution failures
- **Timeout Errors**: Request timeout handling with configurable limits
- **Authentication Errors**: 401/403 status codes with clear error messages
- **Rate Limiting**: 429 status code handling with retry suggestions
- **Server Errors**: 5xx status code handling with error reporting

### Response Format Handling
- **JSON Responses**: Automatic JSON parsing with fallback to text
- **Non-JSON Responses**: Text content preservation with metadata
- **Empty Responses**: Proper handling of empty response bodies
- **Malformed Responses**: Graceful degradation for invalid JSON

## Performance Features

### Connection Optimization
- **Session Reuse**: Persistent HTTP connections for better performance
- **Connection Pooling**: Automatic connection pool management
- **Keep-Alive**: HTTP keep-alive support for reduced connection overhead
- **Streaming Downloads**: Memory-efficient handling of large files

### Request Efficiency
- **Header Persistence**: Headers set once, used for all requests
- **Parameter Handling**: Efficient parameter encoding and URL construction
- **Chunked Transfer**: Support for chunked encoding for large uploads
- **Compression**: Automatic gzip/deflate decompression

### Pagination Optimization
- **Intelligent Stopping**: Automatic detection of pagination end conditions
- **Batch Processing**: Efficient handling of large paginated datasets
- **Memory Management**: Streaming processing for large result sets
- **Rate Limiting**: Built-in delays for API rate limit compliance

## Configuration

### Basic Configuration
```python
api = ApiService(
    api_url="https://api.example.com",
    headers={'User-Agent': 'MyApp/1.0'},
    timeout=30
)
```

### Advanced Configuration
```python
# Custom session configuration
api = ApiService("https://api.example.com")
api.session.proxies.update({'https': 'https://proxy.example.com:8080'})
api.session.verify = '/path/to/ca-bundle.pem'
api.add_header('Accept-Language', 'en-US')
```

### Dynamic Configuration
```python
# Runtime header management
api.add_header('X-Request-ID', str(uuid.uuid4()))
api.set_timeout(60)
api.remove_header('Cache-Control')
```

## Dependencies

### Required Packages
```python
import requests
from typing import Dict, Any, Optional, List
import json
```

### External Dependencies
- **requests**: HTTP library for Python with session support
- **json**: JSON parsing and serialization
- **typing**: Type hints for better code documentation

## Testing Strategy

### Unit Testing
```python
def test_api_service_get():
    with ApiService("https://httpbin.org") as api:
        response = api.fetch_data('/get', params={'test': 'value'})
        assert response is not None
        assert 'args' in response
```

### Integration Testing
```python
def test_authentication():
    api = ApiService("https://api.example.com")
    api.set_authentication('bearer', token='test-token')
    assert 'Authorization' in api.session.headers
    assert api.session.headers['Authorization'] == 'Bearer test-token'
```

### Mock Testing
```python
@patch('requests.Session.get')
def test_fetch_data_with_mock(mock_get):
    mock_response = Mock()
    mock_response.json.return_value = {'test': 'data'}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response
    
    api = ApiService("https://api.example.com")
    result = api.fetch_data('/test')
    assert result['test'] == 'data'
```

## Best Practices

### Usage Guidelines
1. **Use context managers** for automatic resource cleanup
2. **Set appropriate timeouts** based on expected response times
3. **Handle authentication centrally** at service initialization
4. **Implement retry logic** for transient failures
5. **Log API calls** for debugging and monitoring

### Security Considerations
1. **Secure credential storage** - never hardcode API keys
2. **Use HTTPS endpoints** for all API communications
3. **Validate SSL certificates** in production environments
4. **Implement request signing** for sensitive operations
5. **Monitor for suspicious activity** and rate limiting

### Performance Optimization
1. **Reuse service instances** to benefit from connection pooling
2. **Use pagination** for large datasets to reduce memory usage
3. **Implement caching** for frequently accessed data
4. **Set appropriate timeouts** to prevent hanging requests
5. **Monitor API rate limits** and implement backoff strategies