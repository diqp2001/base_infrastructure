"""
Authentication and authorization management for QuantConnect API.
Handles token management, OAuth2 flows, and API key authentication.
"""

import asyncio
import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Optional, Any, Tuple
from urllib.parse import urlencode
import aiohttp

from .interfaces import IAuthenticationProvider
from .models import AuthenticationResponse, ApiConfiguration
from .exceptions import AuthenticationException, ValidationException
from .enums import AuthenticationType


class ApiKeyAuthenticationProvider(IAuthenticationProvider):
    """
    Authentication provider using API key and secret.
    Implements HMAC-SHA256 signature authentication for QuantConnect API.
    """
    
    def __init__(self, api_key: str, api_secret: str):
        """Initialize with API credentials."""
        if not api_key or not api_secret:
            raise ValidationException("API key and secret are required")
        
        self.api_key = api_key
        self.api_secret = api_secret
        self._user_id: Optional[str] = None
        self._authenticated = False
        self._last_auth_time: Optional[datetime] = None
    
    async def authenticate(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """
        Authenticate using API key and secret.
        Returns authentication response with user details.
        """
        try:
            # Create authentication signature
            timestamp = str(int(time.time()))
            signature = self._create_signature(timestamp)
            
            auth_data = {
                'api_key': self.api_key,
                'timestamp': timestamp,
                'signature': signature
            }
            
            # In a real implementation, this would make an HTTP request
            # For now, we'll simulate a successful authentication
            self._authenticated = True
            self._last_auth_time = datetime.utcnow()
            self._user_id = credentials.get('user_id', 'authenticated_user')
            
            return {
                'success': True,
                'user_id': self._user_id,
                'access_token': self._generate_access_token(),
                'expires_in': 3600,
                'token_type': 'Bearer'
            }
            
        except Exception as e:
            raise AuthenticationException(f"Authentication failed: {str(e)}")
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """
        Refresh an expired access token.
        API key authentication doesn't use refresh tokens.
        """
        return await self.authenticate({})
    
    def is_token_valid(self, token: str) -> bool:
        """Check if the provided token is valid."""
        if not self._authenticated or not self._last_auth_time:
            return False
        
        # Check if token has expired (1 hour validity)
        expiry_time = self._last_auth_time + timedelta(hours=1)
        return datetime.utcnow() < expiry_time
    
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """Get the expiry time of the provided token."""
        if not self._last_auth_time:
            return None
        return self._last_auth_time + timedelta(hours=1)
    
    def _create_signature(self, timestamp: str) -> str:
        """Create HMAC-SHA256 signature for API authentication."""
        message = f"{self.api_key}{timestamp}"
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _generate_access_token(self) -> str:
        """Generate a temporary access token."""
        token_data = {
            'api_key': self.api_key,
            'user_id': self._user_id,
            'timestamp': int(time.time())
        }
        token_json = json.dumps(token_data)
        return base64.b64encode(token_json.encode('utf-8')).decode('utf-8')
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        if not self._authenticated:
            raise AuthenticationException("Not authenticated")
        
        timestamp = str(int(time.time()))
        signature = self._create_signature(timestamp)
        
        return {
            'Authorization': f'Bearer {self._generate_access_token()}',
            'X-API-Key': self.api_key,
            'X-Timestamp': timestamp,
            'X-Signature': signature
        }


class OAuth2AuthenticationProvider(IAuthenticationProvider):
    """
    OAuth2 authentication provider for QuantConnect API.
    Handles OAuth2 authorization code flow.
    """
    
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str,
                 authorization_url: str = "https://www.quantconnect.com/oauth/authorize",
                 token_url: str = "https://www.quantconnect.com/oauth/token"):
        """Initialize OAuth2 provider."""
        if not all([client_id, client_secret, redirect_uri]):
            raise ValidationException("Client ID, secret, and redirect URI are required")
        
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.authorization_url = authorization_url
        self.token_url = token_url
        
        self._access_token: Optional[str] = None
        self._refresh_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None
        self._authenticated = False
    
    def get_authorization_url(self, state: Optional[str] = None, 
                            scopes: Optional[list] = None) -> str:
        """
        Generate OAuth2 authorization URL.
        User needs to visit this URL to authorize the application.
        """
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
        }
        
        if state:
            params['state'] = state
        
        if scopes:
            params['scope'] = ' '.join(scopes)
        
        return f"{self.authorization_url}?{urlencode(params)}"
    
    async def authenticate(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        Requires 'code' in credentials from OAuth2 callback.
        """
        authorization_code = credentials.get('code')
        if not authorization_code:
            raise ValidationException("Authorization code is required")
        
        token_data = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'redirect_uri': self.redirect_uri,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.token_url, data=token_data) as response:
                    if response.status != 200:
                        error_data = await response.json()
                        raise AuthenticationException(
                            f"OAuth2 authentication failed: {error_data.get('error_description', 'Unknown error')}"
                        )
                    
                    token_response = await response.json()
                    
                    self._access_token = token_response.get('access_token')
                    self._refresh_token = token_response.get('refresh_token')
                    expires_in = token_response.get('expires_in', 3600)
                    
                    self._token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
                    self._authenticated = True
                    
                    return {
                        'success': True,
                        'access_token': self._access_token,
                        'refresh_token': self._refresh_token,
                        'expires_in': expires_in,
                        'token_type': token_response.get('token_type', 'Bearer')
                    }
                    
        except aiohttp.ClientError as e:
            raise AuthenticationException(f"Network error during authentication: {str(e)}")
        except Exception as e:
            raise AuthenticationException(f"OAuth2 authentication failed: {str(e)}")
    
    async def refresh_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh an expired access token using refresh token."""
        if not refresh_token:
            refresh_token = self._refresh_token
        
        if not refresh_token:
            raise AuthenticationException("No refresh token available")
        
        token_data = {
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.token_url, data=token_data) as response:
                    if response.status != 200:
                        error_data = await response.json()
                        raise AuthenticationException(
                            f"Token refresh failed: {error_data.get('error_description', 'Unknown error')}"
                        )
                    
                    token_response = await response.json()
                    
                    self._access_token = token_response.get('access_token')
                    if 'refresh_token' in token_response:
                        self._refresh_token = token_response['refresh_token']
                    
                    expires_in = token_response.get('expires_in', 3600)
                    self._token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
                    
                    return {
                        'success': True,
                        'access_token': self._access_token,
                        'refresh_token': self._refresh_token,
                        'expires_in': expires_in,
                        'token_type': token_response.get('token_type', 'Bearer')
                    }
                    
        except aiohttp.ClientError as e:
            raise AuthenticationException(f"Network error during token refresh: {str(e)}")
        except Exception as e:
            raise AuthenticationException(f"Token refresh failed: {str(e)}")
    
    def is_token_valid(self, token: str) -> bool:
        """Check if the provided token is valid."""
        if not self._authenticated or not self._token_expiry:
            return False
        
        # Add 5-minute buffer before expiry
        buffer_time = self._token_expiry - timedelta(minutes=5)
        return datetime.utcnow() < buffer_time
    
    def get_token_expiry(self, token: str) -> Optional[datetime]:
        """Get the expiry time of the provided token."""
        return self._token_expiry
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for API requests."""
        if not self._authenticated or not self._access_token:
            raise AuthenticationException("Not authenticated")
        
        return {
            'Authorization': f'Bearer {self._access_token}',
            'Content-Type': 'application/json'
        }


class AuthenticationManager:
    """
    Manages authentication providers and handles automatic token refresh.
    """
    
    def __init__(self, config: ApiConfiguration):
        """Initialize authentication manager."""
        self.config = config
        self._providers: Dict[AuthenticationType, IAuthenticationProvider] = {}
        self._current_provider: Optional[IAuthenticationProvider] = None
        self._current_auth_type: Optional[AuthenticationType] = None
        self._auto_refresh_enabled = True
        self._refresh_lock = asyncio.Lock()
    
    def add_provider(self, auth_type: AuthenticationType, 
                    provider: IAuthenticationProvider) -> None:
        """Add an authentication provider."""
        self._providers[auth_type] = provider
    
    def set_api_key_provider(self, api_key: str, api_secret: str) -> None:
        """Configure API key authentication."""
        provider = ApiKeyAuthenticationProvider(api_key, api_secret)
        self.add_provider(AuthenticationType.API_KEY, provider)
    
    def set_oauth2_provider(self, client_id: str, client_secret: str, 
                           redirect_uri: str) -> None:
        """Configure OAuth2 authentication."""
        provider = OAuth2AuthenticationProvider(client_id, client_secret, redirect_uri)
        self.add_provider(AuthenticationType.OAUTH2, provider)
    
    async def authenticate(self, auth_type: AuthenticationType, 
                         credentials: Dict[str, str]) -> AuthenticationResponse:
        """Authenticate using specified provider."""
        provider = self._providers.get(auth_type)
        if not provider:
            raise AuthenticationException(f"No provider configured for {auth_type.value}")
        
        try:
            result = await provider.authenticate(credentials)
            
            self._current_provider = provider
            self._current_auth_type = auth_type
            
            return AuthenticationResponse(
                success=result.get('success', False),
                user_id=result.get('user_id'),
                access_token=result.get('access_token'),
                refresh_token=result.get('refresh_token'),
                expires_in=result.get('expires_in'),
                token_type=result.get('token_type', 'Bearer')
            )
            
        except Exception as e:
            return AuthenticationResponse(
                success=False,
                errors=[str(e)]
            )
    
    async def get_valid_token(self) -> str:
        """
        Get a valid access token, refreshing if necessary.
        """
        if not self._current_provider:
            raise AuthenticationException("No authenticated session")
        
        # Check if we have a cached valid token
        if hasattr(self._current_provider, '_access_token'):
            token = getattr(self._current_provider, '_access_token')
            if token and self._current_provider.is_token_valid(token):
                return token
        
        # Try to refresh token if auto-refresh is enabled
        if self._auto_refresh_enabled:
            async with self._refresh_lock:
                return await self._refresh_token_if_needed()
        
        raise AuthenticationException("No valid token available and auto-refresh is disabled")
    
    async def _refresh_token_if_needed(self) -> str:
        """Refresh token if needed and return valid token."""
        if not self._current_provider:
            raise AuthenticationException("No authenticated session")
        
        # Check again after acquiring lock
        if hasattr(self._current_provider, '_access_token'):
            token = getattr(self._current_provider, '_access_token')
            if token and self._current_provider.is_token_valid(token):
                return token
        
        # Try to refresh token
        refresh_token = getattr(self._current_provider, '_refresh_token', None)
        if refresh_token:
            try:
                result = await self._current_provider.refresh_token(refresh_token)
                return result.get('access_token', '')
            except Exception as e:
                raise AuthenticationException(f"Token refresh failed: {str(e)}")
        
        raise AuthenticationException("No refresh token available")
    
    def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for the current session."""
        if not self._current_provider:
            raise AuthenticationException("No authenticated session")
        
        if hasattr(self._current_provider, 'get_auth_headers'):
            return self._current_provider.get_auth_headers()
        
        # Fallback to basic Bearer token
        token = getattr(self._current_provider, '_access_token', None)
        if not token:
            raise AuthenticationException("No access token available")
        
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
    
    def is_authenticated(self) -> bool:
        """Check if there's an active authenticated session."""
        return self._current_provider is not None
    
    def get_current_auth_type(self) -> Optional[AuthenticationType]:
        """Get the current authentication type."""
        return self._current_auth_type
    
    def logout(self) -> None:
        """Clear current authentication session."""
        self._current_provider = None
        self._current_auth_type = None
    
    def enable_auto_refresh(self, enabled: bool = True) -> None:
        """Enable or disable automatic token refresh."""
        self._auto_refresh_enabled = enabled
    
    async def validate_token(self, token: Optional[str] = None) -> bool:
        """Validate a token (current token if none provided)."""
        if not self._current_provider:
            return False
        
        if token is None:
            token = getattr(self._current_provider, '_access_token', None)
        
        if not token:
            return False
        
        return self._current_provider.is_token_valid(token)
    
    def get_token_expiry(self) -> Optional[datetime]:
        """Get the expiry time of the current token."""
        if not self._current_provider:
            return None
        
        token = getattr(self._current_provider, '_access_token', None)
        if not token:
            return None
        
        return self._current_provider.get_token_expiry(token)