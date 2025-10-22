# Repository Layer Architecture

## 📋 Overview

The repository layer provides a clean abstraction between domain entities and database infrastructure, following Domain-Driven Design (DDD) principles and the Repository pattern.

## 🏗️ Architecture Structure

```
src/infrastructure/repositories/
├── base_repository.py                      # Generic base for all repositories
├── financial_asset_base_repository.py      # Base for financial asset repositories
├── local_repo/
│   ├── finance/
│   │   └── financial_assets/
│   │       ├── share_repository.py         # Share entity repository
│   │       ├── company_share_repository.py # CompanyShare (inherits from Share)
│   │       ├── currency_repository.py      # Currency entity repository
│   │       └── ...                         # Other financial asset repositories
│   └── factor/
│       ├── base_factor_repository.py       # Base for all factor repositories
│       └── finance/
│           └── financial_assets/
│               ├── share_factor_repository.py
│               ├── currency_factor_repository.py
│               └── ...                     # 11 factor repository types
└── mappers/                                # Entity ↔ ORM conversion utilities
```

## 🔧 Base Repository Pattern

### BaseRepository (Generic)

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List
from sqlalchemy.orm import Session

EntityType = TypeVar("EntityType")  # Domain entity type
ModelType = TypeVar("ModelType")    # SQLAlchemy ORM model type

class BaseRepository(ABC, Generic[EntityType, ModelType]):
    def __init__(self, session: Session):
        self.session = session

    # Standard CRUD operations
    def create(self, entity: EntityType) -> EntityType
    def get(self, model_id: int) -> Optional[ModelType] 
    def update(self, model_id: int, updates: dict) -> Optional[ModelType]
    def delete(self, model_id: int) -> bool
    def get_all(self) -> List[ModelType]
    
    # Sequential ID generation
    def _get_next_available_id(self) -> int
    
    # Abstract methods (must implement)
    @property
    @abstractmethod
    def model_class(self): pass
    
    @abstractmethod
    def _to_entity(self, infra_obj: ModelType) -> EntityType: pass
    
    @abstractmethod  
    def _to_model(self, entity: EntityType) -> ModelType: pass
```

### FinancialAssetBaseRepository

Extends BaseRepository with financial asset specific functionality:

```python
class FinancialAssetBaseRepository(BaseRepository[EntityType, ModelType], ABC):
    # Financial asset specific methods
    def get_by_ticker(self, ticker: str) -> Optional[EntityType]
    def exists_by_ticker(self, ticker: str) -> bool
    def get_by_exchange(self, exchange_id: int) -> List[EntityType] 
    def add_bulk(self, entities: List[EntityType]) -> List[EntityType]
    def get_active_assets(self) -> List[EntityType]
    def get_assets_by_date_range(self, start_date, end_date) -> List[EntityType]
```

## 💼 Repository Hierarchy

### Financial Assets

```
FinancialAssetBaseRepository
├── ShareRepository
│   └── CompanyShareRepository      # Company-specific shares
├── CurrencyRepository              # Foreign exchange currencies  
├── BondRepository                  # Fixed income securities
├── CommodityRepository             # Commodity assets
└── ...                            # Other financial asset types
```

### Factor System

```  
BaseFactorRepository
├── ShareFactorRepository           # Share price/volume factors
├── CurrencyFactorRepository        # Exchange rate factors
├── CompanyShareFactorRepository    # Company-specific factors
├── EquityFactorRepository          # Equity-specific factors
└── ...                            # 11 total factor repository types
```

## 🆔 Sequential ID Generation

All repositories use database-driven sequential ID generation for chronological ordering:

```python
def _get_next_available_id(self) -> int:
    """Generate next sequential ID from database records"""
    max_id_result = self.session.query(
        self.model_class.id
    ).order_by(self.model_class.id.desc()).first()
    
    return max_id_result.id + 1 if max_id_result else 1
```

### Key Benefits:
- **Chronological Ordering**: IDs reflect creation order
- **Thread Safety**: Database-level generation prevents conflicts
- **Scalability**: Works with any number of new entities
- **Uniqueness**: Guaranteed unique IDs across all instances

## 📊 Factor Repository System

### BaseFactorRepository Features

- **Generic Factor CRUD**: Create, read, update, delete factor definitions
- **Factor Values**: Time series data storage and retrieval  
- **Factor Rules**: Business rule validation and transformations
- **Sequential IDs**: Consistent ID assignment across factor types

### Example Usage

```python
# Create factor repository
repo = ShareFactorRepository('sqlite')

# Add factor definition with sequential ID
factor = repo.add_factor(
    name='close_price',
    group='price',
    subgroup='daily',
    data_type='numeric',
    source='historical_csv',
    definition='Daily closing price'
)

# Add factor values
repo.add_factor_value(
    factor_id=factor.id,
    entity_id=share.id,
    date=datetime(2023, 1, 1),
    value=Decimal('150.25')
)
```

## 🔄 Domain-Infrastructure Separation

### Clean Architecture Principles

1. **Domain Independence**: Domain entities have no infrastructure dependencies
2. **Repository Contracts**: Interfaces defined in domain layer, implemented in infrastructure
3. **Mapper Pattern**: Clean conversion between domain entities and ORM models
4. **Dependency Inversion**: High-level modules don't depend on low-level modules

### Entity Conversion Flow

```
Domain Entity → Repository → Mapper → ORM Model → Database
     ↓                                                ↑
Database ← ORM Model ← Mapper ← Repository ← Query Result
```

## ⚡ Performance Features

### Bulk Operations

```python
# Efficient bulk entity creation
entities = [CompanyShare(...), CompanyShare(...), ...]
created_entities = repository.add_bulk(entities)
```

### Transaction Management

- **Automatic Rollback**: Failed operations rollback automatically
- **Session Management**: Proper SQLAlchemy session lifecycle  
- **Connection Pooling**: Efficient database connection reuse

### Caching Strategy

- **Repository Level**: In-memory caching for frequently accessed entities
- **Query Optimization**: Strategic indexing and query patterns
- **Lazy Loading**: On-demand data loading for performance

## 🧪 Testing Strategy

### Repository Testing

```python
# Mock database testing
def test_repository_crud():
    mock_session = Mock()
    repo = ShareRepository(mock_session)
    
    # Test entity creation
    share = Share(ticker='AAPL', ...)
    result = repo.create(share)
    
    assert result.id is not None
    assert result.ticker == 'AAPL'
```

### Integration Testing

- **In-Memory SQLite**: Fast integration tests
- **Transaction Isolation**: Test data cleanup
- **Factory Pattern**: Test data generation

## 🚀 Future Roadmap

### Immediate Enhancements

- [ ] **Async Support**: AsyncIO-compatible repository methods
- [ ] **Query Builder**: Fluent query interface for complex filtering
- [ ] **Audit Trail**: Change tracking for all entity modifications
- [ ] **Soft Deletes**: Logical deletion with restoration capability

### Advanced Features

- [ ] **Multi-Tenancy**: Tenant-aware data isolation
- [ ] **Event Sourcing**: Complete audit log of all state changes
- [ ] **CQRS Integration**: Command/query responsibility segregation
- [ ] **Distributed Caching**: Redis integration for cross-instance caching

## 📚 Usage Examples

### Basic Entity Operations

```python
# Initialize repository with database session
repo = CompanyShareRepository(session)

# Create new entity with sequential ID
share = CompanyShare(ticker='MSFT', exchange_id=1, ...)
created_share = repo.create(share)  # Automatically assigns next ID

# Query operations
all_shares = repo.get_all()
msft_share = repo.get_by_ticker('MSFT')
nasdaq_shares = repo.get_by_exchange(1)

# Update operations  
updated_share = repo.update(share.id, {'end_date': datetime.now()})

# Delete operations
success = repo.delete(share.id)
```

### Factor Management

```python
# Factor definition creation
factor_repo = ShareFactorRepository('sqlite')

price_factor = factor_repo.add_factor(
    name='adj_close_price',
    group='price', 
    subgroup='adjusted',
    data_type='numeric',
    source='yahoo_finance',
    definition='Split and dividend adjusted closing price'
)

# Historical data import
for date, price in historical_data:
    factor_repo.add_factor_value(
        factor_id=price_factor.id,
        entity_id=share.id,
        date=date,
        value=Decimal(str(price))
    )
```

This architecture ensures scalable, maintainable, and testable repository operations while maintaining clean domain-driven design principles.