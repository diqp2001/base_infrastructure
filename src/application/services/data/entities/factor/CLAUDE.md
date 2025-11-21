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

---

## 📁 Directory Structure

```
factor/
├── CLAUDE.md                           # This documentation file
├── factor_creation_service.py          # Factor definition creation/storage
├── factor_calculation_service.py       # Factor value calculation/storage
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

### 2. **Elimination of Duplication** 
- Removed duplicate `create_*_factor()` methods from FactorCalculationService
- Centralized factor creation logic in FactorCreationService

### 3. **Clear Interface Contracts**
- Creation service returns persisted Factor entities
- Calculation service returns computation results and statistics

### 4. **Enhanced Maintainability**
- Easier to modify factor creation logic without affecting calculations
- Easier to add new calculation methods without touching factor definitions

### 5. **Standardized Patterns**
- Both services follow the same `_create_or_get_*()` pattern as BaseFactorRepository
- Consistent error handling and logging across services

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