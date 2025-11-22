# Factor Mapper - CLAUDE.md

## 📖 Overview

This directory contains the mapper responsible for converting between Factor domain entities and ORM models. The mapper implements a **precise discriminator-based approach** with **simplified base arguments mapping** for consistent and maintainable factor entity management.

---

## 🏗️ Architecture

### **Discriminator-Based Factor Mapping**

The factor mapper system uses exact domain class names as discriminators to ensure precise factor type identification and prevent conflicts between similar factor names across different domains.

---

## 📁 Directory Structure

```
factor/
├── CLAUDE.md                  # This documentation file
├── factor_mapper.py           # Core factor mapping logic
├── factor_value_mapper.py     # Factor value mapping logic
└── __init__.py
```

---

## 🎯 Discriminator System

### **Entity Type Function**

The `_get_entity_type_from_factor()` function returns **exact domain class names** as discriminators:

```python
def _get_entity_type_from_factor(factor) -> str:
    """
    Helper function to determine entity_type from factor type.
    Returns the exact domain entity class name to represent accurately what's a discriminator is.
    """
    factor_class_name = factor.__class__.__name__
    
    # Return exact domain class names as discriminators
    return factor_class_name
```

### **Discriminator Examples**

```python
# Domain Entity Class → entity_type Discriminator
ShareFactor              → "ShareFactor"
ShareMomentumFactor      → "ShareMomentumFactor"  
ShareTechnicalFactor     → "ShareTechnicalFactor"
ShareVolatilityFactor    → "ShareVolatilityFactor"
ShareTargetFactor        → "ShareTargetFactor"
CountryFactor            → "CountryFactor"
ContinentFactor          → "ContinentFactor"
```

### **Benefits of Exact Discriminators**

✅ **Precise Type Identification**: No ambiguity about factor types  
✅ **Cross-Domain Support**: Same factor names can exist across different entity types  
✅ **Future-Proof**: Automatically supports new factor types  
✅ **Database Clarity**: entity_type column clearly indicates domain class  
✅ **Query Efficiency**: Exact matching for better database performance

---

## 📋 Base Args Mapping

### **Simplified Mapping Approach**

All factor entities use a **simplified base arguments mapping** approach that focuses on core factor information only, removing complex specialized field handling.

### **Standard Base Arguments**

Every factor entity mapping uses only these essential arguments:

```python
base_args = {
    'name': orm_model.name,                # Factor name
    'group': orm_model.group,              # Factor group (price, momentum, etc.)
    'subgroup': orm_model.subgroup,        # Factor subgroup (ohlc, returns, etc.) 
    'data_type': orm_model.data_type,      # Data type (numeric, string, etc.)
    'source': orm_model.source,            # Data source (market_data, calculated, etc.)
    'definition': orm_model.definition,    # Factor definition/description
    'factor_id': orm_model.id,            # Database ID
}
```

---

## 🔄 Mapping Methods

### **Domain → ORM Conversion (to_orm)**

```python
@staticmethod
def to_orm(domain_entity: FactorEntity) -> FactorModel:
    """Convert domain entity to ORM model using only base args."""
    base_data = {
        'id': domain_entity.id,
        'name': domain_entity.name,
        'group': domain_entity.group,
        'subgroup': domain_entity.subgroup,
        'data_type': domain_entity.data_type,
        'source': domain_entity.source,
        'definition': domain_entity.definition,
        'entity_type': _get_entity_type_from_factor(domain_entity),  # Exact discriminator
    }
    
    # Always return base FactorModel with only base args
    return FactorModel(**base_data)
```

**Key Features:**
- ✅ **Uniform Output**: Always returns base FactorModel regardless of input type
- ✅ **Automatic Discriminator**: entity_type derived automatically from domain class
- ✅ **Simplified Logic**: No complex type-specific field handling
- ✅ **Maintainable**: Easy to understand and modify

### **ORM → Domain Conversion (to_domain)**

```python
@staticmethod
def to_domain(orm_model: Optional[FactorModel]) -> Optional[FactorEntity]:
    """Convert ORM model to domain entity based on entity_type discriminator."""
    if not orm_model:
        return None
    
    # Use only base args for all factor entity mappings
    base_args = {
        'name': orm_model.name,
        'group': orm_model.group,
        'subgroup': orm_model.subgroup,
        'data_type': orm_model.data_type,
        'source': orm_model.source,
        'definition': orm_model.definition,
        'factor_id': orm_model.id,
    }
    
    # Map based on entity_type discriminator to appropriate domain class
    entity_type = orm_model.entity_type
    
    if entity_type == 'ContinentFactor':
        return ContinentFactorEntity(**base_args)
    elif entity_type == 'CountryFactor':
        return CountryFactorEntity(**base_args)
    elif entity_type == 'ShareVolatilityFactor':
        return ShareVolatilityFactorEntity(**base_args)
    elif entity_type == 'ShareTargetFactor':
        return ShareTargetFactorEntity(**base_args)
    elif entity_type == 'ShareTechnicalFactor':
        return ShareTechnicalFactorEntity(**base_args)
    elif entity_type == 'ShareMomentumFactor':
        return ShareMomentumFactorEntity(**base_args)
    elif entity_type == 'ShareFactor':
        return ShareFactorEntity(**base_args)
    elif entity_type == 'EquityFactor':
        return EquityFactorEntity(**base_args)
    elif entity_type == 'SecurityFactor':
        return SecurityFactorEntity(**base_args)
    elif entity_type == 'FinancialAssetFactor':
        return FinancialAssetFactorEntity(**base_args)
    else:
        # Default to base Factor entity
        return FactorEntity(**base_args)
```

**Key Features:**
- ✅ **Discriminator-Driven**: Uses entity_type for precise domain class selection
- ✅ **Consistent Args**: All domain entities receive same base arguments
- ✅ **Fallback Support**: Graceful handling of unknown entity types
- ✅ **Type Safety**: Clear mapping from discriminator to domain class

---

## 🎯 Integration with Repositories

### **Factor Entity Verification**

Repositories now verify factor existence using **name + discriminator** combination:

```python
def get_by_name_and_discriminator(self, name: str, entity_type: str) -> Optional[FactorEntity]:
    """Retrieve a factor by its name and entity_type discriminator."""
    try:
        FactorModel = self.get_factor_model()
        factor = self.session.query(FactorModel).filter(
            FactorModel.name == name,
            FactorModel.entity_type == entity_type
        ).first()
        return self._to_domain_factor(factor)
    except Exception as e:
        print(f"Error retrieving factor by name and discriminator: {e}")
        return None
```

### **Enhanced _create_or_get_factor**

```python
def _create_or_get_factor(self, name: str, group: str, subgroup: str, data_type: str, 
                         source: str, definition: str, entity_type: str = "ShareFactor"):
    """Create factor if it doesn't exist, otherwise return existing based on name AND discriminator."""
    existing_factor = self.get_by_name_and_discriminator(name, entity_type)
    if existing_factor:
        return existing_factor
    
    return self.add_factor(...)
```

---

## 🚀 Benefits of New Approach

### **1. Simplified Maintenance**
- ❌ **Before**: Complex specialized field handling for each factor type
- ✅ **After**: Uniform base args mapping for all factor types

### **2. Enhanced Type Safety**
- ❌ **Before**: String-based entity type guessing (e.g., 'share', 'equity')
- ✅ **After**: Exact domain class names as discriminators

### **3. Cross-Domain Support**
- ❌ **Before**: Factor name conflicts between different domains
- ✅ **After**: Same factor names can exist across different entity types

### **4. Future-Proof Design**
- ❌ **Before**: New factor types required mapper modifications
- ✅ **After**: New factor types automatically supported

### **5. Database Clarity**
- ❌ **Before**: Ambiguous entity_type values
- ✅ **After**: Clear discriminator values matching domain classes

---

## 📊 Factor Value Verification

### **Unique Identification Strategy**

Factor values are verified using **factor_id + date + entity_id** combination:

```python
def get_factor_value_by_combination(self, factor_id: int, entity_id: int, date_value: date) -> Optional[FactorValueEntity]:
    """Retrieve factor value by the combination of factor_id + date + entity_id."""
    try:
        FactorValueModel = self.get_factor_value_model()
        factor_value = (
            self.session.query(FactorValueModel)
            .filter(
                FactorValueModel.factor_id == factor_id,
                FactorValueModel.entity_id == entity_id,
                FactorValueModel.date == date_value
            )
            .first()
        )
        return self._to_domain_value(factor_value)
    except Exception as e:
        print(f"Error retrieving factor value by combination: {e}")
        return None
```

**Benefits:**
- ✅ **Precise Identification**: Unique combination for each factor value
- ✅ **No Duplicates**: Prevents duplicate factor value entries
- ✅ **Efficient Queries**: Optimized for database performance
- ✅ **Clear Intent**: Obvious what combination uniquely identifies values

---

## 📝 Usage Examples

### **Creating Factor with Discriminator**

```python
# Factor creation automatically sets correct entity_type discriminator
momentum_factor = ShareMomentumFactor(
    name="momentum_20d",
    group="momentum",
    subgroup="price"
)

# When mapped to ORM, entity_type will be "ShareMomentumFactor"
orm_factor = FactorMapper.to_orm(momentum_factor)
print(orm_factor.entity_type)  # "ShareMomentumFactor"
```

### **Retrieving Factor by Name and Discriminator**

```python
# Can have same name in different entity types
share_close = repository.get_by_name_and_discriminator("Close", "ShareFactor")
country_close = repository.get_by_name_and_discriminator("Close", "CountryFactor")

# Both can coexist without conflicts
assert share_close.name == country_close.name == "Close"
assert share_close != country_close  # Different entities
```

### **Factor Value Operations**

```python
# Verify factor value exists using precise combination
exists = repository.factor_value_exists(
    factor_id=123,
    entity_id=456, 
    date_value=date(2024, 1, 15)
)

# Create or get factor value using combination verification
factor_value = repository._create_or_get_factor_value(
    factor_id=123,
    entity_id=456,
    date_value=date(2024, 1, 15),
    value=Decimal('100.50')
)
```

---

## 🔮 Future Enhancements

### **Planned Improvements**
- [ ] Automated discriminator validation
- [ ] Performance metrics for discriminator queries
- [ ] Enhanced error handling for invalid discriminators
- [ ] Caching layer for discriminator mappings

### **Migration Support**
- [ ] Legacy entity_type migration utilities
- [ ] Backward compatibility for old discriminators
- [ ] Data validation tools for discriminator consistency