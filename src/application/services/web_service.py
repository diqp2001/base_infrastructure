# src/application/services/web_service.py
from typing import Dict, Any, Optional, Callable, List
import threading
import time
from abc import ABC, abstractmethod


class WebService:
    """
    Service class for common web server operations and management.
    Provides basic methods for managing and configuring web services.
    """

    def __init__(self, host: str = '127.0.0.1', port: int = 5000, debug: bool = False):
        """
        Initialize the WebService with server configuration.
        :param host: The host address to bind the server to.
        :param port: The port to bind the server to.
        :param debug: Enable debug mode.
        """
        self.host = host
        self.port = port
        self.debug = debug
        self.server_thread = None
        self.is_running = False
        self.routes = {}
        self.middleware = []
        self.config = {}
        
        print(f"Initialized WebService with host {self.host} and port {self.port}")

    def add_route(self, path: str, handler: Callable, methods: List[str] = None):
        """
        Add a route handler.
        :param path: URL path.
        :param handler: Handler function.
        :param methods: HTTP methods (default: ['GET']).
        """
        if methods is None:
            methods = ['GET']
        
        self.routes[path] = {
            'handler': handler,
            'methods': methods
        }
        print(f"Added route: {path} with methods {methods}")

    def add_middleware(self, middleware_func: Callable):
        """
        Add middleware function.
        :param middleware_func: Middleware function.
        """
        self.middleware.append(middleware_func)
        print(f"Added middleware: {middleware_func.__name__}")

    def set_config(self, key: str, value: Any):
        """
        Set configuration value.
        :param key: Configuration key.
        :param value: Configuration value.
        """
        self.config[key] = value
        print(f"Set config {key} = {value}")

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        :param key: Configuration key.
        :param default: Default value if key not found.
        :return: Configuration value.
        """
        return self.config.get(key, default)

    def start_server(self, blocking: bool = True):
        """
        Start the web server.
        :param blocking: Whether to block the current thread.
        """
        if self.is_running:
            print("Server is already running")
            return

        try:
            if blocking:
                self._run_server()
            else:
                self.server_thread = threading.Thread(target=self._run_server)
                self.server_thread.daemon = True
                self.server_thread.start()
                
            print(f"Server started on {self.host}:{self.port}")
            
        except Exception as e:
            print(f"Error starting server: {e}")

    def stop_server(self):
        """
        Stop the web server.
        """
        if not self.is_running:
            print("Server is not running")
            return

        try:
            self.is_running = False
            
            if self.server_thread and self.server_thread.is_alive():
                self.server_thread.join(timeout=5.0)
                
            print("Server stopped successfully")
            
        except Exception as e:
            print(f"Error stopping server: {e}")

    def restart_server(self):
        """
        Restart the web server.
        """
        print("Restarting server...")
        self.stop_server()
        time.sleep(1)
        self.start_server(blocking=False)

    def is_server_running(self) -> bool:
        """
        Check if server is running.
        :return: True if running, False otherwise.
        """
        return self.is_running

    def get_server_status(self) -> Dict[str, Any]:
        """
        Get server status information.
        :return: Dictionary with server status.
        """
        return {
            'is_running': self.is_running,
            'host': self.host,
            'port': self.port,
            'debug': self.debug,
            'routes_count': len(self.routes),
            'middleware_count': len(self.middleware),
            'config': self.config.copy()
        }

    def handle_request(self, path: str, method: str, headers: Dict[str, str] = None, 
                      data: Any = None) -> Dict[str, Any]:
        """
        Handle a request (for testing or internal use).
        :param path: Request path.
        :param method: HTTP method.
        :param headers: Request headers.
        :param data: Request data.
        :return: Response dictionary.
        """
        try:
            # Apply middleware
            request_context = {
                'path': path,
                'method': method,
                'headers': headers or {},
                'data': data
            }
            
            for middleware_func in self.middleware:
                try:
                    request_context = middleware_func(request_context)
                except Exception as e:
                    print(f"Middleware error: {e}")
            
            # Find route handler
            if path in self.routes:
                route_info = self.routes[path]
                
                if method in route_info['methods']:
                    try:
                        response = route_info['handler'](request_context)
                        return {
                            'status': 200,
                            'body': response,
                            'headers': {'Content-Type': 'application/json'}
                        }
                    except Exception as e:
                        return {
                            'status': 500,
                            'body': {'error': f'Handler error: {str(e)}'},
                            'headers': {'Content-Type': 'application/json'}
                        }
                else:
                    return {
                        'status': 405,
                        'body': {'error': f'Method {method} not allowed for {path}'},
                        'headers': {'Content-Type': 'application/json'}
                    }
            else:
                return {
                    'status': 404,
                    'body': {'error': f'Route {path} not found'},
                    'headers': {'Content-Type': 'application/json'}
                }
                
        except Exception as e:
            return {
                'status': 500,
                'body': {'error': f'Request handling error: {str(e)}'},
                'headers': {'Content-Type': 'application/json'}
            }

    def _run_server(self):
        """
        Internal method to run the server.
        This is a basic implementation - in a real scenario, you'd integrate with Flask, FastAPI, etc.
        """
        self.is_running = True
        
        print(f"Mock server running on {self.host}:{self.port}")
        print("Note: This is a basic implementation. For production, integrate with Flask/FastAPI.")
        
        try:
            while self.is_running:
                time.sleep(0.1)  # Basic event loop
                
        except KeyboardInterrupt:
            print("Server interrupted by user")
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.is_running = False

    def create_flask_app(self):
        """
        Create a Flask application with registered routes.
        Requires Flask to be installed.
        :return: Flask app instance.
        """
        try:
            from flask import Flask, request, jsonify
            
            app = Flask(__name__)
            app.config.update(self.config)
            
            # Register routes
            for path, route_info in self.routes.items():
                def create_handler(handler_func):
                    def wrapper():
                        request_context = {
                            'path': request.path,
                            'method': request.method,
                            'headers': dict(request.headers),
                            'data': request.get_json() if request.is_json else request.form.to_dict()
                        }
                        
                        # Apply middleware
                        for middleware_func in self.middleware:
                            try:
                                request_context = middleware_func(request_context)
                            except Exception as e:
                                return jsonify({'error': f'Middleware error: {str(e)}'}), 500
                        
                        try:
                            result = handler_func(request_context)
                            return jsonify(result)
                        except Exception as e:
                            return jsonify({'error': f'Handler error: {str(e)}'}), 500
                    
                    return wrapper
                
                handler = create_handler(route_info['handler'])
                app.add_url_rule(path, endpoint=path.replace('/', '_'), 
                               view_func=handler, methods=route_info['methods'])
            
            return app
            
        except ImportError:
            print("Flask not installed. Cannot create Flask app.")
            return None

    def create_fastapi_app(self):
        """
        Create a FastAPI application with registered routes.
        Requires FastAPI to be installed.
        :return: FastAPI app instance.
        """
        try:
            from fastapi import FastAPI, Request
            
            app = FastAPI()
            
            # Register routes
            for path, route_info in self.routes.items():
                def create_handler(handler_func):
                    async def wrapper(request: Request):
                        body = None
                        try:
                            body = await request.json()
                        except:
                            try:
                                body = dict(await request.form())
                            except:
                                body = {}
                        
                        request_context = {
                            'path': str(request.url.path),
                            'method': request.method,
                            'headers': dict(request.headers),
                            'data': body
                        }
                        
                        # Apply middleware
                        for middleware_func in self.middleware:
                            try:
                                request_context = middleware_func(request_context)
                            except Exception as e:
                                return {'error': f'Middleware error: {str(e)}'}
                        
                        try:
                            return handler_func(request_context)
                        except Exception as e:
                            return {'error': f'Handler error: {str(e)}'}
                    
                    return wrapper
                
                handler = create_handler(route_info['handler'])
                
                for method in route_info['methods']:
                    if method.upper() == 'GET':
                        app.get(path)(handler)
                    elif method.upper() == 'POST':
                        app.post(path)(handler)
                    elif method.upper() == 'PUT':
                        app.put(path)(handler)
                    elif method.upper() == 'DELETE':
                        app.delete(path)(handler)
            
            return app
            
        except ImportError:
            print("FastAPI not installed. Cannot create FastAPI app.")
            return None

    def add_static_files(self, path: str, directory: str):
        """
        Add static file serving (implementation depends on web framework).
        :param path: URL path prefix.
        :param directory: Local directory to serve files from.
        """
        self.config[f'static_{path}'] = directory
        print(f"Added static files: {path} -> {directory}")

    def add_cors_support(self, origins: List[str] = None, methods: List[str] = None, 
                        headers: List[str] = None):
        """
        Add CORS support configuration.
        :param origins: Allowed origins.
        :param methods: Allowed methods.
        :param headers: Allowed headers.
        """
        cors_config = {
            'origins': origins or ['*'],
            'methods': methods or ['GET', 'POST', 'PUT', 'DELETE'],
            'headers': headers or ['Content-Type', 'Authorization']
        }
        
        self.config['cors'] = cors_config
        print(f"Added CORS support: {cors_config}")

    def add_authentication(self, auth_func: Callable):
        """
        Add authentication middleware.
        :param auth_func: Authentication function.
        """
        def auth_middleware(request_context):
            if not auth_func(request_context):
                raise Exception("Authentication failed")
            return request_context
        
        self.add_middleware(auth_middleware)
        print("Added authentication middleware")

    def get_routes_info(self) -> List[Dict[str, Any]]:
        """
        Get information about registered routes.
        :return: List of route information dictionaries.
        """
        routes_info = []
        for path, route_info in self.routes.items():
            routes_info.append({
                'path': path,
                'methods': route_info['methods'],
                'handler_name': route_info['handler'].__name__
            })
        return routes_info

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check.
        :return: Health check results.
        """
        return {
            'status': 'healthy' if self.is_running else 'stopped',
            'host': self.host,
            'port': self.port,
            'uptime': 'N/A',  # Could track actual uptime
            'routes': len(self.routes),
            'middleware': len(self.middleware)
        }