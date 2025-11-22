# Factor Repository - CLAUDE.md

## 📖 Overview

This directory contains the BaseFactorRepository, which handles CRUD operations for Factor entities with enhanced discriminator-based verification and simplified mapping patterns. The repository implements **precise factor identification** using name + discriminator combinations and **factor value uniqueness** using factor_id + date + entity_id combinations.

---

## 🏗️ Repository Architecture

### **Enhanced Verification System**

The BaseFactorRepository now implements a **dual verification approach**:

1. **Factor Entities**: Verified by `name + entity_type` (discriminator) combination
2. **Factor Values**: Verified by `factor_id + date + entity_id` combination

This ensures precise entity identification and prevents conflicts while maintaining data integrity.

---

## 📁 Directory Structure

```
factor/
├── CLAUDE.md                      # This documentation file
├── base_factor_repository.py      # Core factor repository with enhanced verification
└── __init__.py
```

---

## 🎯 Factor Entity Verification

### **Name + Discriminator Pattern**

Factors are now verified using the **name + entity_type discriminator** combination instead of name alone:

```python
def get_by_name_and_discriminator(self, name: str, entity_type: str) -> Optional[FactorEntity]:
    """Retrieve a factor by its name and entity_type discriminator."""
    try:
        FactorModel = self.get_factor_model()
        factor = self.session.query(FactorModel).filter(
            FactorModel.name == name,
            FactorModel.entity_type == entity_type  # Discriminator verification
        ).first()
        return self._to_domain_factor(factor)
    except Exception as e:
        print(f"Error retrieving factor by name and discriminator: {e}")
        return None
```

### **Enhanced _create_or_get_factor**

The core factory method now supports discriminator-based creation:

```python
def _create_or_get_factor(self, name: str, group: str, subgroup: str, data_type: str, 
                         source: str, definition: str, entity_type: str = "ShareFactor"):
    """Create factor if it doesn't exist, otherwise return existing based on name AND discriminator."""
    existing_factor = self.get_by_name_and_discriminator(name, entity_type)
    if existing_factor:
        return existing_factor
    
    return self.add_factor(
        name=name,
        group=group,
        subgroup=subgroup,
        data_type=data_type,
        source=source,
        definition=definition
    )
```

### **Benefits of Discriminator Verification**

✅ **Cross-Domain Support**: Same factor names can exist across different entity types
- Example: "Close" factor can exist for ShareFactor, CountryFactor, etc.

✅ **Precise Identification**: No ambiguity about which factor type is being referenced

✅ **Future-Proof**: Automatically supports new factor types without conflicts

✅ **Database Efficiency**: Exact matching improves query performance

---

## 📋 Factor Value Verification

### **Triple-Key Combination**

Factor values are verified using the **factor_id + date + entity_id** combination for unique identification:

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

### **Enhanced Factor Value Creation**

```python
def _create_or_get_factor_value(self, factor_id: int, entity_id: int, date_value: date, value) -> Optional[FactorValueEntity]:
    """
    Create factor value if it doesn't exist, otherwise return existing.
    Verification is based on combination of factor_id + date + entity_id.
    """
    # Check if value already exists using factor_id + date + entity_id combination
    existing_value = self.get_factor_value_by_combination(factor_id, entity_id, date_value)
    if existing_value:
        return existing_value
    
    return self.add_factor_value(factor_id, entity_id, date_value, value)
```

### **Updated Existence Check**

```python
def factor_value_exists(self, factor_id: int, entity_id: int, date_value: date) -> bool:
    """
    Check if a factor value already exists for the given factor_id, entity_id, and date.
    Verification is based on combination of factor_id + date + entity_id as requested.
    """
    try:
        FactorValueModel = self.get_factor_value_model()
        existing_value = (
            self.session.query(FactorValueModel)
            .filter(
                FactorValueModel.factor_id == factor_id,
                FactorValueModel.entity_id == entity_id,
                FactorValueModel.date == date_value
            )
            .first()
        )
        return existing_value is not None
    except Exception as e:
        print(f"Error checking factor value existence: {e}")
        return False
```

---

## 🔄 Integration with Services

### **Service Layer Usage**

The repository now integrates seamlessly with the service layer while maintaining clear separation of concerns:

```python
# Services call repository with discriminator information
class FactorCreationService:
    def get_or_create_factor(self, config: Dict[str, Any]) -> Optional[Factor]:
        entity_type = self._determine_entity_type(config)
        
        # Repository handles discriminator-based verification
        return self.base_factor_repository._create_or_get_factor(
            name=config['name'],
            group=config['group'],
            subgroup=config.get('subgroup'),
            data_type=config.get('data_type', 'numeric'),
            source=config.get('source', 'calculated'),
            definition=config.get('definition', ''),
            entity_type=entity_type  # Exact discriminator
        )
```

### **FactorDataService Integration**

```python
class FactorDataService:
    def create_or_get_factor(self, name: str, group: str, subgroup: str, 
                           data_type: str, source: str, definition: str, 
                           entity_type: str = "ShareFactor") -> Optional[Factor]:
        """Service method that delegates to repository with discriminator."""
        try:
            return self.base_factor_repository._create_or_get_factor(
                name=name, group=group, subgroup=subgroup,
                data_type=data_type, source=source, definition=definition,
                entity_type=entity_type  # Pass discriminator through
            )
        except Exception as e:
            print(f"Error creating/retrieving factor: {e}")
            return None
```

---

## 🎯 Usage Examples

### **Creating Factors with Discriminators**

```python
# Create ShareFactor "Close"
share_close = repository._create_or_get_factor(
    name="Close",
    group="price", 
    subgroup="ohlc",
    data_type="numeric",
    source="market_data",
    definition="Daily closing price",
    entity_type="ShareFactor"
)

# Create CountryFactor "Close" (different discriminator, same name)
country_close = repository._create_or_get_factor(
    name="Close",
    group="economic",
    subgroup="market",
    data_type="numeric", 
    source="central_bank",
    definition="Daily market close indicator",
    entity_type="CountryFactor"
)

# Both coexist without conflicts
assert share_close.name == country_close.name == "Close"
assert share_close.id != country_close.id  # Different database records
```

### **Factor Value Operations with Triple-Key**

```python
# Check if specific factor value exists
exists = repository.factor_value_exists(
    factor_id=123,      # Specific factor
    entity_id=456,      # Specific entity (company share)
    date_value=date(2024, 1, 15)  # Specific date
)

if not exists:
    # Create new factor value with precise identification
    factor_value = repository._create_or_get_factor_value(
        factor_id=123,
        entity_id=456, 
        date_value=date(2024, 1, 15),
        value=Decimal('150.75')
    )
    print(f"Created factor value: {factor_value.value}")
else:
    # Retrieve existing value
    existing_value = repository.get_factor_value_by_combination(
        factor_id=123,
        entity_id=456,
        date_value=date(2024, 1, 15)
    )
    print(f"Existing factor value: {existing_value.value}")
```

### **Bulk Factor Operations**

```python
# Create multiple factors with different discriminators
factor_configs = [
    {
        'name': 'momentum_20d', 
        'group': 'momentum',
        'entity_type': 'ShareMomentumFactor'
    },
    {
        'name': 'rsi_14',
        'group': 'technical', 
        'entity_type': 'ShareTechnicalFactor'
    },
    {
        'name': 'vol_30d',
        'group': 'volatility',
        'entity_type': 'ShareVolatilityFactor' 
    }
]

created_factors = []
for config in factor_configs:
    factor = repository._create_or_get_factor(
        name=config['name'],
        group=config['group'],
        subgroup='',
        data_type='numeric',
        source='calculated',
        definition=f"{config['name']} factor",
        entity_type=config['entity_type']  # Precise discriminator
    )
    created_factors.append(factor)

print(f"Created {len(created_factors)} factors with precise discriminators")
```

---

## 📊 Performance Benefits

### **Query Optimization**

The discriminator-based approach provides several performance benefits:

✅ **Exact Matching**: Database can use precise index lookups instead of pattern matching

✅ **Reduced Conflicts**: Fewer false positives when searching for factors

✅ **Efficient Joins**: Clear factor type identification improves join performance

✅ **Index Utilization**: Compound indexes on (name, entity_type) improve query speed

### **Database Schema Advantages**

```sql
-- Efficient compound index for factor lookups
CREATE INDEX idx_factors_name_entity_type ON factors(name, entity_type);

-- Triple-key index for factor values
CREATE INDEX idx_factor_values_combination ON factor_values(factor_id, entity_id, date);
```

---

## 🔧 Migration Considerations

### **Backward Compatibility**

The repository maintains backward compatibility while introducing enhanced verification:

```python
# Legacy method still works (with default discriminator)
def get_by_name(self, name: str) -> Optional[FactorEntity]:
    """Legacy method - uses ShareFactor as default discriminator."""
    return self.get_by_name_and_discriminator(name, "ShareFactor")
```

### **Data Migration Support**

```python
# Helper method for migrating existing factors to new discriminator system
def migrate_legacy_factors(self):
    """Migrate factors without entity_type to have proper discriminators."""
    factors_without_discriminator = self.session.query(FactorModel).filter(
        FactorModel.entity_type.is_(None)
    ).all()
    
    for factor in factors_without_discriminator:
        # Infer entity_type from factor characteristics
        factor.entity_type = self._infer_entity_type(factor)
        
    self.session.commit()
    print(f"Migrated {len(factors_without_discriminator)} factors")
```

---

## 🚀 Benefits Summary

### **1. Enhanced Precision**
- ❌ **Before**: Factor conflicts between different domains
- ✅ **After**: Precise factor identification with discriminators

### **2. Improved Data Integrity**
- ❌ **Before**: Potential duplicate factor values
- ✅ **After**: Unique identification using triple-key combination

### **3. Better Performance**
- ❌ **Before**: Ambiguous queries and false matches
- ✅ **After**: Exact database matching with optimized indexes

### **4. Future-Proof Design**
- ❌ **Before**: Manual factor type management
- ✅ **After**: Automatic discriminator derivation from domain classes

### **5. Clean Architecture**
- ❌ **Before**: Repository directly called by managers
- ✅ **After**: Service layer abstraction with proper DDD layering

---

## 📝 Testing Considerations

### **Unit Tests for Discriminator Logic**

```python
def test_factor_creation_with_discriminator():
    """Test that factors are created with correct discriminators."""
    # Create ShareMomentumFactor
    momentum_factor = repository._create_or_get_factor(
        name="test_momentum",
        group="momentum",
        entity_type="ShareMomentumFactor"
    )
    
    # Verify discriminator is set correctly
    orm_factor = repository.session.query(FactorModel).filter(
        FactorModel.id == momentum_factor.id
    ).first()
    
    assert orm_factor.entity_type == "ShareMomentumFactor"
    assert orm_factor.name == "test_momentum"

def test_factor_value_uniqueness():
    """Test that factor values are unique by triple-key combination."""
    # Create first value
    value1 = repository._create_or_get_factor_value(
        factor_id=1, entity_id=1, date_value=date(2024, 1, 1), value=100.0
    )
    
    # Attempt to create duplicate (should return existing)
    value2 = repository._create_or_get_factor_value(
        factor_id=1, entity_id=1, date_value=date(2024, 1, 1), value=200.0
    )
    
    # Should return same entity
    assert value1.id == value2.id
    assert value1.value == value2.value  # Original value preserved
```

---

## 🔮 Future Enhancements

### **Planned Improvements**
- [ ] Automated discriminator validation on factor creation
- [ ] Performance monitoring for discriminator-based queries
- [ ] Enhanced error messages for discriminator mismatches
- [ ] Bulk operations optimization for large factor datasets

### **Advanced Features**
- [ ] Factor relationship tracking across discriminators
- [ ] Cross-domain factor dependencies
- [ ] Discriminator-aware caching strategies
- [ ] Automated factor type inference for migration scenarios