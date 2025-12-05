import os
import datetime
import base64
from typing import Dict, Any, List, Optional
from .api_service import ApiService


class ErcotApiService(ApiService):
    """
    Service for accessing ERCOT (Electric Reliability Council of Texas) energy market data.
    
    This service provides access to:
    - Day-ahead market (DAM) clearing prices
    - Real-time market (RTM) settlement prices (physical prices)
    - Settlement point data
    
    Authentication uses OAuth 2.0 client credentials flow.
    """

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        base_url: str = "https://api.ercot.com/api/1",
        timeout: int = 60
    ):
        """
        Initialize the ERCOT API service.

        Args:
            client_id: OAuth 2.0 client ID for ERCOT API access
            client_secret: OAuth 2.0 client secret for ERCOT API access
            base_url: Base URL for ERCOT API (default production endpoint)
            timeout: Request timeout in seconds
        """
        super().__init__(base_url, timeout=timeout)
        
        self.client_id = client_id or os.getenv("ERCOT_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("ERCOT_CLIENT_SECRET")
        
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Client credentials are required. Set ERCOT_CLIENT_ID and ERCOT_CLIENT_SECRET "
                "environment variables or provide client_id and client_secret parameters."
            )
        
        self.access_token = None
        self.token_expires_at = None
        
        # Set default headers for ERCOT API
        self.add_header("Content-Type", "application/json")
        self.add_header("Accept", "application/json")
        self.add_header("User-Agent", "BaseInfrastructure-ErcotClient/1.0")
        
        # Authenticate on initialization
        self._authenticate()

    def _authenticate(self) -> bool:
        """
        Authenticate with ERCOT API using OAuth 2.0 client credentials flow.
        
        Returns:
            True if authentication successful, False otherwise
        """
        try:
            # Prepare credentials for Basic Auth header
            credentials = f"{self.client_id}:{self.client_secret}"
            encoded_credentials = base64.b64encode(credentials.encode()).decode()
            
            # Prepare authentication request
            auth_headers = {
                "Content-Type": "application/x-www-form-urlencoded",
                "Authorization": f"Basic {encoded_credentials}"
            }
            
            auth_data = {
                "grant_type": "client_credentials",
                "scope": "read:market_data"
            }
            
            # Save current headers and temporarily set auth headers
            original_headers = self.session.headers.copy()
            self.session.headers.clear()
            self.session.headers.update(auth_headers)
            
            # Make authentication request
            auth_url = f"{self.api_url}/oauth/token"
            response = self.session.post(auth_url, data=auth_data, timeout=self.timeout)
            
            # Restore original headers
            self.session.headers.clear()
            self.session.headers.update(original_headers)
            
            response.raise_for_status()
            auth_response = response.json()
            
            # Extract token information
            self.access_token = auth_response.get("access_token")
            expires_in = auth_response.get("expires_in", 3600)  # Default 1 hour
            
            if self.access_token:
                # Calculate expiry time
                self.token_expires_at = datetime.datetime.now() + datetime.timedelta(seconds=expires_in - 300)  # 5 min buffer
                
                # Set authorization header
                self.session.headers["Authorization"] = f"Bearer {self.access_token}"
                return True
            
            return False
            
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False

    def _ensure_authenticated(self) -> bool:
        """
        Ensure we have a valid access token, refreshing if necessary.
        
        Returns:
            True if authenticated, False otherwise
        """
        if not self.access_token or (self.token_expires_at and datetime.datetime.now() >= self.token_expires_at):
            return self._authenticate()
        return True

    def _make_authenticated_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Make an authenticated request to the ERCOT API.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            API response data or None if failed
        """
        if not self._ensure_authenticated():
            print("Failed to authenticate with ERCOT API")
            return None
            
        return self.fetch_data(endpoint, params)

    def get_day_ahead_prices(
        self,
        start_date: datetime.date,
        end_date: datetime.date,
        settlement_point: Optional[str] = None,
        page: int = 1,
        limit: int = 1000
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch day-ahead market (DAM) clearing prices.
        
        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            settlement_point: Optional settlement point ID (e.g., 'LZ_HOUSTON')
            page: Page number for pagination (default: 1)
            limit: Records per page (max: 1000, default: 1000)
            
        Returns:
            Dictionary containing price data and pagination info, or None if failed
            
        Example:
            >>> service = ErcotApiService(client_id='your_id', client_secret='your_secret')
            >>> start = datetime.date(2024, 12, 1)
            >>> end = datetime.date(2024, 12, 5)
            >>> prices = service.get_day_ahead_prices(start, end, settlement_point='LZ_HOUSTON')
        """
        if start_date > end_date:
            raise ValueError("Start date must be before or equal to end date")
        
        params = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "page": page,
            "limit": min(limit, 1000)  # Enforce API limit
        }
        
        if settlement_point:
            params["settlement_point"] = settlement_point
            
        return self._make_authenticated_request("/market/dam/prices", params)

    def get_physical_prices(
        self,
        start_date: datetime.date,
        end_date: datetime.date,
        settlement_point: Optional[str] = None,
        price_type: Optional[str] = None,
        page: int = 1,
        limit: int = 1000
    ) -> Optional[Dict[str, Any]]:
        """
        Fetch real-time market (RTM) settlement prices (physical prices).
        
        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            settlement_point: Optional settlement point ID
            price_type: Optional price type filter ('LMP', 'MCC', 'MLC')
            page: Page number for pagination (default: 1)
            limit: Records per page (max: 1000, default: 1000)
            
        Returns:
            Dictionary containing price data and pagination info, or None if failed
            
        Example:
            >>> service = ErcotApiService(client_id='your_id', client_secret='your_secret')
            >>> start = datetime.date(2024, 12, 1)
            >>> end = datetime.date(2024, 12, 5)
            >>> prices = service.get_physical_prices(start, end, price_type='LMP')
        """
        if start_date > end_date:
            raise ValueError("Start date must be before or equal to end date")
        
        params = {
            "startDate": start_date.strftime("%Y-%m-%d"),
            "endDate": end_date.strftime("%Y-%m-%d"),
            "page": page,
            "limit": min(limit, 1000)  # Enforce API limit
        }
        
        if settlement_point:
            params["settlement_point"] = settlement_point
            
        if price_type:
            if price_type not in ["LMP", "MCC", "MLC"]:
                raise ValueError("price_type must be one of: LMP, MCC, MLC")
            params["price_type"] = price_type
            
        return self._make_authenticated_request("/market/rtm/prices", params)

    def get_settlement_points(self) -> Optional[List[Dict[str, Any]]]:
        """
        Fetch list of available settlement points.
        
        Returns:
            List of settlement points with their details, or None if failed
            
        Example:
            >>> service = ErcotApiService(client_id='your_id', client_secret='your_secret')
            >>> points = service.get_settlement_points()
            >>> for point in points[:5]:  # Show first 5
            ...     print(f"{point['id']}: {point['name']}")
        """
        response = self._make_authenticated_request("/market/settlement_points")
        
        if response and 'data' in response:
            return response['data']
        return response

    def get_day_ahead_prices_paginated(
        self,
        start_date: datetime.date,
        end_date: datetime.date,
        settlement_point: Optional[str] = None,
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all day-ahead prices using pagination.
        
        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            settlement_point: Optional settlement point ID
            max_pages: Maximum number of pages to fetch (None for all)
            
        Returns:
            List of all price records across all pages
            
        Example:
            >>> service = ErcotApiService(client_id='your_id', client_secret='your_secret')
            >>> start = datetime.date(2024, 12, 1)
            >>> end = datetime.date(2024, 12, 31)  # Large date range
            >>> all_prices = service.get_day_ahead_prices_paginated(start, end)
        """
        all_data = []
        page = 1
        
        while max_pages is None or page <= max_pages:
            response = self.get_day_ahead_prices(start_date, end_date, settlement_point, page)
            
            if not response or 'data' not in response:
                break
                
            page_data = response['data']
            if not page_data:  # Empty page
                break
                
            all_data.extend(page_data)
            
            # Check if there are more pages
            pagination = response.get('pagination', {})
            if page >= pagination.get('total_pages', 1):
                break
                
            page += 1
        
        return all_data

    def get_physical_prices_paginated(
        self,
        start_date: datetime.date,
        end_date: datetime.date,
        settlement_point: Optional[str] = None,
        price_type: Optional[str] = None,
        max_pages: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all physical prices using pagination.
        
        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            settlement_point: Optional settlement point ID
            price_type: Optional price type filter ('LMP', 'MCC', 'MLC')
            max_pages: Maximum number of pages to fetch (None for all)
            
        Returns:
            List of all price records across all pages
            
        Example:
            >>> service = ErcotApiService(client_id='your_id', client_secret='your_secret')
            >>> start = datetime.date(2024, 12, 1)
            >>> end = datetime.date(2024, 12, 31)  # Large date range
            >>> all_prices = service.get_physical_prices_paginated(start, end, price_type='LMP')
        """
        all_data = []
        page = 1
        
        while max_pages is None or page <= max_pages:
            response = self.get_physical_prices(start_date, end_date, settlement_point, price_type, page)
            
            if not response or 'data' not in response:
                break
                
            page_data = response['data']
            if not page_data:  # Empty page
                break
                
            all_data.extend(page_data)
            
            # Check if there are more pages
            pagination = response.get('pagination', {})
            if page >= pagination.get('total_pages', 1):
                break
                
            page += 1
        
        return all_data

    def check_api_health(self) -> Dict[str, Any]:
        """
        Check ERCOT API health and connection status.
        
        Returns:
            Dictionary with health check results
            
        Example:
            >>> service = ErcotApiService(client_id='your_id', client_secret='your_secret')
            >>> health = service.check_api_health()
            >>> print(f"API Status: {health['status']}")
        """
        try:
            # Try to authenticate
            auth_success = self._ensure_authenticated()
            
            if auth_success:
                # Try a simple API call
                settlement_points = self.get_settlement_points()
                api_responsive = settlement_points is not None
            else:
                api_responsive = False
            
            return {
                "status": "healthy" if auth_success and api_responsive else "unhealthy",
                "authentication": "success" if auth_success else "failed",
                "api_responsive": api_responsive,
                "base_url": self.api_url,
                "timestamp": datetime.datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "base_url": self.api_url,
                "timestamp": datetime.datetime.now().isoformat()
            }