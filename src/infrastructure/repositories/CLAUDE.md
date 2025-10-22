# Repository Layer Architecture

## 🏗️ Repository Pattern Implementation

The repository layer provides the interface between domain entities and data persistence infrastructure, following Domain-Driven Design (DDD) principles and CRUD operations patterns.

---

## 📁 Structure Overview

```
src/infrastructure/repositories/
├── local_repo/                     # Local database repositories
│   ├── factor/                     # Factor-related repositories
│   │   ├── base_factor_repository.py    # Abstract base for all factor repos
│   │   └── finance/
│   │       └── financial_assets/         # Financial asset factor repositories
│   │           ├── share_factor_repository.py
│   │           ├── currency_factor_repository.py
│   │           └── [entity]_factor_repository.py
│   └── finance/                    # Financial entity repositories
│       └── financial_assets/       # Financial asset repositories
│           ├── company_share_repository.py
│           ├── share_repository.py
│           └── [entity]_repository.py
└── mappers/                        # Domain-to-ORM conversion utilities
    ├── factor/                     # Factor mappers
    └── finance/                    # Financial entity mappers
```

---

## 🎯 Standard Repository Pattern

All repositories follow this consistent CRUD structure:

```python
class StandardRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, entity: DomainEntity) -> DomainEntity:
        """Create new entity in database"""
        pass

    def get_by_id(self, entity_id: int) -> Optional[DomainEntity]:
        """Retrieve entity by ID"""
        pass

    def update(self, entity_id: int, updates: dict) -> Optional[DomainEntity]:
        """Update entity with new data"""
        pass

    def delete(self, entity_id: int) -> bool:
        """Delete entity by ID"""
        pass

    def _to_entity(self, infra_obj: ORMModel) -> DomainEntity:
        """Convert ORM model to domain entity"""
        pass
```

---

## 🔢 ID Generation Strategy

### Sequential Database IDs
All repositories implement sequential ID generation for consistent entity ordering:

**Company Share Repository:**
```python
def _get_next_available_company_share_id(self) -> int:
    """Returns next sequential ID for company share creation"""
    max_id_result = self.session.query(CompanyShareModel.id).order_by(CompanyShareModel.id.desc()).first()
    return max_id_result[0] + 1 if max_id_result else 1
```

**Factor Repositories:**
```python
def _get_next_available_factor_id(self) -> int:
    """Returns next sequential ID for factor creation"""
    FactorModel = self.get_factor_model()
    max_id_result = self.session.query(FactorModel.id).order_by(FactorModel.id.desc()).first()
    return max_id_result[0] + 1 if max_id_result else 1
```

### Benefits:
- **Chronological Ordering**: IDs assigned in order of creation
- **Uniqueness**: Database-level auto-increment ensures no conflicts
- **Scalability**: Works with any number of new entities
- **Thread Safety**: Database handles concurrent ID generation

---

## 📊 Factor Repository Architecture

### BaseFactorRepository (Abstract)
Central abstract class providing common functionality for all factor types:

```python
class BaseFactorRepository(ABC):
    def __init__(self, db_type: str = 'sqlite'):
        self.database_manager = DatabaseManager(db_type)
        self.session = self.database_manager.session

    # Abstract methods for concrete implementations
    @abstractmethod
    def get_factor_model(self): pass
    @abstractmethod  
    def get_factor_value_model(self): pass
    @abstractmethod
    def get_factor_rule_model(self): pass

    # CRUD operations for factors
    def create_factor(self, domain_factor: FactorEntity) -> Optional[FactorEntity]
    def get_by_name(self, name: str) -> Optional[FactorEntity]
    def get_by_id(self, factor_id: int) -> Optional[FactorEntity]
    def list_all(self) -> List[FactorEntity]
    def update_factor(self, factor_id: int, **kwargs) -> Optional[FactorEntity]
    def delete_factor(self, factor_id: int) -> bool

    # CRUD operations for factor values  
    def create_factor_value(self, domain_value: FactorValueEntity) -> Optional[FactorValueEntity]
    def get_by_factor_and_date(self, factor_id: int, date_value: date) -> List[FactorValueEntity]
    def get_factor_values_by_entity(self, entity_id: int, factor_id: Optional[int] = None) -> List[FactorValueEntity]

    # CRUD operations for factor rules
    def create_factor_rule(self, domain_rule: FactorRuleEntity) -> Optional[FactorRuleEntity]
    def get_rules_by_factor(self, factor_id: int) -> List[FactorRuleEntity]

    # Convenience methods
    def add_factor(self, name: str, group: str, subgroup: str, data_type: str, source: str, definition: str) -> Optional[FactorEntity]
    def add_factor_value(self, factor_id: int, entity_id: int, date: date, value) -> Optional[FactorValueEntity]
    def add_factor_rule(self, factor_id: int, condition: str, rule_type: str, method_ref: Optional[str] = None) -> Optional[FactorRuleEntity]
```

### Concrete Factor Repositories
Each financial asset type has its own factor repository:

```python
class ShareFactorRepository(BaseFactorRepository):
    def get_factor_model(self):
        return ShareFactor
    def get_factor_value_model(self):
        return ShareFactorValue
    def get_factor_rule_model(self):
        return ShareFactorRule
```

---

## 💼 Financial Asset Repositories

### CompanyShareRepository
Handles CRUD operations for company share entities with advanced features:

**Core Methods:**
- `create()`, `get_by_id()`, `update()`, `delete()` - Standard CRUD
- `get_by_ticker()`, `exists_by_ticker()` - Ticker-specific operations
- `add_bulk()`, `delete_bulk()`, `update_bulk()` - Bulk operations

**Advanced Features:**
- `add_with_openfigi()` - Integration with OpenFIGI API for data enrichment
- `bulk_add_with_openfigi()` - Bulk creation with external data
- `_get_next_available_company_share_id()` - Sequential ID generation

---

## 🗺️ Mapper Integration

Repositories use mappers to convert between domain entities and ORM models:

```python
class CompanyShareRepository:
    def _to_domain(self, infra_share: CompanyShareModel) -> CompanyShareEntity:
        """Convert ORM model to domain entity using mapper"""
        return CompanyShareMapper.to_domain(infra_share)

    def add(self, domain_share: CompanyShareEntity) -> CompanyShareEntity:
        """Convert domain entity to ORM model using mapper"""
        new_share = CompanyShareMapper.to_orm(domain_share)
        self.session.add(new_share)
        self.session.commit()
        return self._to_domain(new_share)
```

---

## 🔄 Session Management

### Database Session Lifecycle
- **Session Injection**: All repositories receive SQLAlchemy session via constructor
- **Transaction Management**: Repositories handle commit/rollback for data integrity
- **Error Handling**: Comprehensive exception handling with automatic rollback

```python
def create_entity(self, domain_entity):
    try:
        orm_entity = self._to_orm(domain_entity)
        self.session.add(orm_entity)
        self.session.commit()
        return self._to_domain(orm_entity)
    except Exception as e:
        self.session.rollback()
        print(f"Error creating entity: {e}")
        return None
```

---

## 📈 Performance Optimizations

### Bulk Operations
Repositories support bulk operations for high-performance data processing:

```python
def add_bulk(self, domain_entities: List[DomainEntity]) -> List[DomainEntity]:
    """Atomic bulk creation with transaction management"""
    try:
        with self.session.begin():
            for domain_entity in domain_entities:
                orm_entity = self._to_orm(domain_entity)
                self.session.add(orm_entity)
            self.session.commit()
    except Exception as e:
        self.session.rollback()
        raise
```

### Query Optimization
- Strategic use of SQLAlchemy query methods
- Proper indexing on frequently queried columns
- Lazy loading for related entities

---

## 🧪 Testing Strategy

### Repository Testing
- **Unit Tests**: Mock session and test CRUD operations
- **Integration Tests**: Test against real database with test fixtures
- **Performance Tests**: Validate bulk operation performance

### Test Structure
```python
def test_repository_crud():
    # Arrange: Create test entity
    # Act: Perform repository operation
    # Assert: Validate result and database state
```

---

## 🔧 Configuration

### Database Types
Repositories support multiple database backends through DatabaseManager:
- SQLite (development/testing)
- PostgreSQL (production)
- MySQL (alternative production)

### Connection Management
```python
class Repository:
    def __init__(self, session: Session):
        self.session = session  # Injected session for testability
```

---

## 📝 Usage Examples

### Basic Entity Operations
```python
# Initialize repository
repository = CompanyShareRepository(session)

# Create new entity
share = CompanyShareEntity(ticker="AAPL", exchange_id=1, company_id=1)
created_share = repository.add(share)

# Retrieve by ticker
aapl_shares = repository.get_by_ticker("AAPL")

# Bulk creation
shares = repository.add_bulk([share1, share2, share3])
```

### Factor Operations
```python
# Initialize factor repository
factor_repo = ShareFactorRepository('sqlite')

# Create factor
factor = factor_repo.add_factor(
    name="close_price", 
    group="price", 
    subgroup="ohlc",
    data_type="numeric",
    source="csv",
    definition="Daily closing price"
)

# Add factor value
factor_repo.add_factor_value(
    factor_id=factor.id,
    entity_id=1,
    date=date.today(),
    value=Decimal("150.25")
)

# Add validation rule
factor_repo.add_factor_rule(
    factor_id=factor.id,
    condition="close_price > 0",
    rule_type="validation",
    method_ref="validate_positive_price"
)
```

---

## 🚀 Future Enhancements

### Planned Features
- **Caching Layer**: Redis integration for high-performance queries
- **Event Sourcing**: Audit trail for all entity changes
- **Multi-tenancy**: Support for isolated data per organization
- **GraphQL Integration**: Direct GraphQL resolver support

### Performance Improvements
- **Connection Pooling**: Optimize database connection usage
- **Query Caching**: Cache frequent read operations
- **Async Support**: SQLAlchemy async session support

---

This repository architecture ensures clean separation of concerns, maintains data integrity, and provides a scalable foundation for the entire financial data system.