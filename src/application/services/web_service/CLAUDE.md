# WebService

## Overview

The `WebService` provides a comprehensive web server abstraction layer that enables easy setup, configuration, and management of web applications. It serves as a unified interface for web server operations with support for multiple frameworks (Flask, FastAPI), middleware management, routing, and production-ready features like CORS, authentication, and static file serving.

## Responsibilities

### Server Management
- **Server Lifecycle**: Start, stop, and restart web servers with proper threading support
- **Configuration Management**: Centralized configuration with flexible key-value storage
- **Health Monitoring**: Server status tracking and health check endpoints
- **Thread Management**: Non-blocking server execution with proper cleanup

### Routing and Middleware
- **Route Management**: Dynamic route registration with HTTP method specification
- **Middleware Pipeline**: Configurable middleware chain for request processing
- **Request Handling**: Unified request/response handling abstraction
- **Error Management**: Comprehensive error handling with proper HTTP status codes

### Framework Integration
- **Flask Integration**: Automatic Flask application creation with route registration
- **FastAPI Integration**: Async-compatible FastAPI application creation
- **Framework Agnostic**: Core functionality independent of specific web frameworks
- **Migration Support**: Easy switching between web frameworks

### Production Features
- **CORS Support**: Cross-Origin Resource Sharing configuration
- **Authentication**: Pluggable authentication middleware
- **Static Files**: Static file serving configuration
- **Security**: Security middleware and request validation

## Architecture

### Service Design
```python
class WebService:
    def __init__(self, host: str = '127.0.0.1', port: int = 5000, debug: bool = False):
        self.host = host
        self.port = port
        self.routes = {}
        self.middleware = []
        self.config = {}
```

### Threading Model
- **Non-blocking Execution**: Server runs in separate daemon thread
- **Graceful Shutdown**: Proper thread joining with timeout handling
- **Thread Safety**: Safe concurrent access to server state
- **Resource Management**: Automatic cleanup of server resources

## Key Features

### 1. Unified Server Management
```python
# Initialize web service
web_service = WebService(host='0.0.0.0', port=8080, debug=True)

# Configure server
web_service.set_config('app_name', 'My API Service')
web_service.set_config('version', '1.0.0')

# Start server (non-blocking)
web_service.start_server(blocking=False)

# Check status
status = web_service.get_server_status()
print(f"Server running: {status['is_running']}")

# Stop server
web_service.stop_server()
```

### 2. Route Management and Middleware
```python
# Define route handlers
def hello_handler(request_context):
    return {'message': 'Hello, World!', 'path': request_context['path']}

def api_handler(request_context):
    return {'data': request_context['data'], 'method': request_context['method']}

# Register routes
web_service.add_route('/hello', hello_handler, methods=['GET'])
web_service.add_route('/api/data', api_handler, methods=['GET', 'POST'])

# Add middleware
def logging_middleware(request_context):
    print(f"Request: {request_context['method']} {request_context['path']}")
    return request_context

def cors_middleware(request_context):
    # Add CORS headers (simplified)
    request_context.setdefault('response_headers', {})
    request_context['response_headers']['Access-Control-Allow-Origin'] = '*'
    return request_context

web_service.add_middleware(logging_middleware)
web_service.add_middleware(cors_middleware)
```

### 3. Framework Integration
```python
# Create Flask application
flask_app = web_service.create_flask_app()
if flask_app:
    flask_app.run(host=web_service.host, port=web_service.port, debug=web_service.debug)

# Create FastAPI application
fastapi_app = web_service.create_fastapi_app()
if fastapi_app:
    import uvicorn
    uvicorn.run(fastapi_app, host=web_service.host, port=web_service.port)
```

### 4. Production Features
```python
# Add CORS support
web_service.add_cors_support(
    origins=['https://myapp.com', 'https://api.myapp.com'],
    methods=['GET', 'POST', 'PUT', 'DELETE'],
    headers=['Content-Type', 'Authorization', 'X-API-Key']
)

# Add authentication
def api_key_auth(request_context):
    api_key = request_context['headers'].get('X-API-Key')
    return api_key == 'your-secret-api-key'

web_service.add_authentication(api_key_auth)

# Configure static files
web_service.add_static_files('/static', './static_files')
web_service.add_static_files('/uploads', './user_uploads')
```

## Usage Patterns

### REST API Service
```python
class APIService:
    def __init__(self):
        self.web_service = WebService(host='0.0.0.0', port=8000)
        self._setup_routes()
        self._setup_middleware()
    
    def _setup_routes(self):
        # Health check
        self.web_service.add_route('/health', self._health_check, ['GET'])
        
        # API endpoints
        self.web_service.add_route('/api/users', self._users_handler, ['GET', 'POST'])
        self.web_service.add_route('/api/users/<id>', self._user_handler, ['GET', 'PUT', 'DELETE'])
        
        # Documentation
        self.web_service.add_route('/docs', self._docs_handler, ['GET'])
    
    def _setup_middleware(self):
        # Request logging
        def request_logger(request_context):
            print(f"{request_context['method']} {request_context['path']} - {datetime.now()}")
            return request_context
        
        # Rate limiting
        def rate_limiter(request_context):
            # Implement rate limiting logic
            return request_context
        
        # Authentication
        def auth_check(request_context):
            if request_context['path'].startswith('/api/'):
                token = request_context['headers'].get('Authorization', '').replace('Bearer ', '')
                if not self._validate_token(token):
                    raise Exception("Invalid or missing token")
            return request_context
        
        self.web_service.add_middleware(request_logger)
        self.web_service.add_middleware(rate_limiter)
        self.web_service.add_middleware(auth_check)
    
    def _health_check(self, request_context):
        return {'status': 'healthy', 'timestamp': datetime.now().isoformat()}
    
    def _users_handler(self, request_context):
        if request_context['method'] == 'GET':
            return {'users': self._get_all_users()}
        elif request_context['method'] == 'POST':
            return {'user': self._create_user(request_context['data'])}
    
    def start(self):
        self.web_service.start_server(blocking=False)
        print("API Service started successfully")
```

### Microservice with Database Integration
```python
class DataMicroservice:
    def __init__(self, database_service):
        self.web_service = WebService(port=8001)
        self.database_service = database_service
        self._register_endpoints()
    
    def _register_endpoints(self):
        # Data endpoints
        self.web_service.add_route('/data/query', self._query_data, ['POST'])
        self.web_service.add_route('/data/insert', self._insert_data, ['POST'])
        self.web_service.add_route('/data/update', self._update_data, ['PUT'])
        
        # Metrics endpoint
        self.web_service.add_route('/metrics', self._get_metrics, ['GET'])
    
    def _query_data(self, request_context):
        query = request_context['data'].get('query')
        params = request_context['data'].get('params', {})
        
        try:
            result = self.database_service.execute_config_query(query)
            return {'data': result, 'count': len(result)}
        except Exception as e:
            return {'error': str(e)}, 400
    
    def _insert_data(self, request_context):
        table = request_context['data'].get('table')
        records = request_context['data'].get('records')
        
        try:
            # Use database service to insert records
            success_count = 0
            for record in records:
                # Insert logic here
                success_count += 1
            
            return {'inserted': success_count}
        except Exception as e:
            return {'error': str(e)}, 500
    
    def _get_metrics(self, request_context):
        return {
            'server_status': self.web_service.get_server_status(),
            'database_status': 'connected',  # Check database connectivity
            'uptime': self._get_uptime(),
            'requests_handled': self._get_request_count()
        }
```

### Development and Testing Server
```python
class DevelopmentServer:
    def __init__(self):
        self.web_service = WebService(host='127.0.0.1', port=5000, debug=True)
        self._setup_development_routes()
    
    def _setup_development_routes(self):
        # API testing endpoints
        self.web_service.add_route('/test/echo', self._echo_handler, ['GET', 'POST'])
        self.web_service.add_route('/test/status/<code>', self._status_handler, ['GET'])
        self.web_service.add_route('/test/delay/<seconds>', self._delay_handler, ['GET'])
        
        # Development utilities
        self.web_service.add_route('/dev/routes', self._list_routes, ['GET'])
        self.web_service.add_route('/dev/config', self._show_config, ['GET'])
        self.web_service.add_route('/dev/reload', self._reload_server, ['POST'])
    
    def _echo_handler(self, request_context):
        return {
            'echo': request_context,
            'timestamp': datetime.now().isoformat()
        }
    
    def _status_handler(self, request_context):
        # Extract status code from path
        code = int(request_context['path'].split('/')[-1])
        return {'status_code': code, 'message': f'Test response with code {code}'}
    
    def _delay_handler(self, request_context):
        seconds = float(request_context['path'].split('/')[-1])
        time.sleep(seconds)
        return {'delayed': seconds, 'message': f'Response delayed by {seconds} seconds'}
    
    def _list_routes(self, request_context):
        return {'routes': self.web_service.get_routes_info()}
    
    def _show_config(self, request_context):
        return {'config': self.web_service.config}
    
    def _reload_server(self, request_context):
        self.web_service.restart_server()
        return {'message': 'Server reloaded successfully'}
```

## Request/Response Model

### Request Context Structure
```python
request_context = {
    'path': '/api/endpoint',           # Request path
    'method': 'POST',                  # HTTP method
    'headers': {                       # Request headers
        'Content-Type': 'application/json',
        'Authorization': 'Bearer token'
    },
    'data': {                         # Request body/form data
        'key': 'value'
    }
}
```

### Response Structure
```python
response = {
    'status': 200,                    # HTTP status code
    'body': {                         # Response body
        'message': 'Success',
        'data': {...}
    },
    'headers': {                      # Response headers
        'Content-Type': 'application/json'
    }
}
```

## Middleware System

### Middleware Function Pattern
```python
def middleware_function(request_context):
    """
    Middleware function that processes request context.
    
    Args:
        request_context (dict): Request context dictionary
        
    Returns:
        dict: Modified request context
        
    Raises:
        Exception: If request should be rejected
    """
    # Pre-processing
    print(f"Processing {request_context['method']} {request_context['path']}")
    
    # Modify request context
    request_context['processed_at'] = datetime.now()
    
    # Return modified context
    return request_context
```

### Common Middleware Examples
```python
# Authentication middleware
def jwt_auth_middleware(request_context):
    if request_context['path'].startswith('/protected/'):
        token = request_context['headers'].get('Authorization', '').replace('Bearer ', '')
        if not validate_jwt_token(token):
            raise Exception("Invalid authentication token")
    return request_context

# Request validation middleware
def validation_middleware(request_context):
    if request_context['method'] in ['POST', 'PUT']:
        if not request_context.get('data'):
            raise Exception("Request body required")
    return request_context

# Performance monitoring middleware
def performance_middleware(request_context):
    request_context['start_time'] = time.time()
    return request_context
```

## Framework Integration

### Flask Integration
```python
# Automatic Flask app creation
flask_app = web_service.create_flask_app()

# Manual Flask integration
from flask import Flask
app = Flask(__name__)

@app.route('/manual')
def manual_route():
    return {'message': 'Manual Flask route'}

# Combine with WebService routes
web_service.create_flask_app()  # Registers WebService routes
```

### FastAPI Integration
```python
# Automatic FastAPI app creation
fastapi_app = web_service.create_fastapi_app()

# Manual FastAPI integration
from fastapi import FastAPI
app = FastAPI()

@app.get('/manual')
async def manual_route():
    return {'message': 'Manual FastAPI route'}

# Run with uvicorn
import uvicorn
uvicorn.run(app, host='0.0.0.0', port=8000)
```

## Configuration Management

### Configuration Options
```python
# Server configuration
web_service.set_config('host', '0.0.0.0')
web_service.set_config('port', 8080)
web_service.set_config('debug', False)

# Application configuration
web_service.set_config('app_name', 'My API')
web_service.set_config('version', '2.0.0')
web_service.set_config('database_url', 'postgresql://...')

# Security configuration
web_service.set_config('secret_key', 'your-secret-key')
web_service.set_config('jwt_algorithm', 'HS256')

# Feature flags
web_service.set_config('enable_metrics', True)
web_service.set_config('enable_documentation', True)
```

### Environment Integration
```python
import os

# Load configuration from environment
web_service.set_config('database_url', os.getenv('DATABASE_URL'))
web_service.set_config('api_key', os.getenv('API_KEY'))
web_service.set_config('debug', os.getenv('DEBUG', 'False').lower() == 'true')
```

## Dependencies

### Core Dependencies
```python
from typing import Dict, Any, Optional, Callable, List
import threading
import time
from abc import ABC, abstractmethod
```

### Optional Framework Dependencies
```python
# For Flask integration
from flask import Flask, request, jsonify

# For FastAPI integration
from fastapi import FastAPI, Request
import uvicorn
```

## Testing Strategy

### Unit Testing
```python
def test_route_registration():
    service = WebService()
    
    def test_handler(request_context):
        return {'test': 'data'}
    
    service.add_route('/test', test_handler, ['GET'])
    
    assert '/test' in service.routes
    assert service.routes['/test']['methods'] == ['GET']

def test_middleware_execution():
    service = WebService()
    
    def middleware(request_context):
        request_context['middleware_applied'] = True
        return request_context
    
    service.add_middleware(middleware)
    
    response = service.handle_request('/test', 'GET')
    # Test middleware was applied
```

### Integration Testing
```python
def test_flask_integration():
    service = WebService()
    
    def api_handler(request_context):
        return {'message': 'API response'}
    
    service.add_route('/api', api_handler, ['GET'])
    
    flask_app = service.create_flask_app()
    assert flask_app is not None
    
    # Test with Flask test client
    with flask_app.test_client() as client:
        response = client.get('/api')
        assert response.status_code == 200
```

### Performance Testing
- **Load Testing**: Test server performance under concurrent requests
- **Memory Usage**: Monitor memory consumption during operation
- **Response Time**: Measure request processing latency
- **Resource Cleanup**: Verify proper cleanup of threads and resources

## Best Practices

### Server Management
1. **Use non-blocking mode** for production servers
2. **Implement proper shutdown handlers** for graceful termination
3. **Monitor server health** with regular health checks
4. **Configure appropriate timeouts** for server operations
5. **Use environment-specific configurations**

### Route and Middleware Design
1. **Keep handlers focused** on single responsibilities
2. **Use middleware for cross-cutting concerns** (auth, logging, validation)
3. **Handle errors gracefully** with proper HTTP status codes
4. **Validate input data** in middleware or handlers
5. **Document API endpoints** for maintainability

### Production Deployment
1. **Use production WSGI servers** (Gunicorn, uWSGI) for Flask
2. **Use ASGI servers** (Uvicorn, Hypercorn) for FastAPI
3. **Implement proper logging** for monitoring and debugging
4. **Configure security headers** and CORS policies
5. **Monitor performance metrics** and resource usage

### Security Considerations
1. **Validate all input data** to prevent injection attacks
2. **Implement proper authentication** and authorization
3. **Use HTTPS** in production environments
4. **Configure CORS** policies restrictively
5. **Monitor for security vulnerabilities** in dependencies