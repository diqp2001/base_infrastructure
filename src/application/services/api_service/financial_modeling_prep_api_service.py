"""
Financial Modeling Prep API Service

Provides access to Financial Modeling Prep's comprehensive financial data API.
Offers real-time quotes, historical prices, company fundamentals, and economic indicators.

Key Features:
- Real-time stock quotes and market data
- Historical price data with flexible date ranges
- Company profiles and financial statements
- Financial ratios and key metrics
- Stock screening capabilities
- Economic indicators and market indices
- Forex and cryptocurrency data
- Rate limiting and error handling

Data Coverage:
- US and international stocks
- Major currencies and cryptocurrencies
- Economic indicators and treasury data
- Company fundamentals and analyst estimates
"""

import datetime
import json
import os
import time
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass
from pathlib import Path

from .api_service import ApiService


@dataclass
class FMPCredentials:
    """Financial Modeling Prep API credentials configuration"""
    api_key: str
    
    @classmethod
    def from_file(cls, filepath: str) -> 'FMPCredentials':
        """Load credentials from JSON file"""
        filepath = Path.cwd().parent / filepath
        with open(filepath, 'r') as f:
            data = json.load(f)
        return cls(
            api_key=data['api_key']
        )
    
    @classmethod
    def from_env(cls) -> 'FMPCredentials':
        """Load credentials from environment variables"""
        return cls(
            api_key=os.getenv('FMP_API_KEY', '')
        )


@dataclass
class FMPRateLimit:
    """Rate limiting configuration for FMP API"""
    max_requests_per_minute: int = 300  # Professional plan default
    request_delay: float = 0.2  # Seconds between requests
    max_requests_per_day: int = 100000  # Professional plan default


class FinancialModelingPrepApiService(ApiService):
    """
    Service for accessing Financial Modeling Prep API for comprehensive financial market data.
    
    This service provides access to real-time quotes, historical prices, company fundamentals,
    financial statements, and economic data through a unified interface.
    
    Features include stock screening, analyst estimates, insider trading data,
    and institutional holdings across US and international markets.
    """
    
    BASE_URL = "https://financialmodelingprep.com/api"
    
    # Major stock exchanges
    MAJOR_EXCHANGES = [
        "NASDAQ",
        "NYSE", 
        "AMEX",
        "TSX",  # Toronto Stock Exchange
        "LSE",  # London Stock Exchange
        "FRA",  # Frankfurt Stock Exchange
    ]
    
    # Common financial statement periods
    PERIODS = ["annual", "quarter"]
    
    # Popular market indices
    MAJOR_INDICES = [
        "^GSPC",  # S&P 500
        "^DJI",   # Dow Jones
        "^IXIC",  # NASDAQ Composite
        "^RUT",   # Russell 2000
        "^VIX",   # Volatility Index
    ]

    def __init__(self, credentials: FMPCredentials, timeout: int = 30, 
                 rate_limit: Optional[FMPRateLimit] = None):
        """
        Initialize the Financial Modeling Prep API service.
        
        Args:
            credentials: FMP API credentials
            timeout: Request timeout in seconds (default: 30)
            rate_limit: Rate limiting configuration (uses default if None)
        """
        super().__init__(self.BASE_URL, timeout=timeout)
        self.credentials = credentials
        self.rate_limit = rate_limit or FMPRateLimit()
        
        if not self.credentials.api_key:
            raise ValueError("FMP API key is required")
        
        # Set default headers
        self.add_header("User-Agent", "BaseInfrastructure-FMP-API/1.0")
        
        self.last_request_time = 0.0

    def _respect_rate_limit(self):
        """Ensure rate limiting is respected between API calls"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit.request_delay:
            sleep_time = self.rate_limit.request_delay - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict[str, Any]]:
        """
        Make a request to the FMP API with rate limiting and API key authentication.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            
        Returns:
            API response data or None if failed
        """
        self._respect_rate_limit()
        
        # Add API key to parameters
        if params is None:
            params = {}
        params['apikey'] = self.credentials.api_key
        
        try:
            response = self.fetch_data(endpoint, params=params)
            return response
            
        except Exception as e:
            print(f"FMP API request failed: {e}")
            return None

    def get_quote(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get real-time quote for a stock symbol.
        
        Args:
            symbol: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
            
        Returns:
            Dictionary containing quote data or None if failed
            
        Example:
            >>> credentials = FMPCredentials.from_file('fmp_credentials.json')
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> quote = service.get_quote('AAPL')
            >>> print(f"{quote['symbol']}: ${quote['price']}")
        """
        endpoint = f"/v3/quote/{symbol.upper()}"
        response = self._make_request(endpoint)
        
        # FMP returns a list with single item for quote endpoint
        if response and isinstance(response, list) and len(response) > 0:
            return response[0]
        return response

    def get_quotes(self, symbols: List[str]) -> Optional[List[Dict[str, Any]]]:
        """
        Get real-time quotes for multiple stock symbols.
        
        Args:
            symbols: List of stock ticker symbols
            
        Returns:
            List of dictionaries containing quote data or None if failed
        """
        symbols_str = ','.join([s.upper() for s in symbols])
        endpoint = f"/v3/quote/{symbols_str}"
        return self._make_request(endpoint)

    def get_historical_prices(
        self, 
        symbol: str, 
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        period: str = "1day"
    ) -> Optional[Dict[str, Any]]:
        """
        Get historical price data for a stock symbol.
        
        Args:
            symbol: Stock ticker symbol
            from_date: Start date (YYYY-MM-DD format, optional)
            to_date: End date (YYYY-MM-DD format, optional)
            period: Time period (1min, 5min, 15min, 30min, 1hour, 4hour, 1day)
            
        Returns:
            Dictionary containing historical price data or None if failed
            
        Example:
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> prices = service.get_historical_prices('AAPL', '2024-01-01', '2024-12-01')
            >>> for price in prices['historical'][:5]:
            ...     print(f"{price['date']}: ${price['close']}")
        """
        endpoint = f"/v3/historical-price-full/{symbol.upper()}"
        params = {}
        
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date
        if period != "1day":
            # For intraday data, use different endpoint
            endpoint = f"/v3/historical-chart/{period}/{symbol.upper()}"
            
        return self._make_request(endpoint, params)

    def get_company_profile(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get company profile information.
        
        Args:
            symbol: Stock ticker symbol
            
        Returns:
            Dictionary containing company profile data or None if failed
        """
        endpoint = f"/v3/profile/{symbol.upper()}"
        response = self._make_request(endpoint)
        
        # FMP returns a list with single item for profile endpoint
        if response and isinstance(response, list) and len(response) > 0:
            return response[0]
        return response

    def get_income_statement(
        self, 
        symbol: str, 
        period: str = "annual", 
        limit: int = 20
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get income statement data for a company.
        
        Args:
            symbol: Stock ticker symbol
            period: 'annual' or 'quarter'
            limit: Number of periods to retrieve
            
        Returns:
            List of dictionaries containing income statement data or None if failed
        """
        endpoint = f"/v3/income-statement/{symbol.upper()}"
        params = {
            'period': period,
            'limit': limit
        }
        return self._make_request(endpoint, params)

    def get_balance_sheet(
        self, 
        symbol: str, 
        period: str = "annual", 
        limit: int = 20
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get balance sheet data for a company.
        
        Args:
            symbol: Stock ticker symbol
            period: 'annual' or 'quarter'
            limit: Number of periods to retrieve
            
        Returns:
            List of dictionaries containing balance sheet data or None if failed
        """
        endpoint = f"/v3/balance-sheet-statement/{symbol.upper()}"
        params = {
            'period': period,
            'limit': limit
        }
        return self._make_request(endpoint, params)

    def get_cash_flow_statement(
        self, 
        symbol: str, 
        period: str = "annual", 
        limit: int = 20
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cash flow statement data for a company.
        
        Args:
            symbol: Stock ticker symbol
            period: 'annual' or 'quarter'
            limit: Number of periods to retrieve
            
        Returns:
            List of dictionaries containing cash flow data or None if failed
        """
        endpoint = f"/v3/cash-flow-statement/{symbol.upper()}"
        params = {
            'period': period,
            'limit': limit
        }
        return self._make_request(endpoint, params)

    def get_financial_ratios(self, symbol: str, period: str = "annual") -> Optional[List[Dict[str, Any]]]:
        """
        Get financial ratios for a company.
        
        Args:
            symbol: Stock ticker symbol
            period: 'annual' or 'quarter'
            
        Returns:
            List of dictionaries containing financial ratios or None if failed
        """
        endpoint = f"/v3/ratios/{symbol.upper()}"
        params = {'period': period}
        return self._make_request(endpoint, params)

    def get_key_metrics(self, symbol: str, period: str = "annual") -> Optional[List[Dict[str, Any]]]:
        """
        Get key financial metrics for a company.
        
        Args:
            symbol: Stock ticker symbol
            period: 'annual' or 'quarter'
            
        Returns:
            List of dictionaries containing key metrics or None if failed
        """
        endpoint = f"/v3/key-metrics/{symbol.upper()}"
        params = {'period': period}
        return self._make_request(endpoint, params)

    def get_stock_screener(
        self, 
        market_cap_more_than: Optional[int] = None,
        market_cap_less_than: Optional[int] = None,
        price_more_than: Optional[float] = None,
        price_less_than: Optional[float] = None,
        beta_more_than: Optional[float] = None,
        beta_less_than: Optional[float] = None,
        volume_more_than: Optional[int] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        exchange: Optional[str] = None,
        limit: int = 1000
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Screen stocks based on various financial criteria.
        
        Args:
            market_cap_more_than: Minimum market cap
            market_cap_less_than: Maximum market cap
            price_more_than: Minimum stock price
            price_less_than: Maximum stock price
            beta_more_than: Minimum beta
            beta_less_than: Maximum beta
            volume_more_than: Minimum trading volume
            sector: Sector filter
            industry: Industry filter
            exchange: Exchange filter (NASDAQ, NYSE, etc.)
            limit: Maximum number of results
            
        Returns:
            List of dictionaries containing screened stocks or None if failed
        """
        endpoint = "/v3/stock-screener"
        params = {'limit': limit}
        
        # Add optional filters
        filters = {
            'marketCapMoreThan': market_cap_more_than,
            'marketCapLessThan': market_cap_less_than,
            'priceMoreThan': price_more_than,
            'priceLessThan': price_less_than,
            'betaMoreThan': beta_more_than,
            'betaLessThan': beta_less_than,
            'volumeMoreThan': volume_more_than,
            'sector': sector,
            'industry': industry,
            'exchange': exchange
        }
        
        # Add non-None filters to params
        params.update({k: v for k, v in filters.items() if v is not None})
        
        return self._make_request(endpoint, params)

    def get_forex_rates(self, symbols: List[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get foreign exchange rates.
        
        Args:
            symbols: List of forex pairs (e.g., ['EURUSD', 'GBPUSD'])
            
        Returns:
            List of dictionaries containing forex rates or None if failed
        """
        if symbols:
            symbols_str = ','.join(symbols)
            endpoint = f"/v3/fx/{symbols_str}"
        else:
            endpoint = "/v3/fx"
            
        return self._make_request(endpoint)

    def get_crypto_prices(self, symbols: List[str] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get cryptocurrency prices.
        
        Args:
            symbols: List of crypto symbols (e.g., ['BTCUSD', 'ETHUSD'])
            
        Returns:
            List of dictionaries containing crypto prices or None if failed
        """
        if symbols:
            symbols_str = ','.join(symbols)
            endpoint = f"/v3/quote/{symbols_str}"
        else:
            endpoint = "/v3/cryptocurrencies"
            
        return self._make_request(endpoint)

    def get_market_indices(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get major market indices data.
        
        Returns:
            List of dictionaries containing market indices data or None if failed
        """
        indices_str = ','.join(self.MAJOR_INDICES)
        endpoint = f"/v3/quote/{indices_str}"
        return self._make_request(endpoint)

    def get_economic_indicators(self, name: str = None) -> Optional[List[Dict[str, Any]]]:
        """
        Get economic indicators data.
        
        Args:
            name: Specific economic indicator name (optional)
            
        Returns:
            List of dictionaries containing economic data or None if failed
        """
        if name:
            endpoint = f"/v4/economic"
            params = {'name': name}
            return self._make_request(endpoint, params)
        else:
            endpoint = "/v4/economic_calendar"
            return self._make_request(endpoint)

    def check_api_health(self) -> Dict[str, Any]:
        """
        Check FMP API health and connectivity.
        
        Returns:
            Dictionary with health check results
            
        Example:
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> health = service.check_api_health()
            >>> print(f"API Status: {health['status']}")
        """
        try:
            # Test with a simple quote request
            test_response = self.get_quote('AAPL')
            
            api_responsive = test_response is not None
            
            return {
                "status": "healthy" if api_responsive else "unhealthy",
                "api_responsive": api_responsive,
                "base_url": self.BASE_URL,
                "rate_limit": {
                    "max_requests_per_minute": self.rate_limit.max_requests_per_minute,
                    "max_requests_per_day": self.rate_limit.max_requests_per_day
                },
                "has_api_key": bool(self.credentials.api_key),
                "timestamp": datetime.datetime.now().isoformat(),
                "test_symbol": "AAPL"
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "api_responsive": False,
                "base_url": self.BASE_URL,
                "timestamp": datetime.datetime.now().isoformat()
            }

    def get_supported_exchanges(self) -> List[str]:
        """
        Get list of supported major exchanges.
        
        Returns:
            List of supported exchange codes
        """
        return self.MAJOR_EXCHANGES.copy()

    def get_supported_periods(self) -> List[str]:
        """
        Get list of supported financial statement periods.
        
        Returns:
            List of supported periods
        """
        return self.PERIODS.copy()

    def get_major_indices(self) -> List[str]:
        """
        Get list of major market indices symbols.
        
        Returns:
            List of major index symbols
        """
        return self.MAJOR_INDICES.copy()