# MarketDataService Documentation

## Overview
The `MarketDataService` serves as the primary market data provider for the trading engine, handling data slice creation for both real-time and backtest scenarios. It orchestrates market data retrieval, entity creation, and point-in-time data access through the `EntityService` layer.

## Core Architecture

### Class: `MarketDataService`
**File**: `/src/application/services/misbuffet/data/market_data_service.py`

```python
class MarketDataService:
    """
    Main market data service that provides data slices to the trading engine.
    Handles slice creation for both real-time and backtest scenarios.
    """
```

### Dependencies
- **EntityService**: Entity creation and management
- **Factor System**: Factor entities and factor value management
- **Trading Infrastructure**: `Slice`, `TradeBar`, `Symbol` classes
- **Pandas**: Data manipulation and analysis
- **Logging**: Comprehensive error tracking

### Key Properties
```python
def __init__(self, entity_service: EntityService):
    self.entity_service = entity_service
    self.logger = logging.getLogger(self.__class__.__name__)
    
    # Performance caching
    self._last_time = None
    self._data_cache = {}
    
    # Event callbacks
    self.on_data_slice: Optional[Callable[[Slice], None]] = None
    self.on_error: Optional[Callable[[str], None]] = None
```

## Key Methods Analysis

### 1. `create_data_slice(current_date: datetime, universe: List[str]) -> Slice`
**Purpose**: Creates a data slice for the given date and universe - the main method called by the trading engine

**Parameters**:
- `current_date`: The date/time for this slice
- `universe`: Dictionary of entity classes mapping to lists of tickers/symbols

**Returns**: `Slice` containing market data for the specified time

**Implementation Pattern**:
```python
def create_data_slice(self, current_date: datetime, universe: Dict[str, List[str]]) -> Slice:
    # Validate trading day
    if self._is_valid_trading_day(current_date):
        slice_data = Slice(time=current_date)
        
        # Process each entity class and its entities
        for entity_class, entities in universe.items():
            for entity in entities:
                try:
                    # Get point-in-time data
                    point_in_time_data = self._get_point_in_time_data(
                        entity, entity_class, current_date
                    )
                    
                    if point_in_time_data is not None and not point_in_time_data.empty:
                        # Create Symbol and TradeBar objects
                        symbol = Symbol.create_equity(entity)
                        latest_data = point_in_time_data.iloc[-1]
                        
                        trade_bar = TradeBar(
                            symbol=symbol,
                            time=current_date,
                            end_time=current_date,
                            open=float(latest_data.get('Open', latest_data.get('open', 0.0))),
                            high=float(latest_data.get('High', latest_data.get('high', 0.0))),
                            low=float(latest_data.get('Low', latest_data.get('low', 0.0))),
                            close=float(latest_data.get('Close', latest_data.get('close', 0.0))),
                            volume=int(latest_data.get('Volume', latest_data.get('volume', 0)))
                        )
                        
                        slice_data.bars[symbol] = trade_bar
                        
                except Exception as e:
                    self.logger.debug(f"Error creating data slice for {symbol}: {e}")
                    
        return slice_data
```

**Usage**: Called by trading algorithms to get market data at specific time points

---

### 2. `_get_point_in_time_data(ticker: str, entity_class: object, point_in_time: datetime) -> Optional[pd.DataFrame]`
**Purpose**: Retrieves point-in-time data for a specific ticker and date using the factor system

**Parameters**:
- `ticker`: Security ticker/symbol
- `entity_class`: Domain entity class for the ticker  
- `point_in_time`: Specific datetime for data retrieval

**Returns**: DataFrame with OHLCV data or None if unavailable

**Implementation Pattern**:
```python
def _get_point_in_time_data(self, ticker: str, entity_class: object, point_in_time: datetime) -> Optional[pd.DataFrame]:
    try:
        # Get entity using entity service
        entity = self._get_entity_by_ticker(ticker, entity_class)
        if not entity:
            return None
        
        # Define required factor names
        factor_names = ['high', 'open', 'low', 'close', 'volume']
        factor_data = {}
        
        # Check IBKR connection availability
        if self.entity_service.repository_factory.ibkr_client.ib_connection.connected_flag:
            # IBKR processing path
            entity_factor_class_input = ENTITY_FACTOR_MAPPING[entity.__class__][0]
            
            # Batch create/get factors
            factors_data = []
            for factor_name in factor_names:
                factors_data.append({
                    'entity_symbol': factor_name,
                    'group': 'price',
                    'entity_cls': entity_factor_class_input
                })
            
            # Use batch IBKR method with real-time parameters
            created_factors = self.entity_service.create_or_get_batch_ibkr(
                factors_data, entity_factor_class_input,
                what_to_show="TRADES",
                duration_str="1 D", 
                bar_size_setting="5 mins"
            )
            
            # Batch create/get factor values
            factor_values_data = []
            for factor in created_factors:
                factor_values_data.append({
                    'factor': factor,
                    'financial_asset_entity': entity,
                    'entity_id': entity.id,
                    'time_date': point_in_time.strftime("%Y-%m-%d %H:%M:%S")
                })
            
            factor_values = self.entity_service.create_or_get_batch_ibkr(
                factor_values_data, FactorValue,
                what_to_show="TRADES",
                duration_str="6 M",
                bar_size_setting="1 day"
            )
            
        else:
            # Local processing path
            # Similar batch processing but using local repositories
            created_factors = self.entity_service.create_or_get_batch_local(factors_data, entity_factor_class_input)
            factor_values = self.entity_service.create_or_get_batch_local(factor_values_data, FactorValue)
        
        # Build factor_data dictionary from results
        for factor_value in factor_values:
            for factor in created_factors:
                if factor.id == factor_value.factor_id:
                    factor_data[factor.name] = float(factor_value.value)
                    break
        
        # Create DataFrame
        if factor_data:
            factor_data['Date'] = point_in_time
            return pd.DataFrame([factor_data])
        
        return None
        
    except Exception as e:
        self.logger.debug(f"Error getting point-in-time data for {ticker}: {e}")
        return None
```

**Usage**: Core data retrieval method leveraging the factor system for historical and real-time data

---

### 3. `_create_or_get(entity_config: Dict[str, Any]) -> Optional[Any]`
**Purpose**: Creates or retrieves entities using the EntityService with comprehensive error handling

**Parameters**:
- `entity_config`: Dictionary containing entity configuration:
  - `entity_class`: Entity class to create/get
  - `entity_symbol`: Entity symbol/identifier
  - Additional parameters for complex entities (strike_price, expiry, option_type for options)

**Returns**: Entity if created/retrieved successfully, None otherwise

**Implementation Pattern**:
```python
def _create_or_get(self, entity_config: Dict[str, Any]) -> Optional[Any]:
    try:
        entity_class = entity_config.get('entity_class')
        entity_symbol = entity_config.get('entity_symbol')
        
        if not entity_class or not entity_symbol:
            self.logger.warning("entity_class and entity_symbol are required")
            return None
        
        # Special handling for IndexFutureOption
        if entity_class.__name__ == 'IndexFutureOption':
            strike_price = entity_config.get('strike_price')
            expiry = entity_config.get('expiry')
            option_type = entity_config.get('option_type')
            
            if not all([strike_price, expiry, option_type]):
                self.logger.warning(f"IndexFutureOption requires strike_price, expiry, and option_type")
                return None
            
            # Try IBKR repository first
            if hasattr(self.entity_service, 'repository_factory'):
                ibkr_repo = getattr(self.entity_service.repository_factory, 'index_future_option_ibkr_repo', None)
                if ibkr_repo:
                    entity = ibkr_repo._create_or_get(
                        symbol=entity_symbol,
                        strike_price=float(strike_price),
                        expiry=expiry,
                        option_type=option_type
                    )
                    if entity:
                        return entity
                
                # Fallback to local repository
                local_repo = getattr(self.entity_service.repository_factory, 'index_future_option_local_repo', None)
                if local_repo:
                    entity = local_repo._create_or_get(
                        symbol=entity_symbol,
                        strike_price=float(strike_price),
                        expiry=expiry,
                        option_type=option_type
                    )
                    return entity
            
            return None
        
        # Standard entity creation
        kwargs = {k: v for k, v in entity_config.items() if k not in ['entity_class', 'entity_symbol']}
        entity = self.entity_service._create_or_get(
            entity_cls=entity_class, 
            **kwargs
        )
        
        return entity
        
    except Exception as e:
        self.logger.error(f"Error in MarketDataService._create_or_get: {e}")
        return None
```

**Usage**: Provides entity creation functionality with complex parameter handling for options and derivatives

## Supporting Methods

### Trading Day Validation
```python
def _is_valid_trading_day(self, date: datetime) -> bool:
    """Check if a given date is a valid trading day."""
    # Skip weekends
    if date.weekday() >= 5:  # Saturday = 5, Sunday = 6
        return False
        
    # Basic US holidays check
    month, day = date.month, date.day
    
    # New Year's Day, Independence Day, Christmas
    if (month == 1 and day == 1) or \
       (month == 7 and day == 4) or \
       (month == 12 and day == 25):
        return False
        
    return True
```

### Entity Retrieval
```python
def _get_entity_by_ticker(self, ticker: str, entity_class=None):
    """Get entity by ticker using the entity service."""
    try:
        # Check IBKR client availability
        if hasattr(self.entity_service, 'repository_factory') and \
           hasattr(self.entity_service.repository_factory, 'ibkr_client') and \
           self.entity_service.repository_factory.ibkr_client:
            # Use IBKR method
            entity = self.entity_service._create_or_get_ibkr(
                entity_cls=entity_class, 
                entity_symbol=ticker
            )
        else:
            # Use local method
            entity = self.entity_service._create_or_get(
                entity_class, 
                ticker
            )
        return entity
    except Exception as e:
        self.logger.debug(f"Error getting entity for ticker {ticker}: {e}")
        return None
```

### Time Management
```python
def set_time(self, current_time: datetime):
    """Set the current time for the data service."""
    if self._last_time and current_time < self._last_time:
        raise ValueError(f"Cannot go backwards in time: {current_time} < {self._last_time}")
    self._last_time = current_time
```

## Integration Patterns

### EntityService Integration
- **Entity Management**: Delegates all entity operations to EntityService
- **Repository Access**: Leverages EntityService's repository factory pattern
- **Batch Processing**: Uses EntityService batch methods for performance

### Factor System Integration  
- **Factor Creation**: Creates price factors (high, open, low, close, volume) automatically
- **Factor Values**: Manages factor values with point-in-time semantics
- **Entity-Factor Mapping**: Uses `ENTITY_FACTOR_MAPPING` for type relationships

### Trading Engine Integration
- **Slice Creation**: Primary interface for trading algorithms
- **Symbol Management**: Creates proper Symbol objects for trading system
- **TradeBar Construction**: Builds standardized OHLCV bars

## Data Sources

### IBKR Integration
- **Real-time Data**: Direct integration with Interactive Brokers API
- **Historical Data**: Retrieves historical bars with configurable timeframes
- **Market Data Parameters**:
  - `what_to_show`: "TRADES", "MIDPOINT", "BID", "ASK", etc.
  - `duration_str`: "1 D", "6 M", "1 Y", etc.
  - `bar_size_setting`: "5 mins", "1 day", etc.

### Local Data Processing
- **Fallback Strategy**: Graceful degradation when IBKR unavailable
- **Batch Optimization**: Efficient local database operations
- **Caching Layer**: Performance optimization for repeated queries

## Performance Considerations

### Batch Processing
- **Factor Batch Creation**: Creates multiple factors in single operation
- **Value Batch Retrieval**: Optimized factor value queries
- **Connection Reuse**: Shares IBKR connections and database sessions

### Caching Strategy
- **Time-based Caching**: `_last_time` for time progression validation
- **Data Caching**: `_data_cache` for performance optimization
- **Entity Caching**: Leverages EntityService repository caching

### Trading Day Optimization
- **Early Exit**: Skips processing for non-trading days
- **Holiday Calendar**: Basic holiday checking (expandable)
- **Weekend Filtering**: Automatic weekend exclusion

## Event-Driven Architecture

### Callback Support
```python
# Event callbacks
self.on_data_slice: Optional[Callable[[Slice], None]] = None
self.on_error: Optional[Callable[[str], None]] = None

# Usage in create_data_slice
if self.on_data_slice:
    self.on_data_slice(slice_data)
    
if self.on_error:
    self.on_error(f"Error getting data for {symbol}: {str(e)}")
```

### Real-time Processing
- **Time Progression**: Enforces forward time movement
- **Streaming Support**: Callback architecture for real-time data
- **Error Propagation**: Comprehensive error handling with callbacks

## Usage Examples

### Basic Data Slice Creation
```python
market_data_service = MarketDataService(entity_service)

universe = {
    'CompanyShare': ['AAPL', 'MSFT', 'GOOGL'],
    'Index': ['SPX', 'NASDAQ']
}

current_date = datetime.now()
data_slice = market_data_service.create_data_slice(current_date, universe)

# Access trade bars
for symbol, trade_bar in data_slice.bars.items():
    print(f"{symbol}: O={trade_bar.open}, C={trade_bar.close}")
```

### Complex Entity Creation
```python
# IndexFutureOption configuration
option_config = {
    'entity_class': IndexFutureOption,
    'entity_symbol': 'EW4',
    'strike_price': 6050.0,
    'expiry': '20260320',
    'option_type': 'C'
}

option_entity = market_data_service._create_or_get(option_config)
```

### Event-driven Processing
```python
def on_new_data(slice_data):
    print(f"New data slice: {len(slice_data.bars)} symbols")

def on_data_error(error_msg):
    print(f"Data error: {error_msg}")

market_data_service.on_data_slice = on_new_data
market_data_service.on_error = on_data_error
```

## Design Principles

### Separation of Concerns
- **Data Orchestration**: Coordinates data retrieval, doesn't implement storage
- **Entity Delegation**: Delegates entity operations to EntityService
- **Trading Integration**: Bridges market data and trading system needs

### Resilience
- **Graceful Degradation**: Falls back from IBKR to local data
- **Error Isolation**: Continues processing other entities on individual errors
- **Connection Management**: Handles IBKR connection availability

### Performance
- **Batch Operations**: Minimizes database and API calls
- **Caching Strategy**: Intelligent caching for repeated requests
- **Trading Day Filtering**: Avoids unnecessary processing on non-trading days

## Testing Considerations

### Mock Support
- **EntityService Mocking**: Can inject mock EntityService
- **IBKR Client Mocking**: Supports mock IBKR connections
- **Callback Testing**: Event-driven architecture supports test callbacks

### Integration Testing
- **End-to-End Testing**: Test complete data slice creation
- **IBKR Integration**: Test with live IBKR connections (with caution)
- **Performance Testing**: Validate batch processing performance