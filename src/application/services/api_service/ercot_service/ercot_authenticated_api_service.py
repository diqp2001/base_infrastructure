"""
ERCOT Authenticated API Service

Provides access to ERCOT's public API with authentication for enhanced data access.
Uses ID token authentication flow with username/password credentials.

Key Features:
- ID token authentication via ERCOT B2C OAuth flow
- Day-ahead market (DAM) settlement point prices
- Real-time market (RTM) settlement point prices  
- Automatic token refresh and session management
- Automatic pagination handling for large datasets
- Rate limiting respect (100 requests/minute)
- Settlement point filtering and validation

Data Coverage:
- Enhanced data access beyond 90-day public limit
- 15-minute interval pricing data
- Major hubs and load zones across Texas
"""

import datetime
import json
import os
import time
from typing import Dict, Any, List, Optional, Union
import requests
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ERCOTCredentials:
    """ERCOT API credentials configuration"""
    username: str
    password: str
    subscription_key: str
    
    @classmethod
    def from_file(cls, filepath: str) -> 'ERCOTCredentials':
        """Load credentials from JSON file"""
        filepath = Path.cwd().parent / filepath
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(
            username=data['username'],
            password=data['password'], 
            subscription_key=data['subscription_key']
        )
    
    @classmethod
    def from_env(cls) -> 'ERCOTCredentials':
        """Load credentials from environment variables"""
        return cls(
            username=os.getenv('ERCOT_USERNAME', ''),
            password=os.getenv('ERCOT_PASSWORD', ''),
            subscription_key=os.getenv('ERCOT_SUBSCRIPTION_KEY', '')
        )


@dataclass
class ERCOTRateLimit:
    """Rate limiting configuration for ERCOT authenticated API"""
    max_requests_per_minute: int = 100
    max_records_per_request: int = 5000
    request_delay: float = 0.6  # Seconds between requests


class ErcotAuthenticatedApiService:
    """
    Service for accessing ERCOT authenticated API endpoints for enhanced energy market data.
    
    This service provides access to day-ahead and real-time market pricing data
    using ERCOT's authenticated API with ID token flow.
    
    Features enhanced data access beyond the 90-day public API limitation.
    All timestamps are in Central Time (CT/CDT).
    Data is provided in 15-minute intervals.
    """
    
    # ERCOT API URLs
    BASE_URL = "https://api.ercot.com/api/public-reports"
    AUTH_URL = "https://ercotb2c.b2clogin.com/ercotb2c.onmicrosoft.com/B2C_1_PUBAPI-ROPC-FLOW/oauth2/v2.0/token"
    
    # Major Settlement Points
    MAJOR_HUBS = [
        "HB_HOUSTON",     # Houston Hub
        "HB_NORTH",       # North Hub  
        "HB_SOUTH",       # South Hub
        "HB_WEST",        # West Hub
    ]
    
    MAJOR_LOAD_ZONES = [
        "LZ_AEN",         # AEP Texas Central
        "LZ_CPS",         # CPS Energy
        "LZ_HOUSTON",     # Houston Load Zone
        "LZ_NORTH",       # North Load Zone
        "LZ_SOUTH",       # South Load Zone
        "LZ_WEST",        # West Load Zone
    ]

    def __init__(self, credentials: ERCOTCredentials, timeout: int = 30, 
                 rate_limit: Optional[ERCOTRateLimit] = None):
        """
        Initialize the ERCOT Authenticated API service.
        
        Args:
            credentials: ERCOT API credentials
            timeout: Request timeout in seconds (default: 30)
            rate_limit: Rate limiting configuration (uses default if None)
        """
        self.credentials = credentials
        self.timeout = timeout
        self.rate_limit = rate_limit or ERCOTRateLimit()
        self.session = requests.Session()
        
        # Authentication state
        self._access_token = None
        self._token_expires_at = None
        
        # Set default headers
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json", 
            "User-Agent": "BaseInfrastructure-ErcotAuthenticatedAPI/1.0"
        })
        
        if self.credentials.subscription_key:
            self.session.headers.update({
                "Ocp-Apim-Subscription-Key": self.credentials.subscription_key
            })
        
        self.last_request_time = 0.0

    def _get_auth_token(self) -> bool:
        """
        Obtain ID token using ERCOT B2C OAuth flow.
        
        Returns:
            True if authentication successful, False otherwise
        """
        auth_params = {
            "username": self.credentials.username,
            "password": self.credentials.password,
            "grant_type": "password",
            "scope": "openid fec253ea-0d06-4272-a5e6-b478baeecd70 offline_access",
            "client_id": "fec253ea-0d06-4272-a5e6-b478baeecd70",
            "response_type": "id_token"
        }
        
        try:
            response = requests.post(self.AUTH_URL, params=auth_params, timeout=self.timeout)
            response.raise_for_status()
            
            auth_data = response.json()
            self._access_token = auth_data.get("access_token")
            
            if not self._access_token:
                print("Failed to retrieve access token from authentication response")
                return False
            
            # Set token expiration (default to 1 hour if not provided)
            expires_in = auth_data.get("expires_in", 3600)  # Default 1 hour
            self._token_expires_at = time.time() + expires_in - 60  # Refresh 1 minute early
            
            # Update session headers with token
            self.session.headers.update({
                "Authorization": f"Bearer {self._access_token}"
            })
            
            print("ERCOT authentication successful")
            return True
            
        except requests.exceptions.RequestException as e:
            print(f"ERCOT authentication failed: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error during ERCOT authentication: {e}")
            return False

    def _ensure_authenticated(self) -> bool:
        """
        Ensure we have a valid authentication token.
        
        Returns:
            True if authentication is valid, False otherwise
        """
        # Check if we need to authenticate or refresh token
        if (self._access_token is None or 
            self._token_expires_at is None or 
            time.time() >= self._token_expires_at):
            
            return self._get_auth_token()
        
        return True

    def _respect_rate_limit(self):
        """Ensure rate limiting is respected between API calls"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit.request_delay:
            sleep_time = self.rate_limit.request_delay - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Make a request to the ERCOT authenticated API with rate limiting.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            API response data or None if failed
        """
        # Ensure we're authenticated
        if not self._ensure_authenticated():
            print("Authentication failed, cannot make API request")
            return None
            
        self._respect_rate_limit()
        
        try:
            url = f"{self.BASE_URL}{endpoint}"
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"ERCOT authenticated API request failed: {e}")
            
            # If 401 unauthorized, try to re-authenticate once
            if hasattr(e, 'response') and e.response.status_code == 401:
                print("Token may have expired, attempting re-authentication...")
                self._access_token = None  # Force re-authentication
                if self._ensure_authenticated():
                    try:
                        response = self.session.get(url, params=params, timeout=self.timeout)
                        response.raise_for_status()
                        return response.json()
                    except requests.exceptions.RequestException as retry_e:
                        print(f"Retry after re-authentication failed: {retry_e}")
            
            return None
        except Exception as e:
            print(f"Unexpected error in ERCOT authenticated API request: {e}")
            return None

    def get_day_ahead_prices(
        self,
        start_date: Union[datetime.date, str],
        end_date: Union[datetime.date, str],
        settlement_point: Optional[str] = None,
        page: int = 1,
        page_size: int = 5000
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch day-ahead market (DAM) settlement point prices.
        
        Args:
            start_date: Start date for data retrieval (YYYY-MM-DD)
            end_date: End date for data retrieval (YYYY-MM-DD)
            settlement_point: Optional settlement point filter (e.g., 'HB_HOUSTON')
            page: Page number for pagination (default: 1)
            page_size: Records per page (max: 5000, default: 5000)
            
        Returns:
            Dictionary containing price data and pagination info, or None if failed
            
        Example:
            >>> credentials = ERCOTCredentials.from_file('ercot_credentials.json')
            >>> service = ErcotAuthenticatedApiService(credentials)
            >>> prices = service.get_day_ahead_prices('2024-12-01', '2024-12-05')
            >>> for record in prices['data'][:5]:
            ...     print(f"{record['settlementPoint']}: ${record['settlementPointPrice']}")
        """
        # Convert dates to strings if needed
        if isinstance(start_date, datetime.date):
            start_date = start_date.strftime("%Y-%m-%d")
        if isinstance(end_date, datetime.date):
            end_date = end_date.strftime("%Y-%m-%d")
            
        # Validate page size
        page_size = min(page_size, self.rate_limit.max_records_per_request)
        
        params = {
            "deliveryDateFrom": start_date,
            "deliveryDateTo": end_date,
            "page": page,
            "size": page_size
        }
        
        # Add settlement point filter if provided
        if settlement_point:
            params["settlementPoint"] = settlement_point
        
        # DAM Settlement Point Prices endpoint
        endpoint = "/np4-190-cd/dam_stlmnt_pnt_prices"
        return self._make_request(endpoint, params)

    def get_physical_prices(
        self,
        start_date: Union[datetime.date, str],
        end_date: Union[datetime.date, str],
        settlement_point: Optional[str] = None,
        page: int = 1,
        page_size: int = 5000
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch real-time market (RTM) settlement point prices (physical prices).
        
        Args:
            start_date: Start date for data retrieval (YYYY-MM-DD)
            end_date: End date for data retrieval (YYYY-MM-DD)  
            settlement_point: Optional settlement point filter
            page: Page number for pagination (default: 1)
            page_size: Records per page (max: 5000, default: 5000)
            
        Returns:
            Dictionary containing price data and pagination info, or None if failed
            
        Example:
            >>> credentials = ERCOTCredentials.from_file('ercot_credentials.json')
            >>> service = ErcotAuthenticatedApiService(credentials)
            >>> prices = service.get_physical_prices('2024-12-01', '2024-12-05', 'HB_HOUSTON')
            >>> for record in prices['data'][:5]:
            ...     print(f"RTM Price: ${record['settlementPointPrice']} at {record['deliveryDate']}")
        """
        # Convert dates to strings if needed
        if isinstance(start_date, datetime.date):
            start_date = start_date.strftime("%Y-%m-%d")
        if isinstance(end_date, datetime.date):
            end_date = end_date.strftime("%Y-%m-%d")
            
        # Validate page size
        page_size = min(page_size, self.rate_limit.max_records_per_request)
        
        params = {
            "deliveryDateFrom": start_date,
            "deliveryDateTo": end_date,
            "page": page,
            "size": page_size
        }
        
        # Add settlement point filter if provided
        if settlement_point:
            params["settlementPoint"] = settlement_point
        
        # RTM Settlement Point Prices endpoint
        endpoint = "/np6-788-cd/rtm_stlmnt_pnt_prices"
        return self._make_request(endpoint, params)

    def get_day_ahead_prices_all(
        self,
        start_date: Union[datetime.date, str],
        end_date: Union[datetime.date, str],
        settlement_point: Optional[str] = None,
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all day-ahead prices using automatic pagination.
        
        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            settlement_point: Optional settlement point filter
            max_pages: Maximum pages to fetch (None for all)
            
        Returns:
            List of all price records across all pages
            
        Example:
            >>> credentials = ERCOTCredentials.from_file('ercot_credentials.json')
            >>> service = ErcotAuthenticatedApiService(credentials)
            >>> all_prices = service.get_day_ahead_prices_all('2024-12-01', '2024-12-31')
            >>> print(f"Retrieved {len(all_prices)} price records")
        """
        all_records = []
        page = 1
        
        while max_pages is None or page <= max_pages:
            response = self.get_day_ahead_prices(start_date, end_date, settlement_point, page)
            
            if not response or 'data' not in response:
                break
                
            page_data = response['data']
            if not page_data:  # Empty page
                break
                
            all_records.extend(page_data)
            
            # Check pagination info
            page_info = response.get('page', {})
            total_pages = page_info.get('totalPages', 1)
            
            if page >= total_pages:
                break
                
            page += 1
            
        return all_records

    def get_physical_prices_all(
        self,
        start_date: Union[datetime.date, str],
        end_date: Union[datetime.date, str],
        settlement_point: Optional[str] = None,
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all physical prices using automatic pagination.
        
        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            settlement_point: Optional settlement point filter
            max_pages: Maximum pages to fetch (None for all)
            
        Returns:
            List of all price records across all pages
            
        Example:
            >>> credentials = ERCOTCredentials.from_file('ercot_credentials.json')
            >>> service = ErcotAuthenticatedApiService(credentials)
            >>> all_prices = service.get_physical_prices_all('2024-12-01', '2024-12-31', 'LZ_HOUSTON')
            >>> print(f"Retrieved {len(all_prices)} RTM price records")
        """
        all_records = []
        page = 1
        
        while max_pages is None or page <= max_pages:
            response = self.get_physical_prices(start_date, end_date, settlement_point, page)
            
            if not response or 'data' not in response:
                break
                
            page_data = response['data']
            if not page_data:  # Empty page
                break
                
            all_records.extend(page_data)
            
            # Check pagination info
            page_info = response.get('page', {})
            total_pages = page_info.get('totalPages', 1)
            
            if page >= total_pages:
                break
                
            page += 1
            
        return all_records

    def get_settlement_points_info(self) -> Dict[str, List[str]]:
        """
        Get information about major settlement points.
        
        Returns:
            Dictionary with hub and load zone information
            
        Example:
            >>> credentials = ERCOTCredentials.from_file('ercot_credentials.json')
            >>> service = ErcotAuthenticatedApiService(credentials)
            >>> points = service.get_settlement_points_info()
            >>> print("Major Hubs:", points['hubs'])
            >>> print("Load Zones:", points['load_zones'])
        """
        return {
            "hubs": self.MAJOR_HUBS.copy(),
            "load_zones": self.MAJOR_LOAD_ZONES.copy(),
            "all_major_points": self.MAJOR_HUBS + self.MAJOR_LOAD_ZONES
        }

    def check_api_health(self) -> Dict[str, Any]:
        """
        Check ERCOT authenticated API health and connectivity.
        
        Returns:
            Dictionary with health check results
            
        Example:
            >>> credentials = ERCOTCredentials.from_file('ercot_credentials.json')
            >>> service = ErcotAuthenticatedApiService(credentials)
            >>> health = service.check_api_health()
            >>> print(f"API Status: {health['status']}")
        """
        try:
            # Check authentication first
            auth_success = self._ensure_authenticated()
            if not auth_success:
                return {
                    "status": "unhealthy",
                    "error": "Authentication failed",
                    "authenticated": False,
                    "base_url": self.BASE_URL,
                    "timestamp": datetime.datetime.now().isoformat()
                }
            
            # Try a simple API call with recent date
            yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            test_response = self.get_day_ahead_prices(yesterday, yesterday, page_size=1)
            
            api_responsive = test_response is not None
            
            return {
                "status": "healthy" if api_responsive else "unhealthy",
                "authenticated": auth_success,
                "api_responsive": api_responsive,
                "base_url": self.BASE_URL,
                "auth_url": self.AUTH_URL,
                "rate_limit": {
                    "max_requests_per_minute": self.rate_limit.max_requests_per_minute,
                    "max_records_per_request": self.rate_limit.max_records_per_request
                },
                "timestamp": datetime.datetime.now().isoformat(),
                "test_date": yesterday
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "authenticated": False,
                "base_url": self.BASE_URL,
                "timestamp": datetime.datetime.now().isoformat()
            }

    def get_authentication_info(self) -> Dict[str, Any]:
        """
        Get current authentication status and token information.
        
        Returns:
            Dictionary with authentication details
        """
        return {
            "authenticated": self._access_token is not None,
            "token_expires_at": self._token_expires_at,
            "token_valid": (
                self._access_token is not None and 
                self._token_expires_at is not None and 
                time.time() < self._token_expires_at
            ),
            "username": self.credentials.username,
            "has_subscription_key": bool(self.credentials.subscription_key),
            "timestamp": datetime.datetime.now().isoformat()
        }