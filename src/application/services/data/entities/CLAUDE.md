# Entity Data Services

## Overview

The Entity Data Services layer provides specialized, domain-entity-focused services that handle persistence, creation, and management operations for all domain entities in the system. This layer follows Domain-Driven Design (DDD) principles and provides a standardized interface for entity lifecycle management across different entity types.

## Architecture

### Hierarchical Organization
```
src/application/services/data/entities/
├── factor/
│   ├── factor_calculation_service.py    # Factor computation and storage
│   └── factor_creation_service.py       # Factory service for all factor types
├── finance/
│   └── financial_asset_service.py       # Financial instruments and assets
├── geographic/
│   └── geographic_service.py            # Geographic entities (countries, continents)
└── time_series/
    └── time_series_service.py           # Time series data management
```

### Service Categories

Each entity category contains specialized services that:
- **Create entities** using factory patterns with validation
- **Persist entities** using standardized `persist_*` methods
- **Retrieve entities** using standardized `pull_*` methods
- **Manage relationships** between related entities
- **Handle data validation** and type conversion

## Design Patterns

### Standardized Service Interface

All entity services follow the same interface pattern established by the `persist_factor` example:

```python
def persist_entity(self, entity: EntityType) -> Optional[EntityType]:
    """
    Persist an entity to the database.
    
    Args:
        entity: Entity instance to persist
        
    Returns:
        Persisted entity or None if failed
    """
    try:
        return self.repository.add_entity(entity)
    except Exception as e:
        self.logger.error(f"Failed to persist entity: {e}")
        return None

def pull_entity_by_id(self, entity_id: int) -> Optional[EntityType]:
    """
    Retrieve entity by ID.
    
    Args:
        entity_id: Entity identifier
        
    Returns:
        Entity instance or None if not found
    """
    try:
        return self.repository.get_by_id(entity_id)
    except Exception as e:
        self.logger.error(f"Failed to retrieve entity: {e}")
        return None
```

### Factory Pattern Implementation

Each service provides factory methods for entity creation with configuration support:

```python
def create_entity_from_config(self, config: Dict[str, Any]) -> Optional[EntityType]:
    """
    Create entity from configuration dictionary.
    
    Args:
        config: Configuration parameters
        
    Returns:
        Created entity instance or None if failed
    """
    try:
        # Validate configuration
        self._validate_config(config)
        
        # Create entity with proper type conversion
        entity = EntityType(
            name=config['name'],
            value=Decimal(str(config['value'])),
            created_date=self._parse_date(config.get('date'))
        )
        
        return entity
    except Exception as e:
        self.logger.error(f"Failed to create entity: {e}")
        return None
```

### Database Integration Pattern

All services integrate with the centralized DatabaseService:

```python
class EntityService:
    def __init__(self, database_service: DatabaseService):
        self.db_service = database_service
        self.session = database_service.session
        self._init_repositories()
    
    def _init_repositories(self):
        """Initialize repositories with database session."""
        self.entity_repository = EntityRepository(self.session)
```

## Entity Service Categories

### 1. Factor Services (`factor/`)

**Responsibilities:**
- **Factor Creation**: Factory methods for all 11 factor types (Share, Momentum, Technical, etc.)
- **Factor Calculations**: Execute domain calculation methods and store results
- **Factor Persistence**: Standardized persistence for factor entities and values
- **Bulk Operations**: Efficient bulk factor creation and calculation

**Key Features:**
```python
# Factor creation with configuration
factor_service = FactorCreationService(database_service)
momentum_factor = factor_service.create_share_momentum_factor({
    'name': 'AAPL_20_day_momentum',
    'symbol': 'AAPL',
    'period': 20,
    'momentum_type': 'price_change'
})

# Factor calculation and storage
calc_service = FactorCalculationService(database_service, factor_repository)
results = calc_service.calculate_and_store_momentum(
    factor=momentum_factor,
    entity_id=1,
    entity_type='share',
    prices=[100, 102, 98, 105],
    dates=['2024-01-01', '2024-01-02', '2024-01-03', '2024-01-04']
)
```

### 2. Financial Asset Services (`finance/`)

**Responsibilities:**
- **Asset Creation**: Factory methods for 15+ financial instrument types
- **Market Data Integration**: Connect financial assets with market data
- **Corporate Actions**: Handle splits, dividends, and other corporate events
- **Portfolio Integration**: Support for portfolio construction and management

**Key Features:**
```python
# Financial asset creation
asset_service = FinancialAssetService(database_service)

# Create company share
apple_share = asset_service.create_company_share({
    'ticker': 'AAPL',
    'company_name': 'Apple Inc.',
    'exchange': 'NASDAQ',
    'sector': 'Technology',
    'market_cap': 3000000000000
})

# Persist and retrieve
persisted = asset_service.persist_company_share(apple_share)
retrieved = asset_service.pull_company_share_by_ticker('AAPL')
```

### 3. Geographic Services (`geographic/`)

**Responsibilities:**
- **Geographic Entity Creation**: Countries, continents, sectors, industries
- **Geographic Hierarchies**: Manage relationships between geographic entities
- **Localization Support**: Currency, timezone, and regional data
- **Sector Classification**: Industry and sector taxonomy management

**Key Features:**
```python
# Geographic entity creation
geo_service = GeographicService(database_service)

# Create country with full details
usa = geo_service.create_country({
    'name': 'United States',
    'iso_code': 'US',
    'continent': 'North America',
    'currency': 'USD',
    'timezone': 'UTC-5'
})

# Create industry sector
tech_sector = geo_service.create_sector({
    'name': 'Technology',
    'code': 'TECH',
    'description': 'Information Technology Sector'
})
```

### 4. Time Series Services (`time_series/`)

**Responsibilities:**
- **Time Series Creation**: Create different types of time series (Stock, Financial, ML, Dask)
- **Data Validation**: Ensure proper temporal ordering and data quality
- **Resampling Operations**: Handle frequency conversion and aggregation
- **Large Dataset Support**: Efficient processing with Dask integration

**Key Features:**
```python
# Time series creation
ts_service = TimeSeriesService(database_service)

# Create stock time series
stock_ts = ts_service.create_stock_time_series({
    'symbol': 'AAPL',
    'data_type': 'daily_prices',
    'start_date': '2024-01-01',
    'end_date': '2024-12-31',
    'frequency': 'daily'
})

# Create ML time series for model training
ml_ts = ts_service.create_ml_time_series({
    'feature_names': ['price', 'volume', 'volatility'],
    'target_name': 'next_day_return',
    'model_type': 'regression',
    'lookback_window': 30
})
```

## Common Patterns and Utilities

### Configuration-Based Creation

All services support configuration-driven entity creation:

```python
# Standardized configuration format
entity_config = {
    'name': 'Entity Name',
    'type': 'entity_type',
    'parameters': {
        'param1': 'value1',
        'param2': 123
    },
    'metadata': {
        'created_by': 'system',
        'source': 'api'
    }
}

entity = service.create_entity_from_config(entity_config)
```

### Data Validation and Type Conversion

Built-in validation and conversion utilities:

```python
def _validate_config(self, config: Dict[str, Any]) -> None:
    """Validate configuration parameters."""
    required_fields = ['name', 'type']
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required field: {field}")

def _parse_date(self, date_str: str) -> Optional[datetime]:
    """Parse date string with multiple format support."""
    if not date_str:
        return None
    
    formats = ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S', '%m/%d/%Y']
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            continue
    
    raise ValueError(f"Unable to parse date: {date_str}")

def _convert_decimal(self, value: Union[str, int, float]) -> Decimal:
    """Convert numeric value to Decimal for financial precision."""
    return Decimal(str(value))
```

### Error Handling Patterns

Consistent error handling across all services:

```python
def safe_operation(self, operation_func, *args, **kwargs):
    """Execute operation with comprehensive error handling."""
    try:
        return operation_func(*args, **kwargs)
    except ValidationError as e:
        self.logger.warning(f"Validation error: {e}")
        return None
    except DatabaseError as e:
        self.logger.error(f"Database error: {e}")
        return None
    except Exception as e:
        self.logger.error(f"Unexpected error: {e}")
        return None
```

## Usage Patterns

### Service Integration in Applications

```python
class TradingApplication:
    def __init__(self):
        self.db_service = DatabaseService('postgresql')
        
        # Initialize entity services
        self.factor_service = FactorCreationService(self.db_service)
        self.asset_service = FinancialAssetService(self.db_service)
        self.geo_service = GeographicService(self.db_service)
        self.ts_service = TimeSeriesService(self.db_service)
    
    def setup_trading_universe(self):
        """Set up complete trading universe with all entities."""
        
        # Create geographic entities
        us = self.geo_service.create_country({'name': 'USA', 'iso_code': 'US'})
        tech_sector = self.geo_service.create_sector({'name': 'Technology'})
        
        # Create financial assets
        apple = self.asset_service.create_company_share({
            'ticker': 'AAPL',
            'company_name': 'Apple Inc.',
            'sector_id': tech_sector.id,
            'country_id': us.id
        })
        
        # Create factors
        momentum_factor = self.factor_service.create_share_momentum_factor({
            'name': 'AAPL_20d_momentum',
            'symbol': 'AAPL',
            'period': 20
        })
        
        # Create time series
        price_series = self.ts_service.create_stock_time_series({
            'symbol': 'AAPL',
            'data_type': 'daily_ohlc'
        })
        
        return {
            'country': us,
            'sector': tech_sector,
            'asset': apple,
            'factor': momentum_factor,
            'time_series': price_series
        }
```

### Bulk Operations and Performance

```python
def bulk_create_factors(factor_configs: List[Dict]):
    """Create multiple factors efficiently."""
    factor_service = FactorCreationService(database_service)
    
    created_factors = []
    with database_service.session.begin():  # Transaction context
        for config in factor_configs:
            factor = factor_service.create_factor_from_config(config)
            if factor:
                persisted = factor_service.persist_factor(factor)
                if persisted:
                    created_factors.append(persisted)
    
    return created_factors
```

## Testing Strategy

### Unit Testing Entity Services

```python
def test_factor_creation():
    """Test factor creation service."""
    db_service = DatabaseService('sqlite')  # Test database
    factor_service = FactorCreationService(db_service)
    
    config = {
        'name': 'test_momentum_factor',
        'symbol': 'TEST',
        'period': 10,
        'momentum_type': 'price_change'
    }
    
    factor = factor_service.create_share_momentum_factor(config)
    assert factor is not None
    assert factor.name == 'test_momentum_factor'
    assert factor.period == 10
```

### Integration Testing

```python
def test_service_integration():
    """Test integration between entity services."""
    db_service = DatabaseService('sqlite')
    
    # Test cross-service functionality
    geo_service = GeographicService(db_service)
    asset_service = FinancialAssetService(db_service)
    
    # Create country
    country = geo_service.create_country({'name': 'Test Country', 'iso_code': 'TC'})
    persisted_country = geo_service.persist_country(country)
    
    # Use country in asset creation
    asset_config = {
        'ticker': 'TEST',
        'company_name': 'Test Company',
        'country_id': persisted_country.id
    }
    
    asset = asset_service.create_company_share(asset_config)
    assert asset.country_id == persisted_country.id
```

## Best Practices

### Service Design Guidelines

1. **Consistent Interface**: All services implement the same `persist_*` and `pull_*` method signatures
2. **Configuration-Driven**: Support configuration-based entity creation for flexibility
3. **Type Safety**: Use proper type hints and validation throughout
4. **Error Handling**: Comprehensive error handling with meaningful messages
5. **Database Integration**: Leverage centralized DatabaseService for consistency

### Performance Optimization

1. **Batch Operations**: Group related operations in transactions
2. **Lazy Loading**: Load related entities only when needed
3. **Caching**: Cache frequently accessed entities
4. **Connection Pooling**: Use DatabaseService connection pooling
5. **Query Optimization**: Use efficient database queries

### Maintainability

1. **Clear Separation**: Maintain clear boundaries between entity types
2. **Documentation**: Document all public methods and configuration options
3. **Testing**: Comprehensive unit and integration testing
4. **Logging**: Detailed logging for debugging and monitoring
5. **Evolution**: Design for easy addition of new entity types

The Entity Data Services layer provides a robust, scalable foundation for managing all domain entities in the system while maintaining clean architecture principles and providing a consistent developer experience across different entity types.