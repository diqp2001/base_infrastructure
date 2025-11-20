# Factor Calculation Services - CLAUDE.md

## 📖 Overview

This directory contains application services responsible for calculating and storing factor values in the database. These services orchestrate domain logic with infrastructure concerns to execute factor calculation use cases.

---

## 🏗️ Architecture

The factor calculation services follow the **Application Service** pattern from Domain-Driven Design:

- **Use Case Orchestration**: Coordinate domain entities and repositories
- **Database Transaction Management**: Handle persistence concerns
- **Domain-Infrastructure Bridge**: Translate between domain objects and database models
- **Standardized Patterns**: Consistent approach across all factor types

---

## 📁 Directory Structure

```
factor/
├── CLAUDE.md                           # This documentation file
├── factor_calculation_service.py       # Core calculation service
├── factor_creation_service.py          # Factor definition creation
└── __init__.py
```

---

## 🆕 Recent Enhancements (2025-11-20)

### ✅ Database-Driven Price Data Extraction

**Problem Solved**: Previously, factor calculations required external price data to be passed as raw `List[float]` parameters. This violated DDD principles and created tight coupling.

**Solution Implemented**: 
- **PriceData Domain Object**: Created standardized domain entity for price data
- **Database Extraction**: Service now extracts price data internally from database
- **Backward Compatibility**: Legacy interface preserved for smooth migration

---

## 🔧 Key Components

### 1. FactorCalculationService

**File**: `factor_calculation_service.py`

**Responsibilities**:
- Calculate momentum, technical, volatility, and target factors
- Extract price data from database using repositories
- Store calculated values with proper error handling
- Maintain calculation history and statistics

#### New Price Data Pattern

**Before** (Deprecated):
```python
# External data preparation required
prices = [100.0, 102.5, 101.8]
dates = [date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3)]

service.calculate_and_store_momentum(
    factor=momentum_factor,
    entity_id=123,
    entity_type='share',
    prices=prices,    # Raw data passed in
    dates=dates,      # Raw data passed in
    overwrite=False
)
```

**After** (Recommended):
```python
# Service extracts data internally from database
service.calculate_and_store_momentum(
    factor=momentum_factor,
    entity_id=123,
    entity_type='share',
    ticker='AAPL',    # Optional ticker for logging
    overwrite=False
)
```

#### Internal Architecture

**Price Data Extraction**:
```python
def _extract_price_data_from_database(self, entity_id: int, ticker: str = None) -> Optional[PriceData]:
    """
    Extract price data from database and create PriceData domain object.
    
    Flow:
    1. Get 'Close' price factor from ShareFactorRepository
    2. Extract factor values as DataFrame
    3. Convert and sort data by date
    4. Create PriceData domain object
    5. Return standardized domain object
    """
```

**Calculation Flow**:
```python
def calculate_and_store_momentum(self, factor, entity_id, entity_type, ticker=None, overwrite=False):
    """
    Enhanced calculation flow:
    1. Extract price data using _extract_price_data_from_database()
    2. Create PriceData domain object with validation
    3. Use PriceData.get_historical_prices() for each calculation point
    4. Apply domain factor.calculate_momentum() method
    5. Store results with proper error handling
    """
```

---

## 📊 Calculation Patterns

### 1. Momentum Factor Calculation
```python
# Domain-driven approach
price_data = self._extract_price_data_from_database(entity_id, ticker)
for i, (date, price) in enumerate(zip(price_data.dates, price_data.prices)):
    historical_prices = price_data.get_historical_prices(i + 1)
    momentum_value = factor.calculate_momentum(historical_prices)
    # Store result...
```

### 2. Generic Factor Calculation
```python
# Support multiple calling patterns
if isinstance(factor, ShareMomentumFactor):
    if isinstance(data, dict) and 'ticker' in data:
        # New database extraction pattern
        return self.calculate_and_store_momentum(factor, entity_id, entity_type, 
                                               ticker=data['ticker'], overwrite=overwrite)
    elif isinstance(data, dict) and 'prices' in data:
        # Legacy compatibility mode
        return self._calculate_momentum_legacy(factor, entity_id, entity_type,
                                             data['prices'], data['dates'], overwrite)
```

---

## 🔗 Integration Points

### Repository Dependencies
- **BaseFactorRepository**: Factor definition and value storage
- **ShareFactorRepository**: Share-specific factor operations
- **CompanyShareRepository**: Entity lookup and validation

### Domain Entity Usage
- **ShareMomentumFactor**: Domain calculation logic
- **PriceData**: Standardized price data container
- **FactorValue**: Calculated result storage

### Database Services
- **DatabaseService**: Transaction management and session handling

---

## 📈 Performance Considerations

### Database Query Optimization
- **Single Query**: Extract all price data at once per entity
- **Sorted Data**: Ensure chronological order for calculations
- **Type Conversion**: Convert to proper numeric types early

### Memory Management
- **Streaming Processing**: Process one calculation point at a time
- **Garbage Collection**: Clear intermediate results appropriately
- **Connection Pooling**: Reuse database connections efficiently

---

## 🎯 Usage Examples

### Basic Momentum Calculation
```python
from src.application.services.data.entities.factor.factor_calculation_service import FactorCalculationService
from src.domain.entities.factor.finance.financial_assets.share_factor.share_momentum_factor import ShareMomentumFactor

# Initialize service
service = FactorCalculationService(database_service)

# Create momentum factor
momentum_factor = ShareMomentumFactor(
    name="momentum_20d",
    period=20,
    group="momentum", 
    subgroup="price"
)

# Calculate and store (new pattern)
results = service.calculate_and_store_momentum(
    factor=momentum_factor,
    entity_id=123,
    entity_type='share',
    ticker='AAPL',
    overwrite=False
)

print(f"Stored {results['stored_values']} momentum values")
```

### Legacy Compatibility
```python
# Still supported for backward compatibility
results = service.calculate_and_store_factor(
    factor=momentum_factor,
    entity_id=123,
    entity_type='share',
    data={'prices': [100.0, 102.5], 'dates': [date(2024, 1, 1), date(2024, 1, 2)]},
    overwrite=False
)
```

---

## 🛠️ Error Handling

### Common Error Scenarios
1. **No Price Data**: Entity has no 'Close' factor values in database
2. **Data Validation**: Inconsistent price/date arrays
3. **Storage Failures**: Database constraints or connection issues
4. **Domain Logic Errors**: Insufficient data for factor calculations

### Error Response Format
```python
{
    'factor_name': 'momentum_20d',
    'factor_id': 42,
    'entity_id': 123,
    'entity_type': 'share',
    'calculations': [],
    'stored_values': 0,
    'skipped_values': 0,
    'errors': ['No price data available in database']
}
```

---

## 🔄 Migration Guide

### From Raw Price Lists to Database Extraction

**Step 1**: Update service calls to use new signature
```python
# Old
service.calculate_and_store_momentum(factor, entity_id, 'share', prices, dates, overwrite)

# New  
service.calculate_and_store_momentum(factor, entity_id, 'share', ticker='AAPL', overwrite=overwrite)
```

**Step 2**: Remove external price data preparation
```python
# Remove this code
factorentityClose = self.share_factor_repository.get_by_name('Close')
df = self.share_factor_repository.get_factor_values_df(factor_id=int(factorentityClose.id), entity_id=company.id)
prices = df["value"].tolist()
dates = df.index.tolist()
```

**Step 3**: Update result handling
```python
# Old
values_stored = len(momentum_results) if momentum_results else 0

# New
values_stored = momentum_results.get('stored_values', 0) if momentum_results else 0
```

---

## 📝 Contributing Guidelines

### Adding New Factor Types
1. **Create Domain Entity**: Implement in `src/domain/entities/factor/`
2. **Add Calculation Method**: Follow `calculate_and_store_momentum` pattern
3. **Update Generic Handler**: Add case to `calculate_and_store_factor`
4. **Write Tests**: Unit tests for domain logic, integration tests for service
5. **Document Usage**: Add examples and patterns to this file

### Code Quality Standards
- **Error Handling**: Always return structured error information
- **Logging**: Use descriptive log messages for debugging
- **Type Hints**: Full type annotations for all method parameters
- **Docstrings**: Comprehensive documentation for all public methods
- **Testing**: Unit tests with >80% coverage