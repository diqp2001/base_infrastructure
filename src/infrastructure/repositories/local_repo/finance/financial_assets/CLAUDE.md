# CLAUDE.md - Financial Assets Repositories

## 🏦 Financial Assets Repository Layer

This directory contains repository implementations for financial asset entities, providing the infrastructure layer for data persistence and retrieval in the Domain-Driven Design (DDD) architecture.

---

## 📁 Directory Structure

```
financial_assets/
├── financial_asset_base_repository.py  # Base repository for all financial assets
├── company_share_repository.py         # Company share entity persistence
├── bond_repository.py                  # Bond entity persistence  
├── currency_repository.py              # Currency entity persistence
└── share_repository.py                 # Share entity base class
```

---

## 🎯 Standardized Entity Creation Pattern

### Implementation Standard

All repositories in this directory now implement the **standardized entity creation pattern** following the same approach as `BaseFactorRepository._create_or_get_factor()`:

```python
def _create_or_get_entity(self, unique_identifier: str, **kwargs) -> Optional[EntityType]:
    """
    Create entity if it doesn't exist, otherwise return existing.
    
    Args:
        unique_identifier: The unique field used to check existence
        **kwargs: Additional entity creation parameters
        
    Returns:
        EntityType: Created or existing entity
    """
    # 1. Check if entity already exists by unique identifier
    existing_entity = self.get_by_unique_field(unique_identifier)
    if existing_entity:
        return existing_entity
    
    # 2. Generate next sequential ID
    next_id = self._get_next_available_entity_id()
    
    # 3. Create new entity with proper error handling
    try:
        new_entity = EntityType(id=next_id, unique_field=unique_identifier, **kwargs)
        return self.add(new_entity)
    except Exception as e:
        print(f"Error creating entity {unique_identifier}: {str(e)}")
        return None
```

### Key Components

1. **Unique Identifier Check**: Each entity type has a specific unique field (e.g., ticker for CompanyShare)
2. **Sequential ID Generation**: Uses `_get_next_available_*_id()` method for ID assignment
3. **Error Handling**: Graceful failure with logging
4. **Consistent Pattern**: Same structure across all entity repositories

---

## 🏢 CompanyShareRepository

### Enhanced Methods

- **`_create_or_get_company_share()`**: Standardized entity creation
- **`_get_next_available_company_share_id()`**: Sequential ID generation  
- **OpenFIGI Integration**: Optional data enrichment via external API
- **Bulk Operations**: Efficient mass entity creation

### Usage Example

```python
# Use standardized creation pattern
share = repository._create_or_get_company_share(
    ticker="AAPL",
    exchange_id=1,
    company_name="Apple Inc.",
    sector="Technology"
)
```

### Integration with Factor Manager

The `FactorEnginedDataManager._ensure_entities_exist()` method has been updated to use the standardized pattern:

```python
def _ensure_entities_exist(self, tickers: List[str]) -> Dict[str, Any]:
    """Uses standardized _create_or_get_company_share pattern."""
    for ticker in tickers:
        share = self.company_share_repository._create_or_get_company_share(
            ticker=ticker,
            exchange_id=1,
            company_name=f"{ticker} Inc.",
            sector="Technology"
        )
```

---

## 🔄 Migration Benefits

### Before Standardization
- Inconsistent entity creation patterns
- Manual duplicate checking
- Varied error handling approaches
- Different ID generation strategies

### After Standardization  
- ✅ Consistent `_create_or_get_*` pattern across all repositories
- ✅ Automatic duplicate prevention
- ✅ Standardized error handling and logging
- ✅ Sequential ID generation with collision avoidance
- ✅ Improved maintainability and reliability

---

## 🧪 Testing Considerations

When testing repositories with the standardized pattern:

```python
def test_create_or_get_pattern(self):
    """Test the standardized entity creation pattern."""
    # First call should create new entity
    entity1 = repository._create_or_get_entity("unique_id")
    assert entity1 is not None
    
    # Second call should return existing entity  
    entity2 = repository._create_or_get_entity("unique_id")
    assert entity1.id == entity2.id
```

---

## 📚 Related Documentation

- `/src/infrastructure/repositories/CLAUDE.md` - Repository layer overview
- `/src/infrastructure/repositories/local_repo/factor/CLAUDE.md` - Factor repository patterns
- `/CLAUDE.md` - Main project architecture and conventions

---

## ⚙️ Configuration

Repository configuration follows the main project database settings:

```python
# Database configuration in DEFAULT_CONFIG
DATABASE = {
    'DB_TYPE': 'sqlite',  # or 'postgresql' for production
    'CONNECTION_STRING': '...'
}
```

---

## 🚀 Future Enhancements

- [ ] Add caching layer for frequently accessed entities
- [ ] Implement soft delete functionality
- [ ] Add audit trail for entity modifications
- [ ] Extend OpenFIGI integration to other asset types