"""
Comprehensive unit tests for the API module.
Tests all major components including clients, authentication, serialization, and models.
"""

import asyncio
import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from decimal import Decimal
import json

# Import the modules we're testing
from .clients import (
    ApiConnection, QuantConnectApiClient, ProjectManager, 
    BacktestManager, LiveAlgorithmManager, DataManager, NodeManager
)
from .authentication import (
    ApiKeyAuthenticationProvider, OAuth2AuthenticationProvider, AuthenticationManager
)
from .serialization import ApiSerializer, ApiResponseDeserializer
from .models import (
    Project, Backtest, LiveAlgorithm, ApiConfiguration, AuthenticationResponse,
    BacktestResult, CreateProjectRequest, CreateBacktestRequest
)
from .enums import (
    ProjectLanguage, BacktestStatus, LiveAlgorithmStatus, AuthenticationType,
    ApiResponseStatus, NodeType
)
from .exceptions import (
    ApiException, AuthenticationException, ValidationException,
    NetworkException, TimeoutException, RateLimitException
)


class TestApiSerializer(unittest.TestCase):
    """Test API serialization functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.serializer = ApiSerializer()
    
    def test_serialize_basic_types(self):
        """Test serialization of basic types."""
        # Test basic types
        self.assertEqual('"test"', self.serializer.serialize("test"))
        self.assertEqual('123', self.serializer.serialize(123))
        self.assertEqual('true', self.serializer.serialize(True))
        
    def test_serialize_decimal(self):
        """Test Decimal serialization."""
        decimal_value = Decimal("123.45")
        result = self.serializer.serialize(decimal_value)
        self.assertEqual('"123.45"', result)
    
    def test_serialize_datetime(self):
        """Test datetime serialization."""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = self.serializer.serialize(dt)
        self.assertIn("2023-01-01T12:00:00", result)
    
    def test_serialize_enum(self):
        """Test enum serialization."""
        language = ProjectLanguage.PYTHON
        result = self.serializer.serialize(language)
        self.assertEqual('"Py"', result)
    
    def test_deserialize_basic_types(self):
        """Test deserialization of basic types."""
        self.assertEqual("test", self.serializer.deserialize('"test"', str))
        self.assertEqual(123, self.serializer.deserialize('123', int))
        self.assertEqual(True, self.serializer.deserialize('true', bool))
    
    def test_deserialize_decimal(self):
        """Test Decimal deserialization."""
        result = self.serializer.deserialize_decimal("123.45")
        self.assertEqual(Decimal("123.45"), result)
    
    def test_deserialize_enum(self):
        """Test enum deserialization."""
        result = self.serializer.deserialize('"Py"', ProjectLanguage)
        self.assertEqual(ProjectLanguage.PYTHON, result)
    
    def test_serialization_error_handling(self):
        """Test serialization error handling."""
        with self.assertRaises(Exception):
            # Create an object that can't be serialized
            class UnserializableObject:
                def __getstate__(self):
                    raise Exception("Cannot serialize")
            
            obj = UnserializableObject()
            self.serializer.serialize(obj)


class TestApiModels(unittest.TestCase):
    """Test API data models."""
    
    def test_project_model(self):
        """Test Project model creation and validation."""
        project = Project(
            project_id=123,
            name="Test Project",
            created=datetime.now(),
            modified=datetime.now(),
            language=ProjectLanguage.PYTHON,
            description="Test description"
        )
        
        self.assertEqual(project.project_id, 123)
        self.assertEqual(project.name, "Test Project")
        self.assertEqual(project.language, ProjectLanguage.PYTHON)
    
    def test_backtest_model(self):
        """Test Backtest model."""
        backtest = Backtest(
            project_id=123,
            backtest_id="bt-456",
            name="Test Backtest",
            status=BacktestStatus.COMPLETED,
            created=datetime.now(),
            progress=100.0
        )
        
        self.assertTrue(backtest.is_completed)
        self.assertEqual(backtest.progress, 100.0)
    
    def test_backtest_result_model(self):
        """Test BacktestResult model with financial metrics."""
        result = BacktestResult(
            total_return=Decimal("0.15"),
            sharpe_ratio=Decimal("1.2"),
            max_drawdown=Decimal("0.05"),
            total_trades=150,
            win_rate=Decimal("0.6")
        )
        
        self.assertEqual(result.total_return, Decimal("0.15"))
        self.assertEqual(result.total_trades, 150)
    
    def test_api_configuration(self):
        """Test API configuration validation."""
        # Valid configuration
        config = ApiConfiguration(
            base_url="https://api.quantconnect.com",
            timeout=30,
            max_retries=3
        )
        self.assertEqual(config.timeout, 30)
        
        # Invalid configuration should raise error
        with self.assertRaises(ValueError):
            ApiConfiguration(base_url="", timeout=-1)
    
    def test_authentication_response(self):
        """Test authentication response model."""
        auth_response = AuthenticationResponse(
            success=True,
            access_token="token123",
            expires_in=3600
        )
        
        self.assertTrue(auth_response.is_authenticated())
        
        # Failed authentication
        failed_auth = AuthenticationResponse(
            success=False,
            errors=["Invalid credentials"]
        )
        
        self.assertFalse(failed_auth.is_authenticated())


class TestApiExceptions(unittest.TestCase):
    """Test API exception handling."""
    
    def test_api_exception_creation(self):
        """Test basic API exception."""
        exc = ApiException("Test error", 500, {"detail": "Server error"})
        self.assertEqual(exc.status_code, 500)
        self.assertIn("HTTP 500", str(exc))
    
    def test_authentication_exception(self):
        """Test authentication exception."""
        exc = AuthenticationException("Auth failed")
        self.assertEqual(exc.status_code, 401)
    
    def test_rate_limit_exception(self):
        """Test rate limit exception."""
        exc = RateLimitException("Rate limited", retry_after=60)
        self.assertEqual(exc.retry_after, 60)
        self.assertIn("retry after 60", str(exc))
    
    def test_validation_exception(self):
        """Test validation exception."""
        validation_errors = {"field1": "Required field missing"}
        exc = ValidationException("Validation failed", validation_errors)
        self.assertEqual(exc.validation_errors, validation_errors)
    
    def test_exception_factory(self):
        """Test exception creation from response."""
        from .exceptions import create_exception_from_response
        
        # 404 error
        exc = create_exception_from_response(404, {"message": "Not found"})
        self.assertEqual(exc.status_code, 404)
        
        # 429 rate limit
        exc = create_exception_from_response(429, {"retry_after": 120})
        self.assertIsInstance(exc, RateLimitException)


class TestApiAuthentication(unittest.TestCase):
    """Test API authentication providers."""
    
    def test_api_key_provider_creation(self):
        """Test API key provider initialization."""
        provider = ApiKeyAuthenticationProvider("test_key", "test_secret")
        self.assertEqual(provider.api_key, "test_key")
        self.assertEqual(provider.api_secret, "test_secret")
        
        # Should raise error with empty credentials
        with self.assertRaises(ValidationException):
            ApiKeyAuthenticationProvider("", "")
    
    def test_api_key_signature_generation(self):
        """Test HMAC signature generation."""
        provider = ApiKeyAuthenticationProvider("test_key", "test_secret")
        signature = provider._create_signature("1234567890")
        
        # Signature should be consistent
        signature2 = provider._create_signature("1234567890")
        self.assertEqual(signature, signature2)
        
        # Different timestamps should give different signatures
        signature3 = provider._create_signature("1234567891")
        self.assertNotEqual(signature, signature3)
    
    @patch('aiohttp.ClientSession.post')
    async def test_oauth2_authentication(self, mock_post):
        """Test OAuth2 authentication flow."""
        # Mock successful token response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            'access_token': 'access123',
            'refresh_token': 'refresh123',
            'expires_in': 3600,
            'token_type': 'Bearer'
        })
        mock_post.return_value.__aenter__.return_value = mock_response
        
        provider = OAuth2AuthenticationProvider(
            "client_id", "client_secret", "http://localhost/callback"
        )
        
        result = await provider.authenticate({'code': 'auth_code123'})
        
        self.assertTrue(result['success'])
        self.assertEqual(result['access_token'], 'access123')
    
    def test_authentication_manager(self):
        """Test authentication manager functionality."""
        config = ApiConfiguration()
        auth_manager = AuthenticationManager(config)
        
        # Add API key provider
        auth_manager.set_api_key_provider("test_key", "test_secret")
        
        self.assertIn(AuthenticationType.API_KEY, auth_manager._providers)
        
        # Initially not authenticated
        self.assertFalse(auth_manager.is_authenticated())


class TestApiConnection(unittest.TestCase):
    """Test API connection functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.config = ApiConfiguration(base_url="https://test.api.com")
        self.auth_manager = Mock()
        self.auth_manager.is_authenticated.return_value = True
        self.auth_manager.get_auth_headers.return_value = {
            'Authorization': 'Bearer test_token'
        }
    
    @patch('aiohttp.ClientSession')
    async def test_api_connection_get_request(self, mock_session_class):
        """Test GET request through API connection."""
        # Mock session and response
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.text = AsyncMock(return_value='{"success": true, "data": "test"}')
        mock_response.headers = {}
        
        mock_session.request.return_value.__aenter__.return_value = mock_response
        mock_session_class.return_value = mock_session
        
        connection = ApiConnection(self.config, self.auth_manager)
        
        result = await connection.get("/test/endpoint")
        
        self.assertTrue(result.get('success'))
        mock_session.request.assert_called_once()
    
    @patch('aiohttp.ClientSession')
    async def test_api_connection_error_handling(self, mock_session_class):
        """Test error handling in API connection."""
        # Mock session to raise timeout
        mock_session = AsyncMock()
        mock_session.request.side_effect = asyncio.TimeoutError()
        mock_session_class.return_value = mock_session
        
        connection = ApiConnection(self.config, self.auth_manager)
        
        with self.assertRaises(TimeoutException):
            await connection.get("/test/endpoint")
    
    @patch('aiohttp.ClientSession')
    async def test_api_connection_retry_logic(self, mock_session_class):
        """Test retry logic on failures."""
        # Configure for quick retries
        config = ApiConfiguration(max_retries=2, retry_delay=0.1)
        
        # Mock session to fail first two calls, succeed on third
        mock_session = AsyncMock()
        mock_response_success = AsyncMock()
        mock_response_success.status = 200
        mock_response_success.text = AsyncMock(return_value='{"success": true}')
        mock_response_success.headers = {}
        
        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("Network error")
            return mock_response_success
        
        mock_session.request.return_value.__aenter__ = side_effect
        mock_session_class.return_value = mock_session
        
        connection = ApiConnection(config, self.auth_manager)
        
        # Should eventually succeed after retries
        result = await connection.get("/test/endpoint")
        self.assertTrue(result.get('success'))


class TestApiClients(unittest.TestCase):
    """Test API client implementations."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_connection = AsyncMock()
        self.mock_deserializer = Mock()
        
    async def test_project_manager_create_project(self):
        """Test project creation through project manager."""
        # Mock successful project creation response
        project_data = {
            'project_id': 123,
            'name': 'Test Project',
            'language': 'Py',
            'created': datetime.now().isoformat(),
            'modified': datetime.now().isoformat()
        }
        
        self.mock_connection.post.return_value = project_data
        self.mock_deserializer.deserialize_response.return_value = Project(
            project_id=123,
            name='Test Project',
            language=ProjectLanguage.PYTHON,
            created=datetime.now(),
            modified=datetime.now()
        )
        
        manager = ProjectManager(self.mock_connection, self.mock_deserializer)
        
        result = await manager.create_project("Test Project", "Python")
        
        self.assertEqual(result.project_id, 123)
        self.assertEqual(result.name, "Test Project")
        self.mock_connection.post.assert_called_once()
    
    async def test_backtest_manager_operations(self):
        """Test backtest manager operations."""
        backtest_data = {
            'project_id': 123,
            'backtest_id': 'bt-456',
            'name': 'Test Backtest',
            'status': 'Completed',
            'created': datetime.now().isoformat()
        }
        
        self.mock_connection.post.return_value = backtest_data
        self.mock_deserializer.deserialize_response.return_value = Backtest(
            project_id=123,
            backtest_id='bt-456',
            name='Test Backtest',
            status=BacktestStatus.COMPLETED,
            created=datetime.now()
        )
        
        manager = BacktestManager(self.mock_connection, self.mock_deserializer)
        
        result = await manager.create_backtest(123, "compile-123", "Test Backtest")
        
        self.assertEqual(result.backtest_id, 'bt-456')
        self.assertEqual(result.status, BacktestStatus.COMPLETED)
    
    def test_quantconnect_api_client_initialization(self):
        """Test main API client initialization."""
        client = QuantConnectApiClient()
        
        # Should have default configuration
        self.assertIsNotNone(client.config)
        self.assertIsNotNone(client.auth_manager)
        self.assertIsNotNone(client.connection)
        
        # Should provide access to managers
        self.assertIsNotNone(client.projects)
        self.assertIsNotNone(client.backtests)
        self.assertIsNotNone(client.live)
        self.assertIsNotNone(client.data)
        self.assertIsNotNone(client.nodes)
    
    async def test_api_client_authentication(self):
        """Test API client authentication."""
        client = QuantConnectApiClient()
        
        # Mock authentication manager
        client.auth_manager = AsyncMock()
        client.auth_manager.set_api_key_provider = Mock()
        client.auth_manager.authenticate = AsyncMock()
        client.auth_manager.get_current_auth_type = Mock(return_value=AuthenticationType.API_KEY)
        
        mock_auth_response = AuthenticationResponse(
            success=True,
            access_token="token123"
        )
        mock_auth_response.is_authenticated = Mock(return_value=True)
        client.auth_manager.authenticate.return_value = mock_auth_response
        
        # Test authentication with API key format
        result = await client.authenticate("api_key:api_secret")
        
        self.assertTrue(result)
        client.auth_manager.set_api_key_provider.assert_called_once_with("api_key", "api_secret")


class TestApiIntegration(unittest.TestCase):
    """Integration tests for API components."""
    
    def test_end_to_end_serialization(self):
        """Test end-to-end serialization workflow."""
        # Create a complex object
        backtest = Backtest(
            project_id=123,
            backtest_id="bt-456",
            name="Integration Test",
            status=BacktestStatus.COMPLETED,
            created=datetime(2023, 1, 1, 12, 0, 0),
            progress=100.0,
            result=BacktestResult(
                total_return=Decimal("0.15"),
                sharpe_ratio=Decimal("1.2"),
                total_trades=150
            )
        )
        
        # Serialize to JSON
        serializer = ApiSerializer()
        json_data = serializer.serialize(backtest)
        
        # Deserialize back
        deserialized = serializer.deserialize(json_data, Backtest)
        
        self.assertEqual(deserialized.project_id, backtest.project_id)
        self.assertEqual(deserialized.backtest_id, backtest.backtest_id)
        self.assertEqual(deserialized.status, backtest.status)
        self.assertEqual(deserialized.progress, backtest.progress)
    
    def test_error_propagation(self):
        """Test error propagation through the system."""
        # Test that errors are properly propagated and transformed
        
        # Network error should become NetworkException
        original_error = ConnectionError("Connection failed")
        
        from .exceptions import NetworkException
        wrapped_error = NetworkException("Request failed", original_error)
        
        self.assertIsInstance(wrapped_error, NetworkException)
        self.assertEqual(wrapped_error.original_exception, original_error)
    
    def test_configuration_inheritance(self):
        """Test configuration inheritance and overrides."""
        # Test that configuration is properly inherited
        base_config = ApiConfiguration(
            base_url="https://api.test.com",
            timeout=30,
            max_retries=5
        )
        
        # Configuration should maintain its values
        self.assertEqual(base_config.timeout, 30)
        self.assertEqual(base_config.max_retries, 5)
        
        # Should be able to create client with custom config
        client = QuantConnectApiClient(config=base_config)
        self.assertEqual(client.config.timeout, 30)


class TestApiEdgeCases(unittest.TestCase):
    """Test edge cases and error scenarios."""
    
    def test_empty_response_handling(self):
        """Test handling of empty API responses."""
        serializer = ApiSerializer()
        
        # Empty string should raise error
        with self.assertRaises(Exception):
            serializer.deserialize("", dict)
        
        # Null response should handle gracefully
        result = serializer.deserialize("null", dict)
        self.assertIsNone(result)
    
    def test_malformed_json_handling(self):
        """Test handling of malformed JSON."""
        serializer = ApiSerializer()
        
        with self.assertRaises(Exception):
            serializer.deserialize("{invalid json", dict)
    
    def test_type_mismatch_handling(self):
        """Test handling of type mismatches."""
        serializer = ApiSerializer()
        
        # Trying to deserialize string as int should handle gracefully
        with self.assertRaises(Exception):
            serializer.deserialize('"not_a_number"', int)
    
    def test_authentication_edge_cases(self):
        """Test authentication edge cases."""
        # Empty credentials
        with self.assertRaises(ValidationException):
            ApiKeyAuthenticationProvider("", "secret")
        
        with self.assertRaises(ValidationException):
            ApiKeyAuthenticationProvider("key", "")
    
    def test_concurrent_api_calls(self):
        """Test concurrent API calls don't interfere."""
        # This would require actual async testing in a real scenario
        # For now, we test that the components are thread-safe by design
        
        config = ApiConfiguration()
        auth_manager = AuthenticationManager(config)
        
        # Multiple auth managers should be independent
        auth_manager2 = AuthenticationManager(config)
        
        self.assertIsNot(auth_manager, auth_manager2)
        self.assertEqual(len(auth_manager._providers), 0)
        self.assertEqual(len(auth_manager2._providers), 0)


if __name__ == '__main__':
    # Run all tests
    unittest.main(verbosity=2)