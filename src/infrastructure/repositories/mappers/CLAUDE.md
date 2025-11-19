# CLAUDE.md - Repository Mappers Layer

## 🔄 Repository Mappers Responsibilities

This directory contains **bidirectional mappers** that handle conversion between **Domain Entities** and **Infrastructure ORM Models**, following the **Repository Pattern** in DDD architecture.

---

## 📋 Layer Responsibilities

### ✅ What Repository Mappers ARE Responsible For:

1. **Domain ↔ Infrastructure Conversion**
   - Convert domain entities to ORM models for persistence
   - Convert ORM models to domain entities for business logic
   - Handle type-safe bidirectional mapping
   - Maintain data integrity during conversion

2. **Polymorphic Type Resolution**
   - Map discriminator values to correct domain entity types
   - Handle inheritance hierarchies in both directions
   - Route specialized factor types to appropriate classes
   - Manage type-specific attribute mapping

3. **Data Type Transformation**
   - Convert between domain value types and database types
   - Handle Decimal ↔ Numeric conversions for financial precision
   - Transform string booleans ('true'/'false') to boolean values
   - Process date/datetime conversions

4. **Attribute Mapping Logic**
   - Map specialized columns to domain entity properties
   - Handle optional/nullable field mappings
   - Manage complex attribute transformations
   - Provide safe defaults for missing attributes

### ❌ What Repository Mappers are NOT Responsible For:

1. **Business Logic**
   - No domain calculations or validations
   - No business rule enforcement
   - No domain-specific algorithms
   - No entity behavior implementation

2. **Data Persistence Operations**
   - No database queries or transactions
   - No session management
   - No CRUD operations
   - No repository pattern implementation

3. **Data Validation**
   - No business rule validation
   - No domain constraint checking
   - No data quality assurance beyond type safety
   - No schema validation

---

## 🏗️ Architecture Overview

```
src/infrastructure/repositories/mappers/
├── factor/
│   ├── factor_mapper.py           # Core factor entity ↔ model mapping
│   ├── factor_value_mapper.py     # Factor value mapping
│   └── finance/financial_assets/
│       ├── financial_asset_factor_value_mapper.py
│       ├── security_factor_value_mapper.py
│       ├── equity_factor_value_mapper.py
│       └── share_factor_value_mapper.py
├── finance/financial_assets/
│   ├── company_share_mapper.py
│   ├── security_mapper.py
│   └── currency_mapper.py
└── continent_mapper.py
```

---

## 🎯 Factor Mapper System

### 1. **Core FactorMapper Design**
```python
class FactorMapper:
    @staticmethod
    def to_domain(orm_model: FactorModel) -> Optional[FactorEntity]:
        """Convert ORM model to domain entity based on discriminator."""
        factor_type = orm_model.factor_type
        
        # Route to appropriate domain entity based on discriminator
        if factor_type == 'share_momentum':
            return ShareMomentumFactorEntity(
                **base_args,
                period=orm_model.period,
                momentum_type=orm_model.momentum_type,
            )
        # ... handle other factor types
    
    @staticmethod  
    def to_orm(domain_entity: FactorEntity) -> FactorModel:
        """Convert domain entity to ORM model based on type."""
        # Determine correct polymorphic ORM class
        if isinstance(domain_entity, ShareMomentumFactorEntity):
            return ShareMomentumFactor(
                **base_data,
                period=domain_entity.period,
                momentum_type=domain_entity.momentum_type,
            )
        # ... handle other entity types
```

### 2. **Type-Safe Discriminator Mapping**
```python
# Domain Entity Type → Discriminator Value → ORM Model
ShareMomentumFactorEntity → 'share_momentum' → ShareMomentumFactor
ShareTechnicalFactorEntity → 'share_technical' → ShareTechnicalFactor
ShareTargetFactorEntity → 'share_target' → ShareTargetFactor
ShareVolatilityFactorEntity → 'share_volatility' → ShareVolatilityFactor
ContinentFactorEntity → 'continent' → ContinentFactor
CountryFactorEntity → 'country' → CountryFactor
```

### 3. **Intelligent Attribute Handling**
```python
# Safe attribute access with fallbacks
asset_class=getattr(domain_entity, 'asset_class', None),
currency=getattr(domain_entity, 'currency', None),
is_developed='true' if domain_entity.is_developed else 'false' if domain_entity.is_developed is False else None,
```

---

## 💱 Data Type Conversion Patterns

### 1. **Financial Precision Handling**
```python
# Domain → ORM: Maintain Decimal precision
value=domain_entity.value  # Decimal stays as Decimal for ORM

# ORM → Domain: Safe Decimal conversion
value=Decimal(str(orm_model.value)) if orm_model.value is not None else Decimal('0')
```

### 2. **Boolean String Conversion**
```python
# Domain boolean → ORM string
is_developed='true' if domain_entity.is_developed else 'false' if domain_entity.is_developed is False else None

# ORM string → Domain boolean  
is_developed=orm_model.is_developed == 'true' if orm_model.is_developed else None
```

### 3. **Optional Field Management**
```python
# Safe handling of optional attributes
continent_code=orm_model.continent_code,
geographic_zone=orm_model.geographic_zone,
# These can be None and mapper handles gracefully
```

---

## 🔍 Polymorphic Resolution Strategy

### 1. **Domain → ORM Resolution**
```python
def to_orm(domain_entity: FactorEntity) -> FactorModel:
    """Uses isinstance() checks in inheritance hierarchy order."""
    
    # Most specific types first
    if isinstance(domain_entity, ShareVolatilityFactorEntity):
        return ShareVolatilityFactor(...)
    elif isinstance(domain_entity, ShareTargetFactorEntity):
        return ShareTargetFactor(...)
    # ... more specific types
    elif isinstance(domain_entity, ShareFactorEntity):
        return ShareFactor(...)
    # ... less specific types
    else:
        return FactorModel(...)  # Base case
```

### 2. **ORM → Domain Resolution**
```python
def to_domain(orm_model: FactorModel) -> FactorEntity:
    """Uses discriminator string matching."""
    
    factor_type = orm_model.factor_type
    
    # Direct discriminator mapping
    type_mapping = {
        'share_momentum': ShareMomentumFactorEntity,
        'share_technical': ShareTechnicalFactorEntity,
        'share_target': ShareTargetFactorEntity,
        'share_volatility': ShareVolatilityFactorEntity,
        # ... all other types
    }
    
    entity_class = type_mapping.get(factor_type, FactorEntity)
    return entity_class(**mapped_attributes)
```

### 3. **Inheritance Order Importance**
```python
# Check subclasses before parent classes to avoid incorrect mapping
isinstance(entity, ShareVolatilityFactorEntity)  # Check first
isinstance(entity, ShareFactorEntity)           # Check after
isinstance(entity, EquityFactorEntity)          # Check after
isinstance(entity, FactorEntity)               # Check last
```

---

## 🔧 Advanced Mapping Patterns

### 1. **Attribute Validation and Sanitization**
```python
def to_domain(orm_model: FactorModel) -> FactorEntity:
    # Validate required attributes
    base_args = {
        'name': orm_model.name or 'Unknown',  # Provide defaults
        'group': orm_model.group or 'General',
        'factor_id': orm_model.id,
    }
    
    # Type-specific validation
    if factor_type == 'share_momentum':
        period = max(1, orm_model.period or 20)  # Ensure valid period
        return ShareMomentumFactorEntity(**base_args, period=period)
```

### 2. **Complex Object Construction**
```python
def to_orm(domain_entity: FactorEntity) -> FactorModel:
    # Extract base attributes common to all factors
    base_data = {
        'id': domain_entity.id,
        'name': domain_entity.name,
        'group': domain_entity.group,
        'subgroup': domain_entity.subgroup,
        'data_type': domain_entity.data_type,
        'source': domain_entity.source,
        'definition': domain_entity.definition,
    }
    
    # Add type-specific attributes
    if isinstance(domain_entity, ShareMomentumFactorEntity):
        specialized_data = {
            **base_data,
            'period': domain_entity.period,
            'momentum_type': domain_entity.momentum_type,
        }
        return ShareMomentumFactor(**specialized_data)
```

### 3. **Null Handling Strategy**
```python
# Consistent null handling across all mappers
def safe_get_attr(obj, attr, default=None):
    """Safely get attribute with proper default handling."""
    value = getattr(obj, attr, default)
    return value if value is not None else default

# Usage in mappers
ticker_symbol=safe_get_attr(domain_entity, 'ticker_symbol', None),
share_class=safe_get_attr(domain_entity, 'share_class', None),
```

---

## ⚡ Performance Considerations

### 1. **Lazy Loading Compatibility**
```python
# Mappers should work with lazy-loaded relationships
def to_domain(orm_model: FactorModel) -> FactorEntity:
    # Don't trigger lazy loading unless necessary
    factor_values = getattr(orm_model, '_factor_values', None)
    # Only access if already loaded
```

### 2. **Batch Conversion Optimization**
```python
@staticmethod
def to_domain_list(orm_models: List[FactorModel]) -> List[FactorEntity]:
    """Efficient bulk conversion for large datasets."""
    return [FactorMapper.to_domain(model) for model in orm_models if model]

@staticmethod  
def to_orm_list(domain_entities: List[FactorEntity]) -> List[FactorModel]:
    """Efficient bulk conversion for batch operations."""
    return [FactorMapper.to_orm(entity) for entity in domain_entities if entity]
```

### 3. **Memory Efficiency**
```python
# Avoid creating unnecessary intermediate objects
def to_domain(orm_model: FactorModel) -> FactorEntity:
    # Build arguments dictionary once
    args = self._build_base_args(orm_model)
    args.update(self._build_specialized_args(orm_model))
    return EntityClass(**args)
```

---

## 🧪 Testing Strategy

### 1. **Bidirectional Conversion Testing**
```python
def test_factor_mapper_round_trip():
    """Test Domain → ORM → Domain conversion maintains data integrity."""
    original_entity = ShareMomentumFactorEntity(...)
    orm_model = FactorMapper.to_orm(original_entity)
    converted_entity = FactorMapper.to_domain(orm_model)
    
    assert original_entity.name == converted_entity.name
    assert original_entity.period == converted_entity.period
```

### 2. **Polymorphic Type Testing**
```python
def test_discriminator_mapping():
    """Test all factor types map to correct discriminator values."""
    for entity_class, expected_discriminator in TYPE_MAPPING.items():
        entity = entity_class(...)
        orm_model = FactorMapper.to_orm(entity)
        assert orm_model.factor_type == expected_discriminator
```

### 3. **Edge Case Testing**
```python
def test_null_attribute_handling():
    """Test mapper handles None/null values gracefully."""
    orm_model = FactorModel(name="Test", group="Test", period=None)
    entity = FactorMapper.to_domain(orm_model)
    # Should not raise exceptions, should provide sensible defaults
```

---

## 🔄 Integration with Repository Layer

### 1. **Repository Usage Pattern**
```python
class BaseFactorRepository:
    def _to_entity(self, orm_model) -> Optional[FactorEntity]:
        """Delegate to mapper for conversion."""
        return FactorMapper.to_domain(orm_model)
    
    def _to_model(self, domain_entity) -> FactorModel:
        """Delegate to mapper for conversion."""
        return FactorMapper.to_orm(domain_entity)
```

### 2. **Transaction Boundary Respect**
```python
# Mappers don't manage transactions
def create_factor(self, entity: FactorEntity) -> Optional[FactorEntity]:
    orm_model = FactorMapper.to_orm(entity)  # Pure conversion
    self.session.add(orm_model)              # Repository handles persistence
    self.session.commit()                    # Repository manages transaction
    return FactorMapper.to_domain(orm_model) # Pure conversion
```

---

## 🔮 Evolution Strategy

### 1. **Adding New Factor Types**
```python
# Extend discriminator mapping
FACTOR_TYPE_MAPPING = {
    'new_factor_type': NewFactorTypeEntity,
    # ... existing mappings
}

# Add conversion logic
def to_domain(orm_model: FactorModel):
    if factor_type == 'new_factor_type':
        return NewFactorTypeEntity(...)
```

### 2. **Schema Evolution Support**
```python
# Handle new optional columns gracefully
new_column_value=getattr(orm_model, 'new_column', None),

# Provide migration support for data transformations
def migrate_old_format(orm_model: FactorModel):
    if hasattr(orm_model, 'old_column'):
        return transform_old_to_new(orm_model.old_column)
    return orm_model.new_column
```

---

**Key Takeaway**: Mappers are the **translation layer** between domain entities and infrastructure models. They must be **bidirectional**, **type-safe**, and **performance-conscious** while maintaining **clean separation** between domain logic and persistence concerns.