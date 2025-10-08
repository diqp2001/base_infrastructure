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

🗄️ Database Design
1. Factor Definition Table — factors

Purpose:
Stores all available factors and their metadata.

Columns:

Column	Type	Description
id	UUID / Integer	Primary key (Factor ID)
name	String	Factor name
group	String	Logical group (e.g. "momentum", "valuation")
subgroup	String (nullable)	Optional subgroup
data_type	String	Type of value (numeric, categorical, etc.)
source	String	Data origin (internal, external)
definition	Text	Description or definition of the factor
2. Factor Value Table — factor_values

Purpose:
Stores factor values linked to specific financial entities on specific dates.

Columns:

Column	Type	Description
id	UUID / Integer	Primary key
factor_id	Foreign Key (factors.id)	Links to factor definition
entity_id	Foreign Key (shares.id or securities.id)	The related asset
date	Date	Date of the factor value
value	Decimal	The numeric value of the factor
3. Internal Factor Rule Table — factor_rules

Purpose:
Describes internally defined factors and their computation rules or logic reference.

Columns:

Column	Type	Description
id	UUID / Integer	Primary key
factor_id	Foreign Key (factors.id)	The factor this rule defines
condition	String	Logical condition (for simple computed factors)
rule_type	Enum(bool, numeric, custom)	Rule type
method_ref	String (nullable)	Name of a method or function implemented in code (e.g. FactorEquity.calculate_pe_ratio)
🧱 Folder Layout
src/
├── domain/
│   └── entities/
│       └── factor/
│           └── finance/
│               └── financial_assets/
│                   ├── factor_security.py
│                   └── factor_equity.py
├── infrastructure/
│   └── models/
│       └── finance/
                └── financial_assets/
│                   ├── factor_security_model.py
│                   └── factor_equity_model.py
                    ├── factor_security_value_model.py
│                   └── factor_equity_value_model.py
                    ├── factor_security_rule_model.py
│                   └── factor_equity_rule_model.py
│           
│   └── repositories/
│       └── local_repo/
            └── factor/
    │           └── finance/
                    └── financial_assets/
                    │               ├── factor_repository.py ← CRUD for all 3 tables
                    │               └── factor_value_repository.py
                                    └── factor_rule_repository.py

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

🧰 Repository Example

Each repository will inherit from a base class like BaseRepository (already in your infrastructure).

Example:

class FactorRepository(BaseRepository):
    def get_by_name(self, name: str) -> Optional[Factor]:
        return self.session.query(Factor).filter_by(name=name).first()

class FactorValueRepository(BaseRepository):
    def get_by_factor_and_date(self, factor_id: int, date: date):
        return self.session.query(FactorValue).filter_by(factor_id=factor_id, date=date).all()

class FactorRuleRepository(BaseRepository):
    def get_rules_for_factor(self, factor_id: int):
        return self.session.query(FactorRule).filter_by(factor_id=factor_id).all()