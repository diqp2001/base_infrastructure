# CLAUDE.md - Domain Entities Layer

## 🧠 Domain Entities Responsibilities

This directory contains the **core business logic** of the `base_infrastructure` project, following **Domain-Driven Design (DDD)** principles.

---

## 📋 Layer Responsibilities

### ✅ What Domain Entities ARE Responsible For:

1. **Pure Business Logic**
   - Core domain rules and invariants
   - Business calculations and validations
   - Domain-specific algorithms and computations
   - Entity state management and behavior

2. **Domain Model Definition**
   - Define rich domain objects with behavior
   - Encapsulate business rules within entities
   - Provide domain-specific methods and properties
   - Maintain entity relationships and constraints

3. **Technology-Agnostic Design**
   - Independent of frameworks (no SQLAlchemy, Flask, etc.)
   - No database or persistence concerns
   - No external API dependencies
   - Pure Python business objects

4. **Factor System Core Logic**
   - Factor calculation algorithms (momentum, technical indicators, volatility)
   - Financial asset modeling and behavior
   - Geographic and market-specific business rules
   - Factor value validation and computation

### ❌ What Domain Entities are NOT Responsible For:

1. **Data Persistence**
   - No direct database operations
   - No SQLAlchemy models or ORM concerns
   - No repository pattern implementation
   - No data access layer responsibilities

2. **Infrastructure Concerns**
   - No HTTP requests or API calls
   - No file system operations
   - No caching mechanisms
   - No logging or monitoring

3. **Framework Dependencies**
   - No Flask, FastAPI, or web framework code
   - No external library integrations
   - No configuration management
   - No dependency injection containers

---

## 🏗️ Architecture Overview

```
src/domain/entities/
├── factor/                     # Factor domain models
│   ├── factor.py              # Base factor entity (abstract)
│   ├── factor_value.py        # Factor value entity
│   ├── continent_factor.py    # Geographic factor entities
│   ├── country_factor.py
│   └── finance/
│       └── financial_assets/
│           ├── financial_asset_factor.py
│           ├── security_factor.py
│           ├── equity_factor.py
│           └── share_factor/
│               ├── share_factor.py
│               ├── share_momentum_factor.py     # Rich calculation logic
│               ├── share_technical_factor.py    # Technical indicators
│               ├── share_target_factor.py       # ML training targets
│               └── share_volatility_factor.py   # Risk calculations
└── [other business domains]/
```

---

## 💼 Factor Domain Patterns

### 1. **Inheritance Hierarchy**
- `Factor` (abstract base) → `FinancialAssetFactor` → `SecurityFactor` → `EquityFactor` → `ShareFactor`
- Each level adds domain-specific properties and behavior
- Specialized share factors extend `ShareFactor` with calculation methods

### 2. **Rich Domain Methods**
```python
class ShareMomentumFactor(ShareFactor):
    def calculate_momentum(self, prices: List[float]) -> Optional[float]:
        """Domain logic for momentum calculation"""
        
    def is_short_term(self) -> bool:
        """Business rule for momentum classification"""
```

### 3. **Validation and Invariants**
```python
class ShareTechnicalFactor(ShareFactor):
    def validate_period(self) -> bool:
        """Business rule validation"""
        return self.period >= 2 and self.period <= 200
```

### 4. **Immutable Value Objects**
```python
@dataclass(frozen=True)
class FactorValue:
    """Immutable value object for factor calculations"""
    factor_id: int
    entity_id: int
    entity_type: str
    date: date
    value: Decimal
```

---

## 🧪 Testing Guidelines

### Domain Entity Testing:
- **Unit tests only** - no integration tests in domain layer
- **Mock-free testing** - domain entities should not require mocks
- **Business logic focus** - test calculations, validations, and rules
- **Fast execution** - no database or external dependencies

### Test Structure:
```python
class TestShareMomentumFactor:
    def test_calculate_momentum_with_valid_prices(self):
        """Test business calculation logic"""
        
    def test_momentum_classification_rules(self):
        """Test business rule validation"""
        
    def test_invalid_input_handling(self):
        """Test domain invariant enforcement"""
```

---

## 📚 Key Principles

### 1. **Ubiquitous Language**
- Use domain expert terminology in code
- Factor names match financial industry standards
- Method names reflect business operations

### 2. **Aggregates and Roots**
- `Factor` entities are aggregate roots
- `FactorValue` entities belong to Factor aggregates
- Maintain consistency within aggregate boundaries

### 3. **Domain Services** (when needed)
- Complex business logic spanning multiple entities
- Domain calculations requiring multiple factors
- Market-specific business rules and validations

### 4. **Value Objects**
- Immutable objects for factor values
- Money, dates, and calculation results as value objects
- Equality based on value, not identity

---

## 🔄 Integration with Other Layers

### Domain → Infrastructure:
- Domain entities are mapped to ORM models via **mappers**
- No direct dependencies on infrastructure
- Pure business objects converted for persistence

### Domain ← Application:
- Application services orchestrate domain operations
- Use cases coordinate multiple domain entities
- Application layer handles cross-cutting concerns

### Domain ↔ Interfaces:
- API controllers consume domain entities via application services
- Web interfaces display domain data through DTOs
- No direct coupling between domain and presentation layers

---

## ⚡ Performance Considerations

### Calculation Efficiency:
- Domain calculations should be optimized for business logic clarity
- Avoid premature optimization in domain layer
- Complex computations may use specialized libraries (numpy, pandas) when appropriate
- Cache-heavy operations should be handled in application/infrastructure layers

### Memory Management:
- Factor calculations may process large datasets
- Use generators and iterators for large data processing
- Minimize object creation in calculation loops
- Leverage immutable objects to prevent side effects

---

## 🔮 Future Enhancements

### Planned Domain Extensions:
- [ ] Options and derivatives factor calculations
- [ ] ESG (Environmental, Social, Governance) factors
- [ ] Alternative data factor models
- [ ] Multi-asset portfolio factor calculations
- [ ] Real-time factor streaming calculations

### Domain Service Opportunities:
- [ ] Factor combination and blending services
- [ ] Risk adjustment calculations across factor types  
- [ ] Benchmark and universe-relative factor calculations
- [ ] Factor decay and lifecycle management

---

**Key Takeaway**: This layer contains the **heart of the business logic**. Keep it pure, focused, and technology-agnostic. All factor calculations, validations, and business rules live here.