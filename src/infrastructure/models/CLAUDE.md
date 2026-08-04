# CLAUDE.md - Infrastructure Models Layer

## 🗄️ Infrastructure Models Responsibilities

This directory contains **SQLAlchemy ORM models** that handle data persistence and database schema definition for the `base_infrastructure` project.

---

## 📋 Layer Responsibilities

### ✅ What Infrastructure Models ARE Responsible For:

1. **Data Persistence Schema**
   - SQLAlchemy ORM model definitions
   - Database table structure and relationships
   - Column definitions, constraints, and indexes
   - Foreign key relationships and cascading rules

2. **Polymorphic Inheritance Management**
   - Discriminator column configuration
   - Polymorphic identity mapping
   - Inheritance hierarchy for factor types
   - Type-specific column management

3. **Database Optimization**
   - Index definitions for query performance
   - Relationship configuration for efficient joins
   - Database-specific optimizations
   - Query performance tuning through model design

4. **Data Validation at Schema Level**
   - Column constraints (nullable, length, type)
   - Database-level validation rules
   - Referential integrity enforcement
   - Data type conversion and validation

### ❌ What Infrastructure Models are NOT Responsible For:

1. **Business Logic**
   - No domain calculations or algorithms
   - No business rule enforcement beyond basic constraints
   - No domain-specific validation logic
   - No business process orchestration

2. **Data Access Patterns**
   - No repository pattern implementation
   - No query logic or data access methods
   - No transaction management
   - No database session handling

3. **Domain Entity Conversion**
   - No direct mapping to/from src.domain entities
   - No business object transformation
   - No domain-specific method implementations
   - No entity behavior definition

---

## 🏗️ Architecture Overview

```
src/infrastructure/models/
├── __init__.py                 # Base model configuration
├── factor/
│   └── factor.py              # Unified factor models with discriminator
└── [other domain models]/
```

### Actual FactorModel Schema (single-table inheritance)

```python
class FactorModel(Base):
    __tablename__ = 'factors'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    name        = Column(String(255),  nullable=False)
    group       = Column(String(100),  nullable=False)
    subgroup    = Column(String(100),  nullable=False)
    frequency   = Column(String(50),   nullable=False)
    data_type   = Column(String(100),  nullable=False)
    source      = Column(String(255),  nullable=False)
    definition  = Column(Text,         nullable=False)
    factor_type = Column(String(100),  nullable=False, index=False)  # discriminator; NOT indexed

    __mapper_args__ = {
        'polymorphic_identity': 'factor',
        'polymorphic_on': factor_type,
    }
```

#### Key constraints
| Rule | Detail |
|------|--------|
| **All columns `nullable=False`** | Every factor persisted to DB must supply non-None values for all eight columns. The domain entity allows `Optional` for `subgroup`, `frequency`, `data_type`, `source`, `definition` — repos must provide explicit defaults in `_create_or_get` rather than forwarding `None`. |
| **`factor_type` is NOT indexed** (`index=False`) | Intentional — single-table inheritance lookups are done by primary key or name+group filter, not by discriminator scan. Adding an index would add write overhead with no read benefit for this access pattern. |
| **`frequency` must always be explicit** | Callers must always pass `frequency` as a named argument to repos. Never use a fallback default (e.g. `"1d"`) that silently misrepresents what the factor actually covers. |

### Actual FactorValueModel Schema

```python
class FactorValueModel(Base):
    __tablename__ = 'factor_values'

    id          = Column(Integer, primary_key=True, autoincrement=True)
    factor_id   = Column(Integer, ForeignKey("factors.id"),       nullable=False)
    entity_id   = Column(Integer,                                 nullable=False)   # generic entity reference
    entity_type = Column(String(100),                             nullable=False, index=True)  # entity class name
    date        = Column(DateTime(timezone=True),                 nullable=False)
    value       = Column(String(255),                             nullable=False)
    currency_id = Column(Integer, ForeignKey("currencies.id"),    nullable=False)
```

#### Key constraints
| Rule | Detail |
|------|--------|
| **All columns `nullable=False`** | Every factor value persisted to DB must supply non-None values for all columns. Persisting a value without `currency_id`, `entity_type`, or `value` will raise an `IntegrityError`. |
| **`entity_type` is indexed** | Used for discriminator-based lookups across entity classes. |
| **`value` stored as `String(255)`** | Financial values are serialised to string for precision; deserialise with `Decimal(str_val)` at the domain layer. |
| **`date` includes timezone** (`DateTime(timezone=True)`) | All datetimes stored with tz info; naive datetimes may cause comparison issues. |

---

## 🎯 Factor Model Polymorphic System

### 1. **Discriminator-Based Inheritance**
- **Single table inheritance** using `factor_type` discriminator
- **11+ polymorphic subclasses** for different factor types
- **Specialized columns** for each factor type (all nullable)
- **Automatic type resolution** by SQLAlchemy based on discriminator

### 2. **Factor Type Mapping**
```python
# Geographic Factors
ContinentFactor → 'continent'
CountryFactor → 'country'

# Financial Asset Factors  
FinancialAssetFactor → 'financial_asset'
SecurityFactor → 'security'
EquityFactor → 'equity'
ShareFactor → 'share'

# Share-Specific Factors
ShareMomentumFactor → 'share_momentum'
ShareTechnicalFactor → 'share_technical'
ShareTargetFactor → 'share_target'
ShareVolatilityFactor → 'share_volatility'

# Asset Type Factors
BondFactor → 'bond'
CommodityFactor → 'commodity'
CurrencyFactor → 'currency'
ETFShareFactor → 'ETF'
FuturesFactor → 'futures'
IndexFactor → 'index'
OptionsFactor → 'option'
```

### 3. **Specialized Columns by Type**
```python
# Geographic columns
continent_code, geographic_zone, country_code, currency, is_developed

# Financial asset columns
asset_class, market, security_type, isin, cusip

# Equity/Share columns
sector, industry, market_cap_category, ticker_symbol, share_class, exchange

# Share factor specialized columns
period, momentum_type, indicator_type, smoothing_factor,
target_type, forecast_horizon, is_scaled, scaling_method,
volatility_type, annualization_factor
```

---

## 🔗 Relationship Management

### 1. **Factor ↔ FactorValue Relationship**
```python
class FactorModel(Base):
    factor_values = relationship(
        "FactorValue", 
        back_populates="factor", 
        cascade="all, delete-orphan"
    )

class FactorValue(Base):
    factor = relationship("FactorModel", back_populates="factor_values")
```

### 2. **Entity Type Tracking**
```python
class FactorValue(Base):
    entity_id = Column(Integer, nullable=False)        # Generic entity reference
    entity_type = Column(String(50), nullable=False)   # 'share', 'equity', etc.
```

### 3. **Performance Optimizations**
```python
# Strategic indexes for query performance
factor_type = Column(String(50), nullable=False, index=True)  # Discriminator index
entity_type = Column(String(50), nullable=False, index=True)  # Entity type index  
date = Column(Date, nullable=False, index=True)               # Date index
name = Column(String(255), nullable=False, index=True)        # Factor name index
```

---

## 💾 Database Schema Strategy

### 1. **Single Table Inheritance Benefits**
- **Unified storage** for all factor types
- **Simple queries** across factor types
- **Easy factor type additions** without schema changes
- **Efficient polymorphic queries** with discriminator index

### 2. **Column Design Patterns**
```python
# Nullable specialized columns
period = Column(Integer, nullable=True)              # Only for time-based factors
is_developed = Column(String(10), nullable=True)     # String boolean for flexibility
value = Column(Numeric(20, 8), nullable=False)      # High precision for financial data
```

### 3. **Data Type Considerations**
```python
# Financial precision
Numeric(20, 8)  # For factor values requiring high precision
Float           # For smoothing factors and ratios
String(10)      # For boolean flags stored as 'true'/'false'
Date           # For factor value dates (no time component needed)
Text           # For factor definitions and descriptions
```

---

## 🏃‍♂️ Performance Optimization

### 1. **Index Strategy**
- **Discriminator index** on `factor_type` for fast polymorphic queries
- **Composite indexes** on frequently queried combinations
- **Date indexes** for time-series factor value queries
- **Entity type indexes** for cross-entity factor analysis

### 2. **Query Optimization**
```python
# Efficient polymorphic queries
session.query(ShareMomentumFactor).filter(...)  # Automatic type filtering
session.query(FactorModel).filter(FactorModel.factor_type == 'share_momentum')

# Optimized relationship loading
factor_values = relationship(..., lazy='select')  # Control loading strategy
```

### 3. **Storage Efficiency**
- **Nullable columns** minimize storage for unused specialized fields
- **Appropriate data types** balance precision and storage
- **Normalized relationships** prevent data duplication

---

## 🔄 Integration Patterns

### 1. **Domain ← Infrastructure Mapping**
- **Mappers handle conversion** between ORM models and domain entities
- **Infrastructure models remain persistence-focused**
- **Domain logic stays in domain layer**

### 2. **Repository Pattern Integration**
```python
# Repositories use these models for persistence
class BaseFactorRepository:
    def get_factor_model(self):
        return FactorModel  # Returns the ORM model class
    
    def _to_entity(self, orm_model):
        return FactorMapper.to_domain(orm_model)  # Delegates to mapper
```

### 3. **Application Service Usage**
```python
# Application services work with domain entities
# Infrastructure models are abstracted away
factor_entity = repository.get_by_id(factor_id)  # Returns domain entity
```

---

## 🧪 Testing Considerations

### Model Testing Focus:
- **Schema validation** - test column definitions and constraints
- **Relationship integrity** - test foreign keys and cascading
- **Polymorphic behavior** - test discriminator-based queries
- **Performance testing** - test query efficiency with large datasets

### Test Database Strategy:
```python
# Use SQLite for fast model tests
def test_factor_model_creation():
    factor = ShareMomentumFactor(
        name="Test Momentum",
        factor_type="share_momentum",
        period=20
    )
    # Test model creation and persistence
```

---

## 🔮 Migration Strategy

### Schema Evolution:
- **Additive changes preferred** - new nullable columns
- **Alembic migrations** for schema versioning
- **Backward compatibility** consideration for existing data
- **Data migration scripts** for complex transformations

### Factor Type Extensions:
```python
# Adding new factor types
class NewFactorType(FactorModel):
    __mapper_args__ = {'polymorphic_identity': 'new_type'}
    
# Add specialized columns to FactorModel base class
new_specialized_column = Column(String(50), nullable=True)
```

---

## ⚠️ Important Considerations

### 1. **No Business Logic**
- Infrastructure models are **data containers only**
- Business calculations belong in domain entities
- Validation logic beyond basic constraints belongs in domain layer

### 2. **Mapper Dependency**
- Models should not directly convert to domain entities
- Use dedicated mapper classes for conversion
- Keep models focused on persistence concerns

### 3. **Performance Monitoring**
- Monitor query performance with large factor datasets
- Index effectiveness should be regularly reviewed
- Consider partitioning strategies for very large factor value tables

---

**Key Takeaway**: This layer handles **data persistence only**. Keep models focused on database schema and relationships. All business logic and domain behavior lives in the domain layer, accessed through mappers and repositories.