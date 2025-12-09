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

import requests

from ..api_service import ApiService


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
    STABLE_BASE_URL = "https://financialmodelingprep.com/stable"
    
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

    def __init__(self,  timeout: int = 30, 
                 rate_limit: Optional[FMPRateLimit] = None):
        """
        Initialize the Financial Modeling Prep API service.
        
        Args:
            credentials: FMP API credentials
            timeout: Request timeout in seconds (default: 30)
            rate_limit: Rate limiting configuration (uses default if None)
        """
        super().__init__(self.BASE_URL, timeout=timeout)
        self.credentials = FMPCredentials.from_file('FPM_credentials.json')
        
        self.session = requests.Session()
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

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None, use_stable: bool = False) -> Optional[Dict[str, Any]]:
        """
        Make a request to the FMP API with rate limiting and API key authentication.
        
        Args:
            endpoint: API endpoint path
            params: Query parameters
            use_stable: If True, use stable URL base instead of v3
            
        Returns:
            API response data or None if failed
        """
        self._respect_rate_limit()
        
        # Add API key to parameters
        if params is None:
            params = {}
        params['apikey'] = self.credentials.api_key
        
        # Construct full URL based on endpoint type
        if use_stable:
            full_url = f"{self.STABLE_BASE_URL}{endpoint}"
        else:
            full_url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = requests.get(full_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"Error fetching data from {endpoint}: {e}")
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

    # ====================
    # FREE TIER ENDPOINTS
    # ====================
    # The following methods access FMP's free/stable endpoints
    # Available with free API key (250 calls/day limit)
    
    def search_symbol(self, query: str, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        Search for companies by ticker symbol or query string.
        **FREE ENDPOINT** - Available on free tier (250 calls/day)
        
        Args:
            query: Search query (ticker symbol or partial symbol)
            limit: Maximum number of results to return
            
        Returns:
            List of matching companies with symbol, name, and exchange info
            
        Example:
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> results = service.search_symbol('AAPL')
            >>> print(f"Found {len(results)} matches")
        """
        endpoint = "/search-symbol"
        params = {'query': query}
        if limit != 10:
            params['limit'] = limit
        return self._make_request(endpoint, params, use_stable=True)
    
    def search_company_name(self, query: str, limit: int = 10) -> Optional[List[Dict[str, Any]]]:
        """
        Search for companies by company name or partial name.
        **FREE ENDPOINT** - Available on free tier (250 calls/day)
        
        Args:
            query: Company name or partial name to search for
            limit: Maximum number of results to return
            
        Returns:
            List of matching companies with detailed information
            
        Example:
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> results = service.search_company_name('Apple')
            >>> for company in results:
            ...     print(f"{company['symbol']}: {company['name']}")
        """
        endpoint = "/search-name"
        params = {'query': query}
        if limit != 10:
            params['limit'] = limit
        return self._make_request(endpoint, params, use_stable=True)
    
    def get_financial_statement_symbol_list(self) -> Optional[List[str]]:
        """
        Get list of symbols for which financial statement data is available.
        **FREE ENDPOINT** - Available on free tier (250 calls/day)
        
        Returns:
            List of stock symbols with available financial statements
            
        Example:
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> symbols = service.get_financial_statement_symbol_list()
            >>> print(f"Financial data available for {len(symbols)} companies")
        """
        endpoint = "/v3/financial-statement-symbol-lists"
        return self._make_request(endpoint)
    
    def get_cik_list(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of companies with their CIK (Central Index Key) identifiers.
        **FREE ENDPOINT** - Available on free tier (250 calls/day)
        
        Returns:
            List of companies with CIK, symbol, and name information
            
        Example:
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> cik_list = service.get_cik_list()
            >>> for company in cik_list[:5]:
            ...     print(f"{company['symbol']}: CIK {company['cik']}")
        """
        endpoint = "/cik-list"
        return self._make_request(endpoint, use_stable=True)
    
    def search_cik(self, cik: str) -> Optional[List[Dict[str, Any]]]:
        """
        Search for companies by CIK (Central Index Key) identifier.
        **FREE ENDPOINT** - Available on free tier (250 calls/day)
        
        Args:
            cik: CIK identifier to search for
            
        Returns:
            Company information matching the CIK
            
        Example:
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> result = service.search_cik('0000320193')  # Apple's CIK
            >>> print(f"Company: {result[0]['name']}")
        """
        endpoint = "/search-cik"
        params = {'cik': cik}
        return self._make_request(endpoint, params, use_stable=True)
    
    def get_available_exchanges(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of all supported stock exchanges.
        **FREE ENDPOINT** - Available on free tier (250 calls/day)
        
        Returns:
            List of exchanges with codes, names, and country information
            
        Example:
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> exchanges = service.get_available_exchanges()
            >>> for exchange in exchanges:
            ...     print(f"{exchange['exchangeShortName']}: {exchange['name']}")
        """
        endpoint = "/available-exchanges"
        return self._make_request(endpoint, use_stable=True)
    
    def get_available_sectors(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of all available sectors in the FMP database.
        **FREE ENDPOINT** - Available on free tier (250 calls/day)
        
        Returns:
            List of sectors with sector information
            
        Example:
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> sectors = service.get_available_sectors()
            >>> print(f"Available sectors: {[s['sector'] for s in sectors]}")
        """
        endpoint = "/available-sectors"
        return self._make_request(endpoint, use_stable=True)
    
    def get_available_countries(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of countries for which stock data is supported.
        **FREE ENDPOINT** - Available on free tier (250 calls/day)
        
        Returns:
            List of countries with stock market coverage
            
        Example:
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> countries = service.get_available_countries()
            >>> for country in countries:
            ...     print(f"{country['country']}: {country['totalCompanies']} companies")
        """
        endpoint = "/available-countries"
        return self._make_request(endpoint, use_stable=True)

    def search_cusip(self, cusip: str) -> Optional[List[Dict[str, Any]]]:
        """
        Search for companies by CUSIP (Committee on Uniform Securities Identification Procedures) identifier.
        **FREE ENDPOINT** - Available on free tier (250 calls/day)
        
        Args:
            cusip: CUSIP identifier to search for
            
        Returns:
            Company information matching the CUSIP
            
        Example:
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> result = service.search_cusip('037833100')  # Apple's CUSIP
            >>> print(f"Company: {result[0]['name']}")
        """
        endpoint = "/search-cusip"
        params = {'cusip': cusip}
        return self._make_request(endpoint, params, use_stable=True)
    
    def search_isin(self, isin: str) -> Optional[List[Dict[str, Any]]]:
        """
        Search for companies by ISIN (International Securities Identification Number) identifier.
        **FREE ENDPOINT** - Available on free tier (250 calls/day)
        
        Args:
            isin: ISIN identifier to search for
            
        Returns:
            Company information matching the ISIN
            
        Example:
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> result = service.search_isin('US0378331005')  # Apple's ISIN
            >>> print(f"Company: {result[0]['name']}")
        """
        endpoint = "/search-isin"
        params = {'isin': isin}
        return self._make_request(endpoint, params, use_stable=True)

    def company_screener(self, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
        """
        Basic company screener to get list of companies with basic information.
        **FREE ENDPOINT** - Available on free tier (250 calls/day)
        
        Args:
            limit: Maximum number of results to return
            
        Returns:
            List of companies with basic screening information
            
        Example:
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> companies = service.company_screener(50)
            >>> for company in companies[:10]:
            ...     print(f"{company['symbol']}: {company['companyName']}")
        """
        endpoint = "/company-screener"
        params = {}
        if limit != 100:
            params['limit'] = limit
        return self._make_request(endpoint, params, use_stable=True)

    def search_exchange_variants(self, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """
        Search for exchange variants of a symbol across different exchanges.
        **FREE ENDPOINT** - Available on free tier (250 calls/day)
        
        Args:
            symbol: Stock ticker symbol to search variants for
            
        Returns:
            List of exchange variants for the symbol
            
        Example:
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> variants = service.search_exchange_variants('AAPL')
            >>> for variant in variants:
            ...     print(f"{variant['symbol']} on {variant['exchange']}")
        """
        endpoint = "/search-exchange-variants"
        params = {'symbol': symbol.upper()}
        return self._make_request(endpoint, params, use_stable=True)
    
    def get_historical_price_eod(self, symbol: str, from_date: Optional[str] = None, 
                               to_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get historical end-of-day price data for a stock symbol.
        **FREE ENDPOINT** - Available on free tier (250 calls/day)
        
        Args:
            symbol: Stock ticker symbol
            from_date: Start date (YYYY-MM-DD format, optional)
            to_date: End date (YYYY-MM-DD format, optional)
            
        Returns:
            Historical price data with OHLCV information
            
        Example:
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> prices = service.get_historical_price_eod('AAPL', '2024-01-01')
            >>> for price in prices['historical'][-5:]:  # Last 5 days
            ...     print(f"{price['date']}: ${price['close']:.2f}")
            
        Note:
            This is the same as get_historical_prices but explicitly marked as free tier
        """
        return self.get_historical_prices(symbol, from_date, to_date)
    
    def get_historical_financial_statements_free(self, symbol: str, period: str = "annual", 
                                                limit: int = 5) -> Optional[Dict[str, Any]]:
        """
        Get historical financial statements (income, balance sheet, cash flow) for free tier.
        **FREE ENDPOINT** - Available on free tier (250 calls/day)
        
        Args:
            symbol: Stock ticker symbol
            period: 'annual' or 'quarter'
            limit: Number of periods (limited to 5 for free tier)
            
        Returns:
            Dictionary containing all three financial statements
            
        Example:
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> statements = service.get_historical_financial_statements_free('AAPL')
            >>> income = statements['income_statement']
            >>> balance = statements['balance_sheet']
            >>> cashflow = statements['cash_flow']
        """
        # Limit to 5 periods for free tier
        limit = min(limit, 5)
        
        income_statement = self.get_income_statement(symbol, period, limit)
        balance_sheet = self.get_balance_sheet(symbol, period, limit)
        cash_flow = self.get_cash_flow_statement(symbol, period, limit)
        
        return {
            'symbol': symbol.upper(),
            'period': period,
            'limit': limit,
            'income_statement': income_statement,
            'balance_sheet': balance_sheet,
            'cash_flow_statement': cash_flow
        }
    
    def get_available_indexes(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get list of available market indexes/indices.
        **FREE ENDPOINT** - Available on free tier (250 calls/day)
        
        Returns:
            List of available market indices with symbols and names
            
        Example:
            >>> service = FinancialModelingPrepApiService(credentials)
            >>> indexes = service.get_available_indexes()
            >>> for index in indexes:
            ...     print(f"{index['symbol']}: {index['name']}")
        """
        # Use the existing major indices functionality for free tier
        indices_data = []
        for symbol in self.MAJOR_INDICES:
            quote_data = self.get_quote(symbol)
            if quote_data:
                indices_data.append({
                    'symbol': symbol,
                    'name': quote_data.get('name', f'Index {symbol}'),
                    'price': quote_data.get('price'),
                    'change': quote_data.get('change'),
                    'changesPercentage': quote_data.get('changesPercentage')
                })
        
        return indices_data if indices_data else None
    
    def get_free_tier_summary(self) -> Dict[str, Any]:
        """
        Get a summary of available free tier endpoints and their usage.
        **INFORMATIONAL** - No API call made
        
        Returns:
            Dictionary summarizing free tier capabilities and limits
        """
        return {
            'free_tier_info': {
                'daily_limit': '250 API calls per day',
                'rate_limit': 'No specific rate limit mentioned',
                'plan_type': 'Basic/Stable tier'
            },
            'available_endpoints': {
                'search': [
                    'search_symbol - Search companies by ticker symbol',
                    'search_company_name - Search companies by name',
                    'get_financial_statement_symbol_list - List symbols with financial data',
                    'get_cik_list - Get CIK identifiers',
                    'search_cik - Search by CIK identifier',
                    'search_cusip - Search by CUSIP identifier',
                    'search_isin - Search by ISIN identifier',
                    'company_screener - Basic company screening',
                    'search_exchange_variants - Find symbol variants across exchanges'
                ],
                'metadata': [
                    'get_available_exchanges - List supported exchanges',
                    'get_available_sectors - List available sectors',
                    'get_available_countries - List supported countries'
                ],
                'historical_data': [
                    'get_historical_price_eod - End-of-day historical prices',
                    'get_historical_financial_statements_free - Financial statements (limited)'
                ],
                'market_data': [
                    'get_available_indexes - List of market indices'
                ]
            },
            'limitations': {
                'financial_statements': 'Limited to 5 periods for free tier',
                'historical_data': 'EOD data only, no intraday',
                'real_time': 'Limited real-time data access'
            },
            'upgrade_benefits': [
                'Increased daily API limits',
                'Access to real-time data',
                'Intraday historical data',
                'Advanced endpoints',
                'Faster rate limits'
            ]
        }