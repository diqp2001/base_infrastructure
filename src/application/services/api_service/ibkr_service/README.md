# Interactive Brokers Service Module

## Overview

This module provides Interactive Brokers API services for the base_infrastructure project. It has been refactored to use the existing misbuffet broker infrastructure as the foundation, eliminating code duplication and improving maintainability.

## Architecture

### Recommended Implementation: misbuffet Broker

The **recommended approach** is to use the `InteractiveBrokersBroker` from the misbuffet services:

```python
from src.application.services.misbuffet.brokers.interactive_brokers_broker import InteractiveBrokersBroker

# Configuration
config = {
    'host': '127.0.0.1',
    'port': 7497,  # Paper trading
    'client_id': 1,
    'timeout': 60,
    'paper_trading': True,
    'account_id': 'DEFAULT',
    'enable_logging': True
}

# Create broker instance
broker = InteractiveBrokersBroker(config)

# Connect and use
if broker.connect():
    market_data = broker.get_market_data_snapshot(contract)
    historical_data = broker.get_historical_data(contract)
    broker.disconnect()
```

### Futures Service

The `IBKRFuturesDataService` provides specialized futures data handling:

```python
from src.application.services.api_service.ibkr_service import (
    IBKRFuturesDataService, 
    IBKRFuturesServiceConfig,
    InteractiveBrokersBroker
)

# Create futures service
config = IBKRFuturesServiceConfig.get_default_config()
service = IBKRFuturesDataService(session, config)

# Use the service
if service.connect_to_ibkr():
    result = service.fetch_futures_market_data(['ES', 'NQ', 'YM'])
    print(f"Processed {result.contracts_processed} futures contracts")
```

## Key Refactoring Changes

### 1. Eliminated Duplicate Broker Factory

- **Before**: Used separate `create_interactive_brokers_broker()` factory function
- **After**: Directly instantiate `InteractiveBrokersBroker(config)`

### 2. Deprecated Old API Service

- The `InteractiveBrokersApiService` class is now **deprecated**
- Added deprecation warnings to guide users to `InteractiveBrokersBroker`
- Provided migration helper method: `get_recommended_broker()`

### 3. Enhanced Contract Creation

- Futures service now uses the misbuffet broker's `create_stock_contract()` method
- Supports the updated signature: `create_stock_contract(symbol, secType="FUT", exchange="CME")`
- Falls back to direct contract creation if broker unavailable

### 4. Improved Error Handling

- Better integration with misbuffet broker's error handling
- Consistent logging and connection management
- More robust connection retry logic

## Benefits of Refactoring

1. **Eliminated Code Duplication**: Single source of truth for IB API interactions
2. **Better Error Handling**: Leverages proven misbuffet broker error management
3. **Consistent Architecture**: Follows established DDD patterns
4. **Enhanced Maintainability**: Changes to IB API logic only need to be made in one place
5. **Better Testing**: Can test against single broker implementation
6. **Future-Proof**: Easy to extend and modify broker behavior centrally

## Migration Guide

### From InteractiveBrokersApiService

**Old Code:**
```python
from src.application.services.api_service.ibkr_service import InteractiveBrokersApiService

service = InteractiveBrokersApiService("127.0.0.1", 7497, 1)
service.connect_api()
data = service.fetch_market_data("ES", "CME", "USD")
service.disconnect_api()
```

**New Code:**
```python
from src.application.services.api_service.ibkr_service import InteractiveBrokersBroker
from ibapi.contract import Contract

config = {
    'host': '127.0.0.1',
    'port': 7497,
    'client_id': 1,
    'timeout': 60,
    'paper_trading': True
}

broker = InteractiveBrokersBroker(config)
if broker.connect():
    contract = Contract()
    contract.symbol = "ES"
    contract.secType = "FUT"
    contract.exchange = "CME"
    
    data = broker.get_market_data_snapshot(contract)
    broker.disconnect()
```

### From Broker Factory

**Old Code:**
```python
from src.application.services.misbuffet.brokers.broker_factory import create_interactive_brokers_broker

broker = create_interactive_brokers_broker(**config)
```

**New Code:**
```python
from src.application.services.misbuffet.brokers.interactive_brokers_broker import InteractiveBrokersBroker

broker = InteractiveBrokersBroker(config)
```

## Configuration

All services now use the standardized configuration format:

```python
config = {
    'host': '127.0.0.1',           # IB Gateway/TWS host
    'port': 7497,                  # Port (7497=paper, 7496=live)
    'client_id': 1,                # Unique client ID
    'timeout': 60,                 # Connection timeout
    'paper_trading': True,         # Paper trading flag
    'account_id': 'DEFAULT',       # Account ID (auto-detected)
    'enable_logging': True         # Enable detailed logging
}
```

## Testing

The refactored service can be tested using the misbuffet broker's test infrastructure:

```python
# Test connection
assert broker.connect()
assert broker.is_connected()

# Test market data
contract = broker.ib_connection.create_stock_contract("ES", "FUT", "CME")
market_data = broker.get_market_data_snapshot(contract)
assert 'BID' in market_data or 'ASK' in market_data

# Test historical data
historical = broker.get_historical_data(contract, duration_str="1 W")
assert len(historical) > 0

# Cleanup
broker.disconnect()
```

## Future Enhancements

1. **WebSocket Integration**: Add real-time streaming via misbuffet broker
2. **Advanced Order Management**: Leverage misbuffet order tracking
3. **Portfolio Integration**: Connect with existing portfolio management
4. **Risk Management**: Integrate position sizing and risk controls
5. **Multi-Account Support**: Extend for multiple IB accounts

This refactoring positions the IBKR service for better scalability, maintainability, and integration with the broader base_infrastructure ecosystem.