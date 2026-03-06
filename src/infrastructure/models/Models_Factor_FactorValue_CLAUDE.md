# Models Documentation: Factor vs FactorValue

## Overview
This documentation explains the distinction between `Factor` and `FactorValue` models in the infrastructure layer, their relationships, inheritance patterns, and how they support the domain-driven architecture. The models use SQLAlchemy ORM for database persistence while maintaining clear separation from domain entities.

## Core Architecture

### Model Hierarchy
```
ModelBase (SQLAlchemy Base)
├── FactorModel (Polymorphic Base)
│   ├── IndexFactorModel
│   ├── CompanyShareFactorModel  
│   ├── IndexFutureFactorModel
│   ├── IndexFutureOptionFactorModel
│   ├── EquityFactorModel
│   ├── BondFactorModel
│   └── ... (other factor types)
└── FactorValueModel (Time-series data)
    ├── Financial asset associations
    └── Point-in-time factor values
```

## Factor Models

### Base Factor Model
**File**: `/src/infrastructure/models/factor/factor.py`

```python
class FactorModel(Base):
    __tablename__ = 'factors'

    # Primary key and identification
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    
    # Factor classification
    group = Column(String(100), nullable=False)              # e.g., "price", "volume", "volatility"
    subgroup = Column(String(100), nullable=True)            # e.g., "return", "momentum", "technical"
    
    # Metadata
    frequency = Column(String(50), nullable=True)            # e.g., "daily", "monthly", "quarterly"
    data_type = Column(String(100), nullable=True)           # e.g., "decimal", "percentage", "ratio"
    source = Column(String(255), nullable=True)              # e.g., "bloomberg", "ibkr", "calculated"
    definition = Column(Text, nullable=True)                 # Factor description/formula
    
    # Polymorphic discrimination
    factor_type = Column(String(100), nullable=False, index=True)  # Discriminator for inheritance
    
    # Relationships
    factor_values = relationship(
        "src.infrastructure.models.factor.factor_value.FactorValueModel",
        back_populates="factors"
    )
    
    # Factor dependency relationships
    dependents = relationship(
        "src.infrastructure.models.factor.factor_dependency.FactorDependencyModel",
        foreign_keys="FactorDependencyModel.dependent_factor_id",
        back_populates="dependent_factor"
    )
    
    dependencies = relationship(
        "src.infrastructure.models.factor.factor_dependency.FactorDependencyModel", 
        foreign_keys="FactorDependencyModel.independent_factor_id",
        back_populates="independent_factor"
    )
    
    # Polymorphic configuration
    __mapper_args__ = {
        'polymorphic_identity': 'factor',
        'polymorphic_on': factor_type
    }
```

**Key Characteristics**:
- **Polymorphic Base**: Supports inheritance through `factor_type` discriminator
- **Metadata Rich**: Extensive classification and documentation fields
- **Relationship Support**: Links to factor values and dependencies
- **Extensible**: Easy to add new factor types through inheritance

### Concrete Factor Models

#### IndexFactorModel
```python
class IndexFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "index_factor"
    }
```

#### CompanyShareFactorModel  
```python
class CompanyShareFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_factor"
    }
```

#### Derivative Factor Models
```python
class IndexFutureFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "index_future_factor"
    }

class IndexFutureOptionFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "index_future_option_factor"
    }

class IndexFutureOptionPriceFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "index_future_option_price_factor"
    }

class IndexFutureOptionDeltaFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "index_future_option_delta_factor"
    }
```

#### Specialized Return Factor Models
```python
class IndexPriceReturnFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "index_price_return_factor"
    }

class CompanySharePriceReturnFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "company_share_price_return_factor"
    }

class FuturePriceReturnFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "future_price_return_factor"
    }
```

## FactorValue Models

### Core FactorValue Model
**File**: `/src/infrastructure/models/factor/factor_value.py`

```python
class FactorValueModel(Base):
    __tablename__ = 'factor_values'
    
    # Composite primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    factor_id = Column(Integer, ForeignKey('factors.id'), nullable=False, index=True)
    entity_id = Column(Integer, nullable=False, index=True)        # Financial asset entity ID
    date = Column(Date, nullable=False, index=True)               # Observation date
    
    # Value storage
    value = Column(Numeric(precision=20, scale=6), nullable=True)  # High precision for financial data
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    source = Column(String(100), nullable=True)                   # Data source ("ibkr", "bloomberg", etc.)
    quality_score = Column(Float, nullable=True)                  # Data quality indicator
    
    # Relationships
    factors = relationship(
        "src.infrastructure.models.factor.factor.FactorModel",
        back_populates="factor_values"
    )
    
    # Indexes for performance
    __table_args__ = (
        Index('ix_factor_entity_date', 'factor_id', 'entity_id', 'date'),
        Index('ix_entity_date', 'entity_id', 'date'),
        Index('ix_factor_date', 'factor_id', 'date'),
        UniqueConstraint('factor_id', 'entity_id', 'date', name='uq_factor_entity_date'),
    )
```

**Key Characteristics**:
- **Time-Series Data**: Stores factor values over time
- **Composite Keys**: Uniqueness enforced on factor_id + entity_id + date
- **High Precision**: Uses Numeric type for accurate financial calculations  
- **Performance Optimized**: Multiple indexes for common query patterns
- **Audit Trail**: Created/updated timestamps for data lineage
- **Data Quality**: Quality scoring for value reliability

## Factor vs FactorValue Distinction

### 1. **Conceptual Difference**

#### Factor (Definition/Metadata)
- **What**: Defines the calculation/metric (e.g., "daily_price_return")
- **Reusable**: One factor definition applies to many entities
- **Static**: Definition rarely changes once established
- **Examples**:
  - `IndexPriceReturnFactor`: "Daily price return for index securities"
  - `CompanyShareVolumeFactor`: "Daily trading volume for company shares"
  - `IndexFutureOptionDeltaFactor`: "Option sensitivity to underlying price changes"

#### FactorValue (Data Points)
- **What**: Stores actual calculated values for specific entity/date combinations
- **Entity-Specific**: Each value tied to specific financial asset
- **Time-Series**: Many values per factor across different dates
- **Examples**:
  - SPX daily return on 2025-01-15: 0.0234 (2.34%)
  - AAPL volume on 2025-01-15: 45,678,900 shares
  - ESH5 C6000 delta on 2025-01-15: 0.65

### 2. **Relationship Pattern**

```
Factor (1) ←→ (Many) FactorValue

One factor definition → Multiple values across:
- Different entities (SPX, NASDAQ, AAPL, MSFT, etc.)
- Different dates (daily, monthly, quarterly observations)
- Different sources (IBKR, Bloomberg, calculated)
```

### 3. **Database Schema Comparison**

```sql
-- FACTORS table (definitions)
CREATE TABLE factors (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,           -- "daily_price_return"
    group VARCHAR(100) NOT NULL,          -- "price"  
    subgroup VARCHAR(100),                -- "return"
    frequency VARCHAR(50),                -- "daily"
    data_type VARCHAR(100),               -- "percentage"
    source VARCHAR(255),                  -- "calculated"
    definition TEXT,                      -- "Geometric daily return calculation"
    factor_type VARCHAR(100) NOT NULL     -- "index_price_return_factor"
);

-- FACTOR_VALUES table (time-series data)
CREATE TABLE factor_values (
    id INTEGER PRIMARY KEY,
    factor_id INTEGER REFERENCES factors(id),    -- Links to factor definition
    entity_id INTEGER NOT NULL,                  -- Links to financial asset
    date DATE NOT NULL,                          -- Observation date
    value NUMERIC(20,6),                         -- Actual calculated value
    source VARCHAR(100),                         -- "ibkr", "bloomberg"
    quality_score FLOAT,                         -- Data quality measure
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(factor_id, entity_id, date)           -- One value per factor/entity/date
);
```

## Usage Patterns

### 1. **Factor Creation and Retrieval**

```python
# Create factor definition (done once)
price_return_factor = IndexPriceReturnFactorModel(
    name="daily_price_return",
    group="price",
    subgroup="return", 
    frequency="daily",
    data_type="percentage",
    source="calculated",
    definition="Geometric daily return: (P_end/P_start) - 1"
)
session.add(price_return_factor)
session.commit()

# Retrieve factor for calculations
factor = session.query(IndexPriceReturnFactorModel)\
    .filter_by(name="daily_price_return")\
    .first()
```

### 2. **FactorValue Storage and Retrieval**

```python
# Store calculated values
from datetime import date
from decimal import Decimal

# SPX daily return for 2025-01-15
spx_return_value = FactorValueModel(
    factor_id=price_return_factor.id,
    entity_id=spx_entity.id,  # SPX index entity ID
    date=date(2025, 1, 15),
    value=Decimal('0.0234'),  # 2.34% return
    source="ibkr",
    quality_score=0.95
)

# AAPL daily return for same date  
aapl_return_value = FactorValueModel(
    factor_id=price_return_factor.id,
    entity_id=aapl_entity.id,  # AAPL entity ID
    date=date(2025, 1, 15), 
    value=Decimal('0.0156'),  # 1.56% return
    source="ibkr",
    quality_score=0.98
)

session.add_all([spx_return_value, aapl_return_value])
session.commit()
```

### 3. **Time-Series Queries**

```python
# Get all SPX daily returns for January 2025
spx_returns = session.query(FactorValueModel)\
    .join(FactorModel)\
    .filter(
        FactorModel.name == "daily_price_return",
        FactorValueModel.entity_id == spx_entity.id,
        FactorValueModel.date >= date(2025, 1, 1),
        FactorValueModel.date < date(2025, 2, 1)
    )\
    .order_by(FactorValueModel.date)\
    .all()

# Get latest values for all entities for a specific factor
latest_returns = session.query(FactorValueModel)\
    .join(FactorModel)\
    .filter(FactorModel.name == "daily_price_return")\
    .order_by(
        FactorValueModel.entity_id,
        FactorValueModel.date.desc()
    )\
    .distinct(FactorValueModel.entity_id)\
    .all()
```

### 4. **Cross-Entity Analysis**

```python
# Compare factor values across different entities
from sqlalchemy import func

# Average daily returns by entity for Q4 2024
avg_returns = session.query(
    FactorValueModel.entity_id,
    func.avg(FactorValueModel.value).label('avg_return'),
    func.count(FactorValueModel.value).label('count')
)\
    .join(FactorModel)\
    .filter(
        FactorModel.name == "daily_price_return",
        FactorValueModel.date >= date(2024, 10, 1),
        FactorValueModel.date <= date(2024, 12, 31)
    )\
    .group_by(FactorValueModel.entity_id)\
    .all()
```

## Performance Considerations

### 1. **Indexing Strategy**
```python
# Composite indexes for common query patterns
__table_args__ = (
    # Primary lookup: factor + entity + date
    Index('ix_factor_entity_date', 'factor_id', 'entity_id', 'date'),
    
    # Entity time-series: all factors for entity over time
    Index('ix_entity_date', 'entity_id', 'date'),
    
    # Factor cross-section: factor across all entities at point in time
    Index('ix_factor_date', 'factor_id', 'date'),
    
    # Ensure uniqueness
    UniqueConstraint('factor_id', 'entity_id', 'date', name='uq_factor_entity_date'),
)
```

### 2. **Batch Operations**
```python
# Efficient bulk inserts
factor_values = []
for entity_id in entity_ids:
    for date_val in date_range:
        factor_values.append(FactorValueModel(
            factor_id=factor.id,
            entity_id=entity_id,
            date=date_val,
            value=calculate_value(entity_id, date_val),
            source="batch_calculation"
        ))

# Use bulk operations for performance
session.bulk_insert_mappings(FactorValueModel, factor_values)
session.commit()
```

### 3. **Partitioning Strategy**
```sql
-- Partition factor_values by date for better performance
CREATE TABLE factor_values_2024 PARTITION OF factor_values 
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');

CREATE TABLE factor_values_2025 PARTITION OF factor_values
FOR VALUES FROM ('2025-01-01') TO ('2026-01-01');
```

## Data Quality and Validation

### 1. **Model-Level Validation**
```python
class FactorValueModel(Base):
    # ... column definitions
    
    @validates('value')
    def validate_value(self, key, value):
        """Validate factor value ranges."""
        if value is not None:
            # Reasonable bounds checking for financial data
            if abs(value) > 1000:  # More than 100,000% return seems wrong
                raise ValueError(f"Factor value {value} is outside reasonable bounds")
        return value
    
    @validates('date')
    def validate_date(self, key, date_val):
        """Validate observation date."""
        if date_val > datetime.now().date():
            raise ValueError("Factor value date cannot be in the future")
        return date_val
```

### 2. **Data Quality Metrics**
```python
# Add data quality scoring
class FactorValueModel(Base):
    # ... existing columns
    
    quality_score = Column(Float, nullable=True)  # 0.0 to 1.0
    quality_flags = Column(String(200), nullable=True)  # JSON flags
    
    def calculate_quality_score(self) -> float:
        """Calculate data quality score based on various factors."""
        score = 1.0
        
        # Deduct for missing values
        if self.value is None:
            score -= 0.5
            
        # Deduct for stale data
        days_old = (datetime.now().date() - self.date).days
        if days_old > 7:
            score -= 0.1 * min(days_old / 30, 0.3)
            
        # Adjust for source reliability
        source_scores = {"ibkr": 1.0, "bloomberg": 0.95, "yahoo": 0.8, "calculated": 0.9}
        score *= source_scores.get(self.source, 0.7)
        
        return max(0.0, min(1.0, score))
```

## Migration and Evolution

### 1. **Adding New Factor Types**
```python
# Step 1: Add new model class
class CryptocurrencyFactorModel(FactorModel):
    __mapper_args__ = {
        "polymorphic_identity": "cryptocurrency_factor"
    }

# Step 2: Create migration
def upgrade():
    # New discriminator value is automatically supported
    # No schema changes needed for polymorphic models
    pass
```

### 2. **Schema Evolution**
```python
# Adding new columns to FactorModel
def upgrade():
    op.add_column('factors', 
        Column('calculation_method', String(100), nullable=True))
    op.add_column('factors', 
        Column('validation_rules', Text, nullable=True))

# Adding new columns to FactorValueModel  
def upgrade():
    op.add_column('factor_values',
        Column('confidence_interval', String(50), nullable=True))
    op.add_column('factor_values', 
        Column('calculation_metadata', JSON, nullable=True))
```

## Integration with Domain Layer

### 1. **Mapper Pattern**
```python
# Domain entity
class IndexFactor:
    def __init__(self, name, group, factor_id=None):
        self.name = name
        self.group = group
        self.factor_id = factor_id

# ORM Model to Domain mapping
def to_domain(factor_model: IndexFactorModel) -> IndexFactor:
    return IndexFactor(
        name=factor_model.name,
        group=factor_model.group,
        factor_id=factor_model.id
    )

def to_orm(factor_entity: IndexFactor) -> IndexFactorModel:
    return IndexFactorModel(
        name=factor_entity.name,
        group=factor_entity.group
    )
```

### 2. **Repository Pattern**
```python
class IndexFactorRepository:
    def get_factor_values(self, factor: IndexFactor, entity_id: int, 
                         start_date: date, end_date: date) -> List[FactorValue]:
        """Get factor values using domain entities."""
        
        # Query ORM models
        orm_values = self.session.query(FactorValueModel)\
            .filter(
                FactorValueModel.factor_id == factor.factor_id,
                FactorValueModel.entity_id == entity_id,
                FactorValueModel.date >= start_date,
                FactorValueModel.date <= end_date
            )\
            .order_by(FactorValueModel.date)\
            .all()
        
        # Convert to domain entities
        return [self.factor_value_mapper.to_domain(orm_val) for orm_val in orm_values]
```

## Testing Strategies

### 1. **Model Testing**
```python
class TestFactorModels(unittest.TestCase):
    def test_factor_model_creation(self):
        factor = IndexFactorModel(
            name="test_factor",
            group="price", 
            subgroup="return",
            frequency="daily"
        )
        
        assert factor.factor_type == "index_factor"
        assert factor.name == "test_factor"
        
    def test_factor_value_constraints(self):
        # Test unique constraint
        factor_value1 = FactorValueModel(
            factor_id=1, entity_id=100, date=date.today(), value=Decimal('0.05')
        )
        factor_value2 = FactorValueModel(
            factor_id=1, entity_id=100, date=date.today(), value=Decimal('0.06')
        )
        
        session.add(factor_value1)
        session.commit()
        
        session.add(factor_value2)
        with pytest.raises(IntegrityError):
            session.commit()
```

### 2. **Performance Testing**
```python
def test_factor_value_query_performance():
    """Test query performance with large datasets."""
    
    # Create test data
    factor = IndexFactorModel(name="perf_test", group="test")
    session.add(factor)
    session.commit()
    
    # Bulk insert test values
    values = []
    for entity_id in range(1, 101):  # 100 entities
        for day in range(365):        # 1 year of data
            test_date = date(2024, 1, 1) + timedelta(days=day)
            values.append({
                'factor_id': factor.id,
                'entity_id': entity_id,
                'date': test_date,
                'value': random.uniform(-0.1, 0.1)
            })
    
    session.bulk_insert_mappings(FactorValueModel, values)
    session.commit()
    
    # Test query performance
    start_time = time.time()
    results = session.query(FactorValueModel)\
        .filter(FactorValueModel.factor_id == factor.id)\
        .count()
    query_time = time.time() - start_time
    
    assert results == 36500  # 100 entities * 365 days
    assert query_time < 1.0   # Should complete in under 1 second
```

The Factor vs FactorValue model architecture provides a robust foundation for storing and retrieving financial time-series data while maintaining clear separation between factor definitions and their calculated values across entities and time periods.