Factor Domain and Persistence Structure
🎯 Overview

This document describes the domain-driven design (DDD) structure for financial factors used in the project.
Each factor represents a quantitative or qualitative metric linked to a entity (e.g. a share, bond, or security).

In this architecture:

Factors are domain entities (FactorEquity, FactorSecurity, etc.).

Their metadata, values, and internal generation logic are stored in three separate tables.

These structures are mirrored in the infrastructure layer using SQLAlchemy ORM models and repositories for local persistence.

🧩 Domain Concept
Base Entity: FactorSecurity

Located in
src/domain/entities/factor/finance/financial_assets/security_factor.py

Subclasses like FactorEquity inherit from this class and may implement custom calculation logic, such as calculate().

Example:

class FactorEquity(FactorSecurity):
    def calculate(self, *args, **kwargs) -> Decimal:
        raise NotImplementedError("FactorEquity must implement calculate() method.")

🗄️ Database Design - Entity-Specific Factor Tables

**Architecture Overview:**
Each financial asset type now has its own dedicated factor tables following the pattern:
- `{entity}_factors` - Factor definitions specific to that entity type
- `{entity}_factor_values` - Factor values linked to entities and dates
- `{entity}_factor_rules` - Rules for factor calculations

**Implemented Factor Table Sets:**
- Share: `share_factors`, `share_factor_values`, `share_factor_rules`
- Bond: `bond_factors`, `bond_factor_values`, `bond_factor_rules`  
- Security: `security_factors`, `security_factor_values`, `security_factor_rules`
- Equity: `equity_factors`, `equity_factor_values`, `equity_factor_rules`
- Currency: `currency_factors`, `currency_factor_values`, `currency_factor_rules`
- Commodity: `commodity_factors`, `commodity_factor_values`, `commodity_factor_rules`
- Options: `options_factors`, `options_factor_values`, `options_factor_rules`
- Futures: `futures_factors`, `futures_factor_values`, `futures_factor_rules`
- Index: `index_factors`, `index_factor_values`, `index_factor_rules`
- ETF Share: `etf_share_factors`, `etf_share_factor_values`, `etf_share_factor_rules`
- Company Share: `company_share_factors`, `company_share_factor_values`, `company_share_factor_rules`

**1. Factor Definition Tables (`{entity}_factors`)**

Purpose: Store factor metadata specific to each entity type.

Common Columns:
Column	Type	Description
id	Integer	Primary key (auto-increment)
name	String(255)	Factor name (indexed)
group	String(100)	Logical group (e.g. "momentum", "valuation")
subgroup	String(100) nullable	Optional subgroup
data_type	String(50)	Type of value (defaults to 'numeric')
source	String(100) nullable	Data origin (internal, external)
definition	Text nullable	Description or definition of the factor

**2. Factor Value Tables (`{entity}_factor_values`)**

Purpose: Store factor values linked to specific entities on specific dates.

Common Columns:
Column	Type	Description
id	Integer	Primary key (auto-increment)
factor_id	Foreign Key	Links to {entity}_factors.id
entity_id	Foreign Key	Links to {entity}s.id (e.g., shares.id)
date	Date	Date of the factor value (indexed)
value	Numeric(20,8)	The numeric value of the factor

**3. Factor Rule Tables (`{entity}_factor_rules`)**

Purpose: Define computation rules for internally calculated factors.

Common Columns:
Column	Type	Description
id	Integer	Primary key (auto-increment)
factor_id	Foreign Key	Links to {entity}_factors.id
condition	Text	Logical condition for factor calculation
rule_type	String(50)	Rule type (e.g., "calculation", "filter")
method_ref	String(255) nullable	Reference to calculation method
🧱 Updated Folder Layout

**Infrastructure Models** (SQLAlchemy ORM):
```
src/infrastructure/models/finance/financial_assets/
├── share_factors.py                    # ShareFactor, ShareFactorValue, ShareFactorRule
├── bond_factors.py                     # BondFactor, BondFactorValue, BondFactorRule
├── security_factors.py                 # SecurityFactor, SecurityFactorValue, SecurityFactorRule
├── equity_factors.py                   # EquityFactor, EquityFactorValue, EquityFactorRule
├── currency_factors.py                 # CurrencyFactor, CurrencyFactorValue, CurrencyFactorRule
├── commodity_factors.py                # CommodityFactor, CommodityFactorValue, CommodityFactorRule
├── options_factors.py                  # OptionsFactor, OptionsFactorValue, OptionsFactorRule
├── futures_factors.py                  # FuturesFactor, FuturesFactorValue, FuturesFactorRule
├── index_factors.py                    # IndexFactor, IndexFactorValue, IndexFactorRule
├── etf_share_factors.py                # ETFShareFactor, ETFShareFactorValue, ETFShareFactorRule
└── company_share_factors.py            # CompanyShareFactor, CompanyShareFactorValue, CompanyShareFactorRule
```

**Repository Classes** (Data Access Layer):
```
src/infrastructure/repositories/local_repo/factor/finance/financial_assets/
├── base_factor_repository.py           # BaseFactorRepository with common CRUD operations
├── share_factor_repository.py          # ShareFactorRepository
├── bond_factor_repository.py           # BondFactorRepository  
├── security_factor_repository.py       # SecurityFactorRepository
├── equity_factor_repository.py         # EquityFactorRepository
├── currency_factor_repository.py       # CurrencyFactorRepository
├── commodity_factor_repository.py      # CommodityFactorRepository
├── options_factor_repository.py        # OptionsFactorRepository
├── futures_factor_repository.py        # FuturesFactorRepository
├── index_factor_repository.py          # IndexFactorRepository
├── etf_share_factor_repository.py      # ETFShareFactorRepository
└── company_share_factor_repository.py  # CompanyShareFactorRepository
```

**Domain Entities** (Business Logic - existing):
```
src/domain/entities/factor/finance/financial_assets/
├── security_factor.py                  # FactorSecurity (base class)
├── equity_factor.py                    # FactorEquity (inherits from FactorSecurity)
├── share_factor.py                     # FactorShare (inherits from FactorEquity)
└── ...                                 # Other factor domain entities
```

🧠 Design Notes

The domain layer defines factor behavior (e.g., calculation methods, validation).

The infrastructure layer manages persistence and database operations (SQLAlchemy ORM).

The repository pattern isolates data access logic to allow easy database replacement.

🧩 Example Relationship Diagram
 ┌──────────────┐          ┌────────────────────┐
 │  factors     │◄────────►│  factor_rules      │
 └──────┬───────┘          └────────────────────┘
        │
        │ 1─to─many
        ▼
 ┌────────────────────┐
 │  factor_values     │
 └────────────────────┘

🧮 Example SQLAlchemy Model Snippets
class Factor(Base):
    __tablename__ = "factors"
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    group = Column(String, nullable=False)
    subgroup = Column(String)
    data_type = Column(String, default="numeric")
    source = Column(String)
    definition = Column(Text)

    values = relationship("FactorValue", back_populates="factor")
    rules = relationship("FactorRule", back_populates="factor")


class FactorValue(Base):
    __tablename__ = "factor_values"
    id = Column(Integer, primary_key=True)
    factor_id = Column(Integer, ForeignKey("factors.id"))
    entity_id = Column(Integer, ForeignKey("shares.id"))
    date = Column(Date)
    value = Column(DECIMAL(20, 6))

    factor = relationship("Factor", back_populates="values")


class FactorRule(Base):
    __tablename__ = "factor_rules"
    id = Column(Integer, primary_key=True)
    factor_id = Column(Integer, ForeignKey("factors.id"))
    condition = Column(String)
    rule_type = Column(String)
    method_ref = Column(String)

    factor = relationship("Factor", back_populates="rules")

🧰 Repository Implementation

**BaseFactorRepository Pattern:**

All entity-specific repositories inherit from `BaseFactorRepository` which provides common CRUD operations:

```python
class BaseFactorRepository(ABC):
    """Base repository for all factor entities with common CRUD operations."""
    
    # Factory methods (abstract - implemented by subclasses)
    @abstractmethod
    def get_factor_model(self): pass
    @abstractmethod  
    def get_factor_value_model(self): pass
    @abstractmethod
    def get_factor_rule_model(self): pass
    
    # Common CRUD operations
    def create_factor(self, **kwargs): ...
    def get_by_name(self, name: str): ...
    def get_by_id(self, factor_id: int): ...
    def list_all(self) -> List: ...
    def update_factor(self, factor_id: int, **kwargs): ...
    def delete_factor(self, factor_id: int) -> bool: ...
    
    def create_factor_value(self, **kwargs): ...
    def get_by_factor_and_date(self, factor_id: int, date_value: date) -> List: ...
    def get_factor_values_by_entity(self, entity_id: int, factor_id: Optional[int] = None) -> List: ...
    
    def create_factor_rule(self, **kwargs): ...
    def get_rules_by_factor(self, factor_id: int) -> List: ...
```

**Entity-Specific Repository Example:**

```python
class ShareFactorRepository(BaseFactorRepository):
    def get_factor_model(self):
        return ShareFactor
    def get_factor_value_model(self):
        return ShareFactorValue  
    def get_factor_rule_model(self):
        return ShareFactorRule
```

**Usage Example:**

```python
# Create repository instance
repo = ShareFactorRepository()

# Create a new factor
factor = repo.create_factor(
    name="PE_Ratio",
    group="valuation", 
    subgroup="multiples",
    definition="Price to Earnings ratio"
)

# Get factor by name
pe_factor = repo.get_by_name("PE_Ratio")

# Create factor value
repo.create_factor_value(
    factor_id=factor.id,
    entity_id=123,  # share ID
    date=date(2024, 1, 1),
    value=15.5
)

# Query factor values
values = repo.get_by_factor_and_date(factor.id, date(2024, 1, 1))
```