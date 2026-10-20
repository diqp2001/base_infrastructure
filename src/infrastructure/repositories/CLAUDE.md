# Repository Layer Architecture

## 📋 Overview

The repository layer provides a clean abstraction between domain entities and database infrastructure, following Domain-Driven Design (DDD) principles and the Repository pattern.

## 🏗️ Architecture Structure

```
src/infrastructure/repositories/
├── base_repository.py                      # Generic base for all repositories
├── financial_asset_base_repository.py      # Base for financial asset repositories
├── local_repo/
│   └── finance/
│       └── financial_assets/
│           ├── share_repository.py         # Share entity repository
│           ├── company_share_repository.py # CompanyShare (inherits from Share)
│           ├── currency_repository.py      # Currency entity repository
│           └── ...                         # Other financial asset repositories
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

## 🔒 Transaction ownership (BI-006)

Local repositories commit after each write and roll back in their own error handlers. A use case that writes
through **several** repositories must wrap them in one transaction:

```python
from src.infrastructure.database.unit_of_work import TransactionAborted, atomic

with atomic(session) as tx:          # the outermost block owns commit / rollback
    order_repo.add(order)            # repository commit() -> flush only
    position_repo.update(position)
    if not ok:
        tx.fail("why")               # -> rollback, TransactionAborted at exit
```

A nested `atomic` joins the outer one; a repository rollback inside the block aborts it; on failure nothing is
stored and the session is clean. Example: `TradeManager._book_atomically` (order + fill + position + cash).
Contract tests: `tests/contracts/test_unit_of_work.py` (SQLite + SQL Server test database).

**Raw vs derived** (`src/infrastructure/database/derived_value_scope.py`): when an operation both fetches raw
observations and writes derived values (a portfolio valuation), wrap it in `derived_values_all_or_nothing(session)`
instead: raw rows commit as they arrive and are kept; on failure the derived (`source = 'calculated'`) rows it
inserted are deleted and those it overwrote restored. Used by `PortfolioService.calculate_value`; tests:
`tests/contracts/test_derived_value_scope.py`.

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

This architecture ensures scalable, maintainable, and testable repository operations while maintaining clean domain-driven design principles.