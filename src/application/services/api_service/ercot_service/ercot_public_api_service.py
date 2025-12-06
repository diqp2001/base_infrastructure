"""
ERCOT Public API Service

Provides access to ERCOT's public API for energy market data.
No authentication required - uses public endpoints for market price data.

Key Features:
- Day-ahead market (DAM) settlement point prices
- 2-Day Aggregate Energy Demand Curves data
- Automatic pagination handling for large datasets
- Rate limiting respect (100 requests/minute)
- Settlement point filtering and validation

Data Coverage:
- 90-day rolling window for historical data
- 15-minute interval pricing data
- Major hubs and load zones across Texas
"""

import datetime
import os
import time
from typing import Dict, Any, List, Optional, Union
import requests
from dataclasses import dataclass

from application.services.api_service.ercot_service.ercot_authenticated_api_service import ERCOTCredentials, ErcotAuthenticatedApiService



@dataclass
class ERCOTRateLimit:
    """Rate limiting configuration for ERCOT public API"""
    max_requests_per_minute: int = 100
    max_records_per_request: int = 5000
    request_delay: float = 0.6  # Seconds between requests


class ErcotPublicApiService:
    """
    Service for accessing ERCOT public API endpoints for energy market data.
    
    This service provides access to day-ahead market prices and 2-Day Aggregate 
    Energy Demand Curves data from ERCOT's public API without requiring authentication.
    
    All timestamps are in Central Time (CT/CDT).
    Data is provided in 15-minute intervals.
    Historical data is available for a 90-day rolling window.
    """
    
    # ERCOT Public API Base URL
    BASE_URL = "https://api.ercot.com/api/public-reports"
    
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

    def __init__(self, timeout: int = 30, rate_limit: Optional[ERCOTRateLimit] = None):
        """
        Initialize the ERCOT Public API service.
        
        Args:
            timeout: Request timeout in seconds (default: 30)
            rate_limit: Rate limiting configuration (uses default if None)
        """
        # Load credentials from file (will be outside repository)
        credentials = ERCOTCredentials.from_file('ercot_credentials.json')
        self.auth_service = ErcotAuthenticatedApiService(credentials)
        self.timeout = self.auth_service.timeout 
        self.rate_limit = rate_limit or ERCOTRateLimit()
        self.session = self.auth_service.session
        
        # Set default headers
        self.session.headers.update({
            "Accept": "application/json",
            "Content-Type": "application/json", 
            "User-Agent": "BaseInfrastructure-ErcotPublicAPI/1.0"
        })
        
        self.last_request_time = 0.0

    
        

        

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
        Make a request to the ERCOT public API with rate limiting.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            API response data or None if failed
        """
        self._respect_rate_limit()
        
        try:
            url = f"{self.BASE_URL}{endpoint}"
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"ERCOT API request failed: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error in ERCOT API request: {e}")
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
            >>> service = ErcotPublicApiService()
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
        Fetch 2-Day Aggregate Energy Demand Curves data.
        
        Args:
            start_date: Start date for data retrieval (YYYY-MM-DD)
            end_date: End date for data retrieval (YYYY-MM-DD)  
            settlement_point: Optional settlement point filter
            page: Page number for pagination (default: 1)
            page_size: Records per page (max: 5000, default: 5000)
            
        Returns:
            Dictionary containing demand curve data and pagination info, or None if failed
            
        Example:
            >>> service = ErcotPublicApiService()
            >>> prices = service.get_physical_prices('2024-12-01', '2024-12-05', 'HB_HOUSTON')
            >>> for record in prices['data'][:5]:
            ...     print(f"Demand Curve Data at {record['deliveryDate']}")
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
        
        # 2-Day Aggregate Energy Demand Curves endpoint
        endpoint = "/np3-907-ex/2d_agg_edc"
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
            >>> service = ErcotPublicApiService()
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
        Fetch all 2-Day Aggregate Energy Demand Curves data using automatic pagination.
        
        Args:
            start_date: Start date for data retrieval
            end_date: End date for data retrieval
            settlement_point: Optional settlement point filter
            max_pages: Maximum pages to fetch (None for all)
            
        Returns:
            List of all demand curve records across all pages
            
        Example:
            >>> service = ErcotPublicApiService()
            >>> all_data = service.get_physical_prices_all('2024-12-01', '2024-12-31', 'LZ_HOUSTON')
            >>> print(f"Retrieved {len(all_data)} demand curve records")
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
            >>> service = ErcotPublicApiService()
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
        Check ERCOT public API health and connectivity.
        
        Returns:
            Dictionary with health check results
            
        Example:
            >>> service = ErcotPublicApiService()
            >>> health = service.check_api_health()
            >>> print(f"API Status: {health['status']}")
        """
        try:
            # Try a simple API call with recent date
            yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
            test_response = self.get_day_ahead_prices(yesterday, yesterday, page_size=1)
            
            api_responsive = test_response is not None
            
            return {
                "status": "healthy" if api_responsive else "unhealthy",
                "api_responsive": api_responsive,
                "base_url": self.BASE_URL,
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
                "base_url": self.BASE_URL,
                "timestamp": datetime.datetime.now().isoformat()
            }

    def get_date_range_info(self) -> Dict[str, Any]:
        """
        Get information about available date ranges for the API.
        
        Returns:
            Dictionary with date range information
            
        Example:
            >>> service = ErcotPublicApiService()
            >>> info = service.get_date_range_info()
            >>> print(f"Recommended start date: {info['recommended_start_date']}")
        """
        today = datetime.date.today()
        ninety_days_ago = today - datetime.timedelta(days=90)
        yesterday = today - datetime.timedelta(days=1)
        
        return {
            "today": today.strftime("%Y-%m-%d"),
            "yesterday": yesterday.strftime("%Y-%m-%d"),
            "ninety_days_ago": ninety_days_ago.strftime("%Y-%m-%d"),
            "recommended_start_date": ninety_days_ago.strftime("%Y-%m-%d"),
            "recommended_end_date": yesterday.strftime("%Y-%m-%d"),
            "note": "Public API provides 90-day rolling window of historical data",
            "data_availability": "Real-time data available within 1-2 hours"
        }