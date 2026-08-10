# CLAUDE.md - Financial Assets Joined-Table Inheritance

## 🏛️ Financial Entity Polymorphic Architecture

This document outlines the **joined-table inheritance** pattern used for modeling all
financial entities (assets and portfolios) in the `base_infrastructure` project.

---

## 📊 Architecture Overview: Unified Root — `FinancialEntityModel`

`FinancialEntityModel` (`financial_entities` table) is the **single SQLAlchemy inheritance
root** for the entire financial object hierarchy.  Both `FinancialAssetModel` and
`PortfolioModel` are joined-table children of this root.

```
financial_entities (root table — polymorphic_on = entity_type)
├── id (PK, autoincrement)
└── entity_type (single discriminator for the FULL hierarchy)

    ├── financial_assets (child table — FK → financial_entities.id)
    │   ├── FinancialAssetModel  (polymorphic_identity = "financial_asset")
    │   │   ├── asset_type (informational copy of entity_type — no longer discriminator)
    │   │   ├── name, symbol, description
    │   │   └── start_date, end_date
    │   │
    │   ├── company_shares       (polymorphic_identity = "company_share")
    │   ├── currencies           (polymorphic_identity = "currency")
    │   ├── derivatives          (polymorphic_identity = "derivatives")
    │   │   └── underlying_asset_id (FK → financial_entities.id)  ← any entity
    │   └── [other asset types...]
    │
    └── portfolios (child table — FK → financial_entities.id)
        ├── PortfolioModel       (polymorphic_identity = "Portfolio")
        │   ├── portfolio_type (informational copy of entity_type — no longer discriminator)
        │   ├── name, start_date, end_date
        │
        ├── company_share_portfolios  (polymorphic_identity = "CompanySharePortfolio")
        └── currency_portfolios       (polymorphic_identity = "CurrencyPortfolio")
```

### Why the unified root?

`DerivativeModel.underlying_asset_id` previously FK'd to `financial_assets.id`,
making it impossible for `CompanySharePortfolioOption` to reference its underlying
`CompanySharePortfolio` (a Portfolio, not a FinancialAsset).

`HoldingModel.asset_id` also previously had no FK at all, requiring each concrete holding
subclass to declare its own child-table FK column aliased to `asset_id` and merge both
via `column_property`.

With `financial_entities` as the root:
- `DerivativeModel.underlying_asset_id` FKs to `financial_entities.id` → any financial
  entity (asset **or** portfolio) can be an underlying.
- `HoldingModel.asset_id` FKs to `financial_entities.id` → no more child-table FK
  column overrides or `column_property` merges needed for portfolio-holding models.

### Single discriminator

`financial_entities.entity_type` is the sole `polymorphic_on` column.  SQLAlchemy
maps every leaf class's `polymorphic_identity` to this column:

| Class | `entity_type` value |
|-------|---------------------|
| `FinancialAssetModel` | `"financial_asset"` |
| `CompanyShareModel` | `"company_share"` |
| `CurrencyModel` | `"currency"` |
| `DerivativeModel` | `"derivatives"` |
| `PortfolioModel` | `"Portfolio"` |
| `CompanySharePortfolioModel` | `"CompanySharePortfolio"` |
| `CurrencyPortfolioModel` | `"CurrencyPortfolio"` |

### `asset_type` / `portfolio_type` backward compat

These columns are kept **as informational copies** only.  They are auto-populated by
each model's `__init__` from `sa_inspect(type(self)).polymorphic_identity` so that
queries filtering on `asset_type` or `portfolio_type` continue to work without changes.

---

## 🎯 Core Design Principles

---

## 🎯 Core Design Principles

### 1. **Root Table Pattern**
```python
class FinancialAssetModel(Base):
    __tablename__ = 'financial_assets'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_type = Column(String(50), nullable=False, index=True)  # Discriminator
    name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)
    
    __mapper_args__ = {
        "polymorphic_on": asset_type,
        "polymorphic_identity": "financial_asset",
    }
```

### 2. **Child Table Pattern**
```python
class CompanyShareModel(Base):
    __tablename__ = 'company_shares'
    
    # Primary key is also foreign key to parent
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    
    # Asset-specific columns
    ticker = Column(String(20), nullable=False, index=True)
    exchange_id = Column(Integer, ForeignKey('exchanges.id'), nullable=False)
    company_id = Column(Integer, ForeignKey('companies.id'), nullable=False)
    is_tradeable = Column(Boolean, default=True)
    
    __mapper_args__ = {
        "polymorphic_identity": "company_share",  # Discriminator value
    }
```

---

## 🚀 Creation Rules (CRITICAL)

### **Never Create FinancialAssetModel Directly**

```python
# ❌ WRONG: Never do this
financial_asset = FinancialAssetModel(name="Some Asset")

# ✅ CORRECT: Always create concrete types
company_share = CompanyShareModel(
    ticker="AAPL",
    company_id=1,
    exchange_id=1,
    name="Apple Inc."
)
```

### **Automatic Dual-Table Population**

When you create a `CompanyShareModel`, SQLAlchemy automatically:

1. **Inserts into `financial_assets`**:
   - Generates new `id`
   - Sets `asset_type='company_share'` (from `polymorphic_identity`)
   - Populates shared columns (`name`, `description`, etc.)

2. **Inserts into `company_shares`**:
   - Uses the same `id` from `financial_assets`
   - Populates asset-specific columns (`ticker`, `exchange_id`, etc.)

3. **Maintains Referential Integrity**:
   - Foreign key constraint ensures `company_shares.id` references `financial_assets.id`
   - Cascading rules handle deletions properly

---

## 🔍 Holding Resolution Pattern

### **Polymorphic Asset Resolution**

```python
class HoldingModel(Base):
    __tablename__ = 'holdings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey('financial_assets.id'), nullable=False)
    container_id = Column(Integer, nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    
    # Polymorphic relationship - SQLAlchemy handles type resolution
    asset = relationship(
        "FinancialAssetModel", 
        back_populates="holdings"
    )
```

### **Automatic Type Resolution**

```python
# Query a holding
holding = session.query(HoldingModel).filter_by(id=123).first()

# SQLAlchemy automatically:
# 1. Reads financial_assets.asset_type for this holding's asset_id
# 2. Determines the concrete type (e.g., 'company_share')
# 3. Joins with the appropriate child table (company_shares)
# 4. Returns the concrete subclass instance

print(type(holding.asset))  # <class 'CompanyShareModel'>
print(holding.asset.ticker)  # 'AAPL' (asset-specific attribute)
```

---

## 🏗️ Database Schema Design

### **Table Structure**
```sql
-- Root table
CREATE TABLE financial_assets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_type VARCHAR(50) NOT NULL,  -- Discriminator
    name VARCHAR(200),
    description TEXT,
    start_date DATE,
    end_date DATE
);
CREATE INDEX ix_financial_assets_asset_type ON financial_assets(asset_type);

-- Child table example
CREATE TABLE company_shares (
    id INTEGER PRIMARY KEY,
    ticker VARCHAR(20) NOT NULL,
    exchange_id INTEGER NOT NULL,
    company_id INTEGER NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    is_tradeable BOOLEAN DEFAULT TRUE,
    FOREIGN KEY(id) REFERENCES financial_assets(id) ON DELETE CASCADE,
    FOREIGN KEY(exchange_id) REFERENCES exchanges(id),
    FOREIGN KEY(company_id) REFERENCES companies(id)
);
CREATE INDEX ix_company_shares_ticker ON company_shares(ticker);
```

### **Key Schema Features**
- **Shared ID space**: All assets have unique IDs across all types
- **Discriminator index**: Fast filtering by asset type
- **Referential integrity**: CASCADE DELETE from parent to child
- **Type-specific indexes**: Optimized queries for each asset type

---

## 🔄 Core Invariant

### **The Golden Rule**
```
Concrete Asset = Root Row + Subtype Row
```

**This means:**
- Every concrete asset (CompanyShare, IndexFuture, etc.) consists of exactly two database rows
- One row in `financial_assets` (contains shared attributes)
- One row in the specific asset table (contains specialized attributes)
- Both rows share the same `id` value
- Creating the subtype automatically populates the root

### **Invariant Enforcement**
- **Database level**: Foreign key constraints ensure referential integrity
- **ORM level**: SQLAlchemy polymorphism handles dual-table operations
- **Application level**: Creation patterns prevent direct root table access

---

## 📚 Polymorphic Identity Mapping

### **Asset Type Registry**
```python
# Supported asset types and their discriminator values
ASSET_TYPE_MAPPING = {
    'financial_asset': FinancialAssetModel,     # Abstract base (never created)
    'company_share': CompanyShareModel,         # Stock/equity shares
    'index_future': IndexFutureModel,           # Index futures contracts
    'bond': BondModel,                          # Fixed income securities
    'commodity': CommodityModel,                # Physical commodities
    'currency': CurrencyModel,                  # Foreign exchange
    'etf_share': ETFShareModel,                 # Exchange-traded fund shares
    'option': OptionModel,                      # Options contracts
    # ... additional asset types
}
```

### **Automatic Type Resolution**
```python
# SQLAlchemy handles this automatically
asset = session.query(FinancialAssetModel).filter_by(id=123).first()

# Returns the appropriate concrete subclass based on asset_type discriminator
if asset.asset_type == 'company_share':
    return CompanyShareModel instance
elif asset.asset_type == 'index_future':
    return IndexFutureModel instance
# etc.
```

---

## 🔗 Relationship Management

### **Bidirectional Relationships**
```python
class FinancialAssetModel(Base):
    # One-to-many with holdings
    holdings = relationship(
        "HoldingModel", 
        back_populates="asset",
        cascade="all, delete-orphan"
    )
    
    # One-to-many with instruments
    instruments = relationship(
        "InstrumentModel", 
        back_populates="asset",
        cascade="all, delete-orphan"
    )

class CompanyShareModel(Base):
    # Inherits relationships from FinancialAssetModel
    # Plus asset-specific relationships
    company = relationship("CompanyModel", back_populates="company_shares")
    exchange = relationship("ExchangeModel", back_populates="company_shares")
```

### **Cross-Table Queries**
```python
# Query across asset types
all_assets = session.query(FinancialAssetModel).all()

# Filter by specific asset type
company_shares = session.query(FinancialAssetModel).filter(
    FinancialAssetModel.asset_type == 'company_share'
).all()

# Direct subclass queries (more efficient)
company_shares = session.query(CompanyShareModel).all()
```

---

## ⚡ Performance Optimization

### **Query Strategies**
```python
# Efficient: Direct subclass query
shares = session.query(CompanyShareModel).filter_by(ticker='AAPL').all()

# Less efficient: Base class filtering
shares = session.query(FinancialAssetModel).filter(
    and_(
        FinancialAssetModel.asset_type == 'company_share',
        CompanyShareModel.ticker == 'AAPL'
    )
).all()
```

### **Index Strategy**
- **Discriminator index**: `asset_type` for fast polymorphic filtering
- **Asset-specific indexes**: `ticker` for company shares, etc.
- **Relationship indexes**: Foreign keys for joins
- **Composite indexes**: For common query patterns

### **Lazy Loading Configuration**
```python
class HoldingModel(Base):
    asset = relationship(
        "FinancialAssetModel",
        back_populates="holdings",
        lazy='select'  # Control loading strategy
    )
```

---

## 🧪 Testing Patterns

### **Creation Testing**
```python
def test_company_share_creation():
    # Test that creating CompanyShareModel automatically populates both tables
    share = CompanyShareModel(
        ticker="TEST",
        company_id=1,
        exchange_id=1,
        name="Test Company"
    )
    session.add(share)
    session.commit()
    
    # Verify root table entry
    asset = session.query(FinancialAssetModel).filter_by(id=share.id).first()
    assert asset.asset_type == 'company_share'
    assert asset.name == "Test Company"
    
    # Verify child table entry
    assert share.ticker == "TEST"
```

### **Polymorphic Resolution Testing**
```python
def test_holding_asset_resolution():
    # Create holding referencing a company share
    holding = HoldingModel(asset_id=share_id, container_id=1, start_date=datetime.now())
    session.add(holding)
    session.commit()
    
    # Test automatic type resolution
    retrieved_holding = session.query(HoldingModel).filter_by(id=holding.id).first()
    assert isinstance(retrieved_holding.asset, CompanyShareModel)
    assert hasattr(retrieved_holding.asset, 'ticker')
```

---

## 🚨 Common Pitfalls & Solutions

### **❌ Pitfall 1: Direct Root Creation**
```python
# DON'T DO THIS
asset = FinancialAssetModel(name="Some Asset")
# This creates an orphaned row in financial_assets with no specialized data
```

### **✅ Solution: Always Use Concrete Types**
```python
# DO THIS INSTEAD
asset = CompanyShareModel(
    name="Apple Inc.",
    ticker="AAPL",
    company_id=1,
    exchange_id=1
)
```

### **❌ Pitfall 2: Manual ID Management**
```python
# DON'T DO THIS
asset = CompanyShareModel(id=123, ticker="AAPL", ...)
# Let SQLAlchemy manage ID generation automatically
```

### **✅ Solution: Automatic ID Generation**
```python
# DO THIS INSTEAD
asset = CompanyShareModel(ticker="AAPL", company_id=1, exchange_id=1)
# SQLAlchemy generates ID and maintains consistency
```

### **❌ Pitfall 3: Inconsistent Discriminator Values**
```python
# SQLAlchemy prevents this, but be aware
# polymorphic_identity must match the intended asset type
```

---

## 🔮 Extension Patterns

### **Adding New Asset Types**
```python
class BondModel(Base):
    __tablename__ = 'bonds'
    
    id = Column(Integer, ForeignKey("financial_assets.id"), primary_key=True)
    
    # Bond-specific columns
    coupon_rate = Column(Numeric(5, 4), nullable=False)
    maturity_date = Column(Date, nullable=False)
    face_value = Column(Numeric(20, 2), nullable=False)
    credit_rating = Column(String(10), nullable=True)
    
    __mapper_args__ = {
        "polymorphic_identity": "bond",
    }
    
    # Bond-specific relationships
    issuer = relationship("IssuerModel", back_populates="bonds")
```

### **Migration Strategy**
```python
# Alembic migration for new asset type
def upgrade():
    # Create new child table
    op.create_table('bonds',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('coupon_rate', sa.Numeric(5,4), nullable=False),
        sa.Column('maturity_date', sa.Date(), nullable=False),
        sa.Column('face_value', sa.Numeric(20,2), nullable=False),
        sa.Column('credit_rating', sa.String(10), nullable=True),
        sa.ForeignKeyConstraint(['id'], ['financial_assets.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
```

---

## 📋 Summary

### **Key Benefits of Joined-Table Inheritance**
- **Type Safety**: Each asset type has its own table with appropriate columns
- **No Column Bloat**: Child tables only contain relevant columns
- **Referential Integrity**: Database-enforced consistency between root and child
- **Query Efficiency**: Direct queries on specialized tables
- **Easy Extensions**: Adding new asset types doesn't affect existing tables

### **Implementation Checklist**
- [x] Root table (`financial_assets`) with discriminator column
- [x] Child tables with FK to root table's PK
- [x] Polymorphic identity configuration for each asset type
- [x] Never create root class instances directly
- [x] Automatic type resolution in holding relationships
- [x] Proper indexing strategy for query performance
- [x] Cascade deletion rules for data integrity

### **Core Invariant Reminder**
**Concrete asset = root row + subtype row**  
Creating the subtype automatically populates the root. This is the foundation of the entire system.

---

**Key Takeaway**: This pattern provides **type-safe polymorphism** with **database-enforced integrity**. The dual-table structure ensures that each asset type maintains its specialized attributes while participating in the unified financial asset ecosystem through the shared root table.