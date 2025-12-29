"""
Interactive Brokers Service Module

This module provides comprehensive access to Interactive Brokers API services,
including futures data, market data, and trading capabilities.
"""

# Import main service classes
# Note: InteractiveBrokersApiService is deprecated - use misbuffet broker instead
from .interactive_brokers_api_service import InteractiveBrokersApiService
from .get_futures_data_service import (
    IBKRFuturesDataService,
    IBKRFuturesServiceResult,
    FuturesMarketData,
    create_ibkr_futures_service
)
from .config_futures_service import (
    IBKRFuturesServiceConfig,
    get_major_indices_config,
    get_treasury_futures_config,
    get_commodities_config,
    get_volatility_config,
    get_minimal_config
)

# Import recommended misbuffet broker
from application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker

__all__ = [
    # Core API service (deprecated - use InteractiveBrokersBroker instead)
    'InteractiveBrokersApiService',
    
    # Recommended misbuffet broker
    'InteractiveBrokersBroker',
    
    # Futures service
    'IBKRFuturesDataService',
    'IBKRFuturesServiceResult',
    'FuturesMarketData',
    'create_ibkr_futures_service',
    
    # Configuration
    'IBKRFuturesServiceConfig',
    'get_major_indices_config',
    'get_treasury_futures_config',
    'get_commodities_config',
    'get_volatility_config',
    'get_minimal_config'
]