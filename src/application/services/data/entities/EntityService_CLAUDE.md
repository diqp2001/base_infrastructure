# EntityService Documentation

## Overview
The `EntityService` serves as the primary service layer for creating and managing financial asset domain entities. It acts as a centralized orchestrator that delegates entity operations to the appropriate repositories through the `RepositoryFactory` pattern, following Domain-Driven Design (DDD) principles.

## Core Architecture

### Class: `EntityService`
**File**: `/src/application/services/data/entities/entity_service.py`

```python
class EntityService:
    """Service for creating and managing financial asset domain entities."""
```

### Dependencies
- **DatabaseService**: Database session management
- **RepositoryFactory**: Repository creation and dependency injection
- **Domain Entities**: All financial asset entities (Index, CompanyShare, etc.)
- **Infrastructure Repositories**: Local and IBKR repository implementations

## Key Methods Analysis

### 1. `get_local_repository(entity_class: type)`
**Purpose**: Returns the repository associated with a given domain entity class

**Parameters**:
- `entity_class`: Domain entity class (e.g., `FactorValue`, `CompanyShare`, `Index`)

**Returns**: Repository instance managing that entity

**Implementation Pattern**:
```python
def get_local_repository(self, entity_class: type):
    repo = self.repository_factory.get_local_repository(entity_class)
    if not repo:
        raise ValueError(f"No repository registered for entity class: {entity_class.__name__}")
    return repo
```

**Usage**: Delegates to `RepositoryFactory` for repository lookup and validation

---

### 2. `get_ibkr_repository(entity_class: type)` 
**Purpose**: Returns the IBKR repository for a given entity class

**Parameters**:
- `entity_class`: Domain entity class

**Returns**: IBKR Repository instance or None if no IBKR client available

**Implementation Pattern**:
```python
def get_ibkr_repository(self, entity_class: type):
    return self.repository_factory.get_ibkr_repository(entity_class)
```

**Usage**: Used for entities requiring real-time Interactive Brokers data integration

---

### 3. `_create_or_get(entity_cls, name: str, **kwargs)`
**Purpose**: Generic method to create entity if it doesn't exist or return existing entity

**Parameters**:
- `entity_cls`: Entity class to create/retrieve
- `name`: Entity identifier (symbol, name, etc.)  
- `**kwargs`: Additional entity-specific parameters

**Returns**: Created or existing entity instance

**Implementation Pattern**:
```python
def _create_or_get(self, entity_cls, name: str, **kwargs):
    try:
        repository = self.get_local_repository(entity_cls)
        return repository._create_or_get(entity_cls, name, **kwargs)
    except Exception as e:
        print(f"Error pulling {entity_cls.__name__} with symbol {name}: {e}")
```

**Usage**: Standardized entity creation with deduplication logic

---

### 4. `create_or_get_batch_local(entities_data: List[Dict], entity_cls: type)`
**Purpose**: Bulk creation/retrieval of entities using local repositories

**Parameters**:
- `entities_data`: List of dictionaries containing entity data
- `entity_cls`: Entity class to create/get

**Returns**: List of created/retrieved entities

**Implementation Pattern**:
```python
def create_or_get_batch_local(self, entities_data: List[Dict[str, Any]], entity_cls: type):
    repository = self.get_local_repository(entity_cls)
    results = []
    for entity_data in entities_data:
        entity = repository._create_or_get(entity_cls, **entity_data)
        if entity:
            results.append(entity)
    return results
```

**Usage**: Optimized bulk processing for local database operations

---

### 5. `create_or_get_batch_ibkr(entities_data, entity_cls, what_to_show, duration_str, bar_size_setting)`
**Purpose**: Bulk creation/retrieval using IBKR repositories with market data parameters

**Parameters**:
- `entities_data`: List of entity configurations
- `entity_cls`: Entity class
- `what_to_show`: Data type ("TRADES", "MIDPOINT", "BID", "ASK", etc.)
- `duration_str`: Query duration (format: "integer + space + unit S/D/W")  
- `bar_size_setting`: Bar size ("1 sec" to "1 day")

**Returns**: List of entities with IBKR market data

**Implementation Pattern**:
```python
def create_or_get_batch_ibkr(self, entities_data, entity_cls, what_to_show="TRADES", duration_str="6 M", bar_size_setting="1 day"):
    ibkr_repository = self.get_ibkr_repository(entity_cls)
    if not ibkr_repository:
        return self.create_or_get_batch_local(entities_data, entity_cls)
    
    # Special handling for IndexFutureOption
    if entity_cls.__name__ == 'IndexFutureOption':
        # Handle complex option parameters (symbol, strike_price, expiry, option_type)
        
    return ibkr_repository.get_or_create_batch_optimized(entities_data, what_to_show, duration_str, bar_size_setting)
```

**Usage**: Real-time market data integration with fallback to local processing

---

### 6. `_create_or_get_ibkr(entity_cls, entity_symbol, entity_id, **kwargs)`
**Purpose**: Create/retrieve single entity using IBKR integration

**Parameters**:
- `entity_cls`: Entity class
- `entity_symbol`: Symbol or dict for complex entities (IndexFutureOption)
- `entity_id`: Optional entity ID
- `**kwargs`: Additional parameters

**Returns**: Entity with IBKR data or None if no IBKR client

**Implementation Pattern**:
```python
def _create_or_get_ibkr(self, entity_cls, entity_symbol=None, entity_id=None, **kwargs):
    ibkr_repository = self.get_ibkr_repository(entity_cls)
    if not ibkr_repository:
        return None
        
    # Special handling for IndexFutureOption requiring option parameters
    if entity_cls.__name__ == 'IndexFutureOption':
        if isinstance(entity_symbol, dict):
            # Handle: {'symbol': 'EW4', 'strike_price': 6050.0, 'expiry': '20260320', 'option_type': 'C'}
            entity = ibkr_repository._create_or_get(
                symbol=entity_symbol['symbol'],
                strike_price=float(entity_symbol['strike_price']),
                expiry=entity_symbol['expiry'],
                option_type=entity_symbol['option_type'],
                **kwargs
            )
    else:
        entity = ibkr_repository._create_or_get(entity_symbol, **kwargs)
    
    return entity
```

**Usage**: Real-time entity creation with complex parameter handling

## Integration Patterns

### Repository Factory Integration
- **Delegation**: All repository operations delegate to `RepositoryFactory`
- **Session Management**: Shares database session across all repositories
- **Client Management**: Handles optional IBKR client initialization

### Domain Entity Support
Supports all financial asset entities:
- **Securities**: `CompanyShare`, `Index`, `ETFShare`
- **Derivatives**: `IndexFuture`, `IndexFutureOption`, `Bond`
- **Cash & Commodities**: `Cash`, `Currency`, `Commodity`
- **Factors**: All factor types (`IndexFactor`, `CompanyShareFactor`, etc.)

### Error Handling
- **Graceful Degradation**: Falls back from IBKR to local operations
- **Logging**: Comprehensive error logging with context
- **Validation**: Parameter validation before repository operations

## Usage Examples

### Basic Entity Creation
```python
entity_service = EntityService()

# Create/get index entity
spx_index = entity_service._create_or_get(
    entity_cls=Index,
    name="SPX",
    index_type="Stock",
    currency="USD"
)
```

### Batch Processing
```python
# Bulk local entity creation
entities_data = [
    {"symbol": "SPX", "index_type": "Stock"},
    {"symbol": "NASDAQ", "index_type": "Stock"}
]
indices = entity_service.create_or_get_batch_local(entities_data, Index)

# Bulk IBKR integration with market data
indices_with_data = entity_service.create_or_get_batch_ibkr(
    entities_data, Index, 
    what_to_show="TRADES", 
    duration_str="6 M", 
    bar_size_setting="1 day"
)
```

### Complex Options Handling
```python
# IndexFutureOption with complex parameters
option_config = {
    'symbol': 'EW4',
    'strike_price': 6050.0,
    'expiry': '20260320', 
    'option_type': 'C'
}
option_entity = entity_service._create_or_get_ibkr(
    entity_cls=IndexFutureOption,
    entity_symbol=option_config
)
```

## Design Principles

### Single Responsibility
- **Entity Management**: Focused solely on entity lifecycle operations
- **Repository Coordination**: Coordinates but doesn't implement repository logic
- **Service Layer**: Bridges application needs with infrastructure capabilities

### Dependency Inversion
- **Abstract Dependencies**: Depends on repository interfaces, not implementations
- **Factory Pattern**: Uses `RepositoryFactory` for dependency injection
- **Configurable**: Supports different database types and optional IBKR integration

### Domain-Driven Design
- **Domain Focus**: Operates on domain entities, not database models
- **Bounded Context**: Clear separation between application and infrastructure layers
- **Ubiquitous Language**: Uses financial domain terminology consistently

## Performance Considerations

### Batch Optimization
- **Bulk Operations**: Optimized batch methods for large-scale processing
- **Connection Reuse**: Shares database sessions and IBKR connections
- **Fallback Strategy**: Graceful degradation from IBKR to local operations

### Caching Strategy
- **Repository Caching**: Leverages repository-level caching
- **Session Persistence**: Maintains database sessions for transaction efficiency
- **Client Connection**: Reuses IBKR client connections when available

## Testing Considerations

### Mock Support
- **Repository Mocking**: Can inject mock repositories via `RepositoryFactory`
- **IBKR Client Mocking**: Supports mock IBKR clients for testing
- **Database Independence**: Can use in-memory SQLite for testing

### Integration Testing
- **Real Database Testing**: Supports testing against real database instances
- **IBKR Integration Testing**: Can test with live IBKR connections (with care)
- **Batch Processing Testing**: Validates bulk operation behavior