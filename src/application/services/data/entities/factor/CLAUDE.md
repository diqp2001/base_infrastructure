# Factor Services - CLAUDE.md

## 📖 Overview

This directory contains application services responsible for factor management in the base_infrastructure project. Following Domain-Driven Design principles, these services provide clear separation of concerns between factor creation and factor calculation.

---

## 🏗️ Service Architecture

The factor services follow the **Application Service** pattern with clear separation of responsibilities:

### **FactorCreationService** 
- **Responsibility**: Factor entity creation and database persistence
- **File**: `factor_creation_service.py`
- **Purpose**: Create factor definitions and store them in the database

### **FactorCalculationService**
- **Responsibility**: Factor value calculation and storage  
- **File**: `factor_calculation_service.py`
- **Purpose**: Calculate factor values using existing factors and store computed results

### **FactorDataService** 
- **Responsibility**: All factor data retrieval and storage operations
- **File**: `factor_data_service.py`
- **Purpose**: Replace direct repository calls with service layer abstraction

---

## 📁 Directory Structure

```
factor/
├── CLAUDE.md                           # This documentation file
├── factor_creation_service.py          # Factor definition creation/storage
├── factor_calculation_service.py       # Factor value calculation/storage
├── factor_data_service.py              # Factor data operations service
└── __init__.py
```

---

## 🔧 Service Responsibilities

### 1. FactorCreationService

**Primary Functions**:
- Create factor domain entities (ShareMomentumFactor, ShareTechnicalFactor, etc.)
- Persist factor definitions to database using repositories
- Retrieve existing factors by name or ID
- Provide factory methods for different factor types
- Follow standardized `get_or_create_factor()` pattern

**Key Methods**:
```python
# Factor Creation Methods
create_share_momentum_factor(name, period, group, ...)
create_share_technical_factor(name, indicator_type, period, ...)
create_share_volatility_factor(name, volatility_type, period, ...)
create_share_target_factor(name, target_type, forecast_horizon, ...)

# Persistence Methods  
persist_factor(factor: Factor) -> Optional[Factor]
get_or_create_factor(config: Dict[str, Any]) -> Optional[Factor]

# Retrieval Methods
pull_factor_by_id(factor_id: int) -> Optional[Factor]
pull_factor_by_name(name: str) -> Optional[Factor]
```

**Usage Pattern**:
```python
# Create service
creation_service = FactorCreationService(database_service)

# Create momentum factor definition
factor_config = {
    'factor_type': 'share_momentum',
    'name': 'momentum_20d',
    'period': 20,
    'group': 'momentum',
    'subgroup': 'price'
}

# Get or create factor in database
factor = creation_service.get_or_create_factor(factor_config)
print(f"Factor ID: {factor.id}")
```

### 2. FactorCalculationService

**Primary Functions**:
- Calculate factor values using domain logic
- Extract price data from database automatically
- Store calculated values with proper error handling
- Support multiple factor types (momentum, technical, volatility)
- Provide bulk calculation capabilities

**Key Methods**:
```python
# Core Calculation Methods
calculate_and_store_momentum(factor, entity_id, entity_type, ticker=None, overwrite=False)
calculate_and_store_technical(factor, entity_id, entity_type, ticker=None, overwrite=False)
calculate_and_store_volatility(factor, entity_id, entity_type, ticker=None, overwrite=False)

# Generic Calculation
calculate_and_store_factor(factor, entity_id, entity_type, data, overwrite=False)

# Bulk Operations
bulk_calculate_and_store(calculations: List[Dict], overwrite=False)
```

**Usage Pattern**:
```python
# Create service
calc_service = FactorCalculationService(database_service)

# Calculate momentum values (extracts price data automatically)
results = calc_service.calculate_and_store_momentum(
    factor=momentum_factor,
    entity_id=123,
    entity_type='share',
    ticker='AAPL',
    overwrite=False
)

print(f"Stored {results['stored_values']} momentum values")
```

### 3. FactorDataService

**Primary Functions**:
- Replace all direct repository calls from managers
- Provide unified data access layer for factor operations
- Handle company share retrieval by ticker
- Manage factor creation/retrieval operations
- Store and retrieve factor values with proper error handling
- Load price data from database with standardized format

**Key Methods**:
```python
# Company Share Operations
get_company_share_by_ticker(ticker: str) -> Optional[CompanyShare]
get_company_shares_by_tickers(tickers: List[str]) -> Dict[str, Optional[CompanyShare]]

# Factor Operations  
create_or_get_factor(name, group, subgroup, data_type, source, definition) -> Optional[Factor]
get_factor_by_name(name: str) -> Optional[Factor]
get_factors_by_groups(groups: List[str]) -> List[Factor]

# Factor Value Operations
store_factor_values(factor, share, data, column, overwrite=False) -> int
get_factor_values(factor_id, entity_id, start_date=None, end_date=None) -> List
get_factor_values_df(factor_id: int, entity_id: int) -> pd.DataFrame

# Bulk Operations  
bulk_store_factor_values(storage_operations: List[Dict[str, Any]]) -> Dict[str, int]

# Data Loading
load_ticker_price_data(ticker: str) -> Optional[pd.DataFrame]
get_ticker_factor_data(ticker, start_date, end_date, factor_groups) -> Optional[pd.DataFrame]
```

**Usage Pattern**:
```python
# Create service
data_service = FactorDataService(database_service)

# Get company share (replaces repository call)
share = data_service.get_company_share_by_ticker('AAPL')

# Create/get factor (replaces repository call)  
factor = data_service.create_or_get_factor(
    name='Close',
    group='price', 
    subgroup='ohlcv',
    data_type='numeric',
    source='market_data',
    definition='Daily closing price'
)

# Store factor values (replaces repository call)
values_stored = data_service.store_factor_values(
    factor=factor,
    share=share, 
    data=price_df,
    column='Close',
    overwrite=False
)
```

---

## 🔄 Service Integration

### Clear Separation Pattern

The services work together but have distinct responsibilities:

```python
class FactorEnginedDataManager:
    def __init__(self, database_service):
        # Clear service separation
        self.factor_creation_service = FactorCreationService(database_service)  # For factor definitions
        self.factor_calculation_service = FactorCalculationService(database_service)  # For factor values
        self.factor_data_service = FactorDataService(database_service)  # For all data operations
    
    def populate_momentum_factors(self, tickers, overwrite=False):
        # Step 1: Create factor definitions using creation service
        for factor_def in momentum_factors:
            factor_config = {...}
            repo_factor = self.factor_creation_service.get_or_create_factor(factor_config)
            
        # Step 2: Calculate values using calculation service  
        for ticker in tickers:
            results = self.factor_calculation_service.calculate_and_store_momentum(
                factor=momentum_factor,
                entity_id=entity_id,
                entity_type='share',
                ticker=ticker,
                overwrite=overwrite
            )
```

### Integration with BacktestRunner

The BacktestRunner uses factor services through the FactorEnginedDataManager:

```python
class BacktestRunner:
    def run_backtest(self, tickers, overwrite=False):
        # Uses both services through factor_manager
        price_summary = self.factor_manager.populate_price_factors(tickers, overwrite)
        momentum_summary = self.factor_manager.populate_momentum_factors(tickers, overwrite) 
        technical_summary = self.factor_manager.populate_technical_indicators(tickers, overwrite)
```

---

## 🎯 Key Benefits

### 1. **Single Responsibility Principle**
- **Creation Service**: Only handles factor definitions and persistence
- **Calculation Service**: Only handles factor value computation and storage
- **Data Service**: Only handles data retrieval and storage operations (replaces direct repository calls)

### 2. **Elimination of Repository Coupling**
- FactorEnginedDataManager no longer directly calls repositories 
- All data operations abstracted through FactorDataService
- Managers only interact with services, following proper DDD layering

### 3. **Clear Interface Contracts**
- Creation service returns persisted Factor entities
- Calculation service returns computation results and statistics  
- Data service provides unified data access abstraction

### 4. **Enhanced Maintainability**
- Easier to modify data access patterns in one central location
- Reduced coupling between managers and infrastructure layer
- Repository changes don't affect manager implementations

### 5. **Standardized Patterns**
- All services follow the same `_create_or_get_*()` pattern as BaseFactorRepository
- Consistent error handling and logging across all service layers
- Uniform approach to data operations throughout the application

---

## 📊 Database Integration

### Factor Definition Flow (Creation Service)
```
1. FactorCreationService.get_or_create_factor(config)
2. Check if factor exists by name
3. If not exists, create new factor entity
4. Persist to database via BaseFactorRepository
5. Return persisted factor with ID
```

### Factor Value Flow (Calculation Service)  
```
1. FactorCalculationService.calculate_and_store_momentum(...)
2. Extract price data from database automatically
3. Apply domain calculation logic (factor.calculate_momentum())
4. Store results via BaseFactorRepository.add_factor_value()
5. Return calculation statistics
```

---

## 🚀 Usage Examples

### Complete Factor Population Flow

```python
from src.application.services.data.entities.factor.factor_creation_service import FactorCreationService
from src.application.services.data.entities.factor.factor_calculation_service import FactorCalculationService

# Initialize services
creation_service = FactorCreationService(database_service)
calculation_service = FactorCalculationService(database_service)

# Step 1: Create factor definition
factor_config = {
    'factor_type': 'share_momentum',
    'name': 'momentum_20d',
    'period': 20,
    'group': 'momentum',
    'subgroup': 'price'
}
momentum_factor = creation_service.get_or_create_factor(factor_config)

# Step 2: Calculate values for entities
for ticker in ['AAPL', 'GOOGL', 'MSFT']:
    entity_id = get_entity_id_for_ticker(ticker)
    results = calculation_service.calculate_and_store_momentum(
        factor=momentum_factor,
        entity_id=entity_id,
        entity_type='share',
        ticker=ticker,
        overwrite=False
    )
    print(f"{ticker}: {results['stored_values']} values calculated")
```

### Factory Pattern for Multiple Factor Types

```python
# Create multiple factor types using creation service
factor_configs = [
    {'factor_type': 'share_momentum', 'name': 'momentum_20d', 'period': 20},
    {'factor_type': 'share_technical', 'name': 'rsi_14', 'indicator_type': 'RSI', 'period': 14},
    {'factor_type': 'share_volatility', 'name': 'vol_30d', 'period': 30}
]

created_factors = []
for config in factor_configs:
    factor = creation_service.get_or_create_factor(config)
    created_factors.append(factor)
    
print(f"Created {len(created_factors)} factor definitions")
```

---

## 🔧 Configuration Integration

### Factor Manager Integration

The FactorEnginedDataManager uses both services seamlessly:

```python
def _create_momentum_factor_definitions(self) -> Dict[str, Any]:
    """Create momentum factor definitions using FactorCreationService."""
    momentum_factors = self.config['FACTORS']['MOMENTUM_FACTORS']
    
    for factor_def in momentum_factors:
        # Use creation service for factor definitions
        factor_config = {
            'factor_type': 'share_momentum',
            'name': factor_def['name'],
            'period': factor_def['period'],
            # ... other config
        }
        repo_factor = self.factor_creation_service.get_or_create_factor(factor_config)
```

---

## 📝 Contributing Guidelines

### Adding New Factor Types

1. **Domain Entity**: Create in `src/domain/entities/factor/`
2. **Creation Method**: Add to FactorCreationService.create_*_factor()
3. **Calculation Method**: Add to FactorCalculationService.calculate_and_store_*()
4. **Config Support**: Update FactorCreationService.create_factor_from_config()
5. **Integration**: Update FactorEnginedDataManager methods

### Code Quality Standards

- **Error Handling**: Return structured error information
- **Type Hints**: Full type annotations for all methods
- **Docstrings**: Comprehensive documentation with examples
- **Testing**: Unit tests for both services separately
- **Logging**: Descriptive messages for debugging

---

## 🔮 Future Enhancements

### Planned Features
- [ ] Caching layer for factor definitions
- [ ] Async calculation support for large datasets
- [ ] Factor dependency graph management
- [ ] Real-time factor value streaming
- [ ] Cross-factor calculation optimizations

### Performance Optimizations
- [ ] Batch factor value insertions
- [ ] Connection pooling improvements  
- [ ] Query optimization for price data extraction
- [ ] Memory usage optimization for large calculations