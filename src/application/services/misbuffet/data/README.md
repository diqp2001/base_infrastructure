# Market Data Services - DDD Architecture

This directory contains the Domain-Driven Design (DDD) oriented market data services for the trading engine.

## Folder Structure

```
src/application/services/misbuffet/data/
├── README.md                           # This file
├── __init__.py                         # Package initialization with exports
├── CLAUDE.md                          # Existing documentation
│
├── market_data_service.py             # NEW: Main market data service
├── market_data_history_service.py     # NEW: Historical data with frontier
├── data_loader.py                     # NEW: Service initialization factory
│
├── examples/                          # NEW: Usage examples
│   ├── __init__.py
│   ├── engine_loop_example.py         # Engine usage patterns
│   └── algorithm_usage_example.py     # Algorithm usage patterns
│
└── [existing files...]               # Existing data management files
    ├── data_manager.py
    ├── data_feed.py
    ├── history_provider.py
    └── ...
```

## New DDD Services

### 1. MarketDataService

**Purpose**: Provides real-time and backtest market data slices to the trading engine.

**Key Features**:
- Supports both backtesting (file system) and live trading (broker connection)
- Takes an EntityService to resolve symbols
- Creates and manages MarketDataHistoryService
- Generates data slices for the engine loop
- Enforces time progression (cannot go backwards)

**Usage**:
```python
# Initialize for backtest
market_service = MarketDataService(entity_service)
market_service.initialize_backtest(data_folder, start_time, end_time)

# Add symbols and get slices
market_service.add_symbol(Symbol("AAPL", "USA"))
slice_obj = market_service.get_current_slice()
```

### 2. MarketDataHistoryService

**Purpose**: Provides historical data to algorithms with frontier enforcement to prevent look-ahead bias.

**Key Features**:
- Maintains a time frontier that can only advance forward
- Self-contained (no separate HistoryProvider needed)
- Caches recent history requests for performance
- Supports multiple data resolutions (minute, hourly, daily)
- Works with both file system and database sources

**Usage**:
```python
# Get historical data (respects frontier)
history = history_service.get_history("AAPL", periods=20, resolution=Resolution.DAILY)

# Get data for specific date range
history = history_service.get_history_range("AAPL", start_date, end_date)

# Check frontier constraints
can_access = history_service.can_access_time(some_datetime)
```

### 3. DataLoader

**Purpose**: Factory class that initializes and configures all data services.

**Key Features**:
- Orchestrates initialization of EntityService, MarketDataService, and MarketDataHistoryService
- Supports both backtest and live trading configurations
- Returns a DataServices container with all initialized services
- Handles error scenarios and cleanup

**Usage**:
```python
# Simple backtest setup
services = create_backtest_data_services(
    data_folder="/path/to/data",
    start_time=datetime(2023, 1, 1),
    end_time=datetime(2023, 12, 31)
)

# Advanced configuration
config = DataConfiguration(database_type='postgresql', enable_caching=True)
loader = DataLoader()
services = loader.load_with_config(config, mode='backtest')
```

## Integration with Existing Code

### DataLoader Initialization Flow

1. **EntityService**: Created with DatabaseService for symbol resolution
2. **MarketDataService**: Created with EntityService dependency
3. **MarketDataHistoryService**: Automatically created by MarketDataService
4. **Configuration**: Applied based on backtest vs live trading mode

### Engine Loop Pattern

```python
# Engine gets data slices from MarketDataService
slice_obj = market_data_service.advance_time(current_time)
if slice_obj and slice_obj.has_data:
    for algorithm in algorithms:
        algorithm.on_data(slice_obj)  # Algorithms receive slices
```

### Algorithm Pattern

```python
# Algorithms use MarketDataHistoryService for historical analysis
class MyAlgorithm:
    def __init__(self, history_service):
        self.history = history_service
    
    def on_data(self, slice_obj):
        # Get historical data for analysis
        past_data = self.history.get_history("AAPL", 20)  # 20 periods
        
        # Perform analysis and make trading decisions
        # ...
```

## Frontier Enforcement

The `Frontier` class prevents look-ahead bias by maintaining a time boundary:

```python
# Frontier starts at backtest start time
frontier = Frontier(datetime(2023, 1, 1))

# Can only advance forward
frontier.advance(datetime(2023, 1, 2))  # OK
frontier.advance(datetime(2022, 12, 31))  # Raises ValueError

# Check data access
can_access = frontier.can_access(datetime(2023, 1, 1))  # True
can_access = frontier.can_access(datetime(2023, 1, 3))  # False
```

## Examples

See the `examples/` directory for complete working examples:

- **engine_loop_example.py**: Shows how the trading engine uses MarketDataService
- **algorithm_usage_example.py**: Shows how algorithms use MarketDataHistoryService

## Dependencies

The new services integrate with existing infrastructure:

- **EntityService**: For symbol resolution and entity management
- **DatabaseService**: For data persistence and retrieval
- **Common Data Types**: Uses Slice, BaseData, TradeBar, etc.
- **Symbol**: For symbol representation and management

## Error Handling

All services include comprehensive error handling:

- Graceful degradation when data is unavailable
- Logging and statistics for monitoring
- Proper resource cleanup on disposal
- Validation of time boundaries and data integrity

## Performance Considerations

- **Caching**: History service caches recent requests
- **Lazy Loading**: Data is loaded on demand
- **Resource Management**: Proper disposal of resources
- **Time Complexity**: Efficient frontier checking and data lookup

This design follows DDD principles by:
- Separating concerns between data provision and historical analysis
- Using the EntityService for domain entity resolution
- Maintaining clear boundaries between services
- Providing a clean factory pattern for initialization