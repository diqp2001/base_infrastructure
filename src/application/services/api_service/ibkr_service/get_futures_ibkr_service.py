"""
IBKR Futures Service - Legacy Reference

This file contains reference information for Interactive Brokers futures contracts.
The actual implementation is now in get_futures_data_service.py

Major Futures Contracts Available via IBKR:

Equity Index Futures:
- ES: E-mini S&P 500 Futures (CME)
- MES: Micro E-mini S&P 500 Futures (CME)
- SP: S&P 500 Index Futures (Full-Size) (CME)
- NQ: E-mini Nasdaq-100 Futures (CME)
- MNQ: Micro E-mini Nasdaq-100 Futures (CME)
- ND: Nasdaq-100 Index Futures (Full-Size) (CME)
- YM: E-mini Dow Jones Industrial Average Futures (CBOT)
- DJ: Dow Jones Industrial Average Futures (Full-Size) (CBOT)
- EMD: E-mini S&P MidCap 400 Index Futures (CME)

Volatility Futures:
- VX: Standard VIX Futures (CBOE/CFE)
- VXX: VIX Short-Term Futures ETN

Interest Rate Futures:
- ZT: 2-Year U.S. Treasury Note Futures (CBOT)
- ZF: 5-Year U.S. Treasury Note Futures (CBOT)
- ZN: 10-Year U.S. Treasury Note Futures (CBOT)
- TN: Ultra 10-Year U.S. Treasury Note Futures (CBOT)
- ZB: 30-Year U.S. Treasury Bond Futures (CBOT)
- UB: Ultra 30-Year U.S. Treasury Bond Futures (CBOT)
- FF: 30-Day Fed Funds Futures (CBOT)
- GE: Eurodollar Futures (Deprecated - Use SOFR) (CME)

Commodity Futures:
- CL: Crude Oil Futures (NYMEX)
- NG: Natural Gas Futures (NYMEX)
- GC: Gold Futures (COMEX)
- SI: Silver Futures (COMEX)
- ZW: Wheat Futures (CBOT)
- ZC: Corn Futures (CBOT)
- ZS: Soybeans Futures (CBOT)

Currency Futures:
- 6E: Euro Futures (CME)
- 6J: Japanese Yen Futures (CME)
- 6B: British Pound Futures (CME)
- 6S: Swiss Franc Futures (CME)

Usage:
    from src.application.services.api_service.ibkr_service.get_futures_data_service import IBKRFuturesDataService
    
    # Create service instance
    service = IBKRFuturesDataService(session, config)
    
    # Connect and fetch data
    if service.connect_to_ibkr():
        result = service.fetch_futures_market_data()
"""

# Import the actual service implementation for convenience
from .get_futures_data_service import (
    IBKRFuturesDataService,
    IBKRFuturesServiceResult,
    FuturesMarketData,
    create_ibkr_futures_service
)

# Import configurations
from .config_futures_service import (
    IBKRFuturesServiceConfig,
    get_major_indices_config,
    get_treasury_futures_config,
    get_commodities_config,
    get_volatility_config,
    get_minimal_config
)

__all__ = [
    'IBKRFuturesDataService',
    'IBKRFuturesServiceResult', 
    'FuturesMarketData',
    'create_ibkr_futures_service',
    'IBKRFuturesServiceConfig',
    'get_major_indices_config',
    'get_treasury_futures_config',
    'get_commodities_config',
    'get_volatility_config',
    'get_minimal_config'
]
