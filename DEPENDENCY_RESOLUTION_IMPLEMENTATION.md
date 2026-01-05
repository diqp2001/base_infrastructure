# Foreign Key Dependency Cascade Implementation

## Overview
This implementation provides automatic foreign key dependency resolution for repository `_create_or_get` methods. When any repository's `_create_or_get` method is called, all dependent entities (based on foreign keys in the model) automatically have their `_create_or_get` methods called to ensure proper entity hierarchy.

## Architecture

### 1. DependencyResolverMixin
**File**: `src/infrastructure/repositories/dependency_resolver_mixin.py`

Provides the core dependency resolution logic:
- Analyzes model foreign key relationships using SQLAlchemy inspection
- Maps foreign key columns to appropriate repository instances  
- Handles recursive dependency resolution
- Provides fallback strategies for unresolved dependencies

### 2. DependencyRegistry
**File**: `src/infrastructure/repositories/dependency_registry.py`

Central registry that manages all repository dependencies:
- Maintains instances of all repositories
- Maps foreign key relationships to appropriate repositories
- Provides high-level API for entity creation with dependency resolution
- Handles recursive dependency cascading (e.g., Company → Country → Continent)

### 3. Enhanced Repository Methods
Updated existing repositories to support automatic dependency resolution:

#### CompanyShareRepository
- Enhanced `_create_or_get` method with automatic Exchange and Company dependency resolution
- Added `_resolve_exchange_dependency` and `_resolve_company_dependency` methods
- Intelligent exchange detection based on ticker patterns

#### IndexRepository
- Added complete `_create_or_get` method following established patterns
- Support for SPX index creation with proper defaults
- Integration with MarketData service for entity information

#### FutureRepository  
- Added complete `_create_or_get` method for futures contracts
- Support for ES futures creation with SPX underlying
- Proper future type classification (INDEX, COMMODITY, BOND, CURRENCY)

## Foreign Key Dependencies Handled

### CompanyShare Dependencies
```
CompanyShare
├── exchange_id → Exchange → country_id → Country
└── company_id → Company 
    ├── country_id → Country
    └── industry_id → Industry
```

### Company Dependencies
```
Company
├── country_id → Country
└── industry_id → Industry
```

### Exchange Dependencies
```
Exchange
└── country_id → Country
```

## Usage Examples

### Basic Usage with DependencyRegistry
```python
from src.infrastructure.repositories.dependency_registry import DependencyRegistry

# Initialize registry
registry = DependencyRegistry(session)

# Create SPX index with auto-dependency resolution
spx_index = registry.create_or_get_with_dependencies(
    'index',
    symbol='SPX',
    name='S&P 500 Index',
    index_type='Stock',
    currency='USD'
)

# Create ES future with auto-dependency resolution  
es_future = registry.create_or_get_with_dependencies(
    'future',
    symbol='ESZ5',
    contract_name='E-mini S&P 500 December 2025',
    future_type='INDEX',
    underlying_asset='SPX'
)
```

### Direct Repository Usage
```python
from src.infrastructure.repositories.local_repo.finance.financial_assets.company_share_repository import CompanyShareRepository

company_share_repo = CompanyShareRepository(session)

# Create company share with automatic dependency cascade
spx_share = company_share_repo._create_or_get(
    ticker='SPX',
    company_name='Standard & Poor\'s Corporation',
    exchange_name='CBOE',
    country_name='United States',
    industry_name='Financial Services'
)
# This automatically creates:
# 1. Country('United States') if not exists
# 2. Industry('Financial Services') if not exists  
# 3. Company('Standard & Poor\'s Corporation') with proper FKs
# 4. Exchange('CBOE') with proper country FK
# 5. Finally CompanyShare('SPX') with all proper FKs
```

## Benefits

### 1. Automatic Dependency Management
- No need to manually create dependent entities
- Eliminates foreign key constraint violations
- Ensures data consistency across the entire entity hierarchy

### 2. Simplified Entity Creation
- Single method call creates entire dependency tree
- Intelligent defaults based on entity context
- Reduces boilerplate code for entity setup

### 3. Consistency with Existing Patterns
- All repositories maintain existing `_create_or_get` signature patterns
- Backward compatible with existing code
- Follows established repository design patterns

### 4. Intelligent Resolution Strategies
- Context-aware defaults (e.g., CBOE for SPX, NASDAQ for tech stocks)
- Graceful fallback handling for missing information
- Configurable dependency mapping

## Testing

A comprehensive test suite (`test_dependency_resolution.py`) demonstrates:
- SPX Index creation with dependency cascade
- ES Future creation with dependency resolution  
- CompanyShare creation with full dependency tree
- Verification of created dependencies
- Duplicate entity prevention

## Future Enhancements

1. **Configuration-Driven Dependencies**: External configuration for dependency mappings
2. **Circular Dependency Detection**: Prevention of infinite recursion in complex hierarchies
3. **Batch Dependency Resolution**: Optimize for bulk entity creation
4. **Cache-Based Resolution**: Performance optimization for frequently resolved dependencies
5. **MarketData Integration**: Real-time entity information gathering from external APIs

## Files Created/Modified

### New Files
- `src/infrastructure/repositories/dependency_resolver_mixin.py`
- `src/infrastructure/repositories/dependency_registry.py`
- `test_dependency_resolution.py`
- `DEPENDENCY_RESOLUTION_IMPLEMENTATION.md`

### Modified Files  
- `src/infrastructure/repositories/local_repo/finance/financial_assets/company_share_repository.py`
- `src/infrastructure/repositories/local_repo/finance/financial_assets/index_repository.py`
- `src/infrastructure/repositories/local_repo/finance/financial_assets/future_repository.py`
- `src/application/services/data/entities/finance/financial_asset_service.py`

## Integration with SPX Market Making Project

This dependency resolution system directly supports the SPX call spread market making project by:

1. **Automatic SPX Entity Creation**: Creates SPX index and ES futures with proper dependencies
2. **IBKR Integration Ready**: Framework supports MarketData service integration
3. **Factor System Compatible**: All entities created work seamlessly with the factor data system
4. **Algorithm Integration**: Supports the Algorithm.on_data() dependency pattern requested