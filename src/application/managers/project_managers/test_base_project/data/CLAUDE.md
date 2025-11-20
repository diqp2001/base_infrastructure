# CLAUDE.md - Test Base Project Data Manager

## 📊 Factor-Based Data Management Layer

This directory contains the core data management component that orchestrates entity creation, factor calculation, and data persistence for the test base project following standardized patterns.

---

## 📁 Directory Structure

```
data/
├── factor_manager.py           # Main factor and entity orchestration
├── feature_engineer.py         # Spatiotemporal feature engineering
└── CLAUDE.md                   # This documentation
```

---

## 🎯 Standardized Entity Creation Integration

### Key Implementation: FactorEnginedDataManager

The `FactorEnginedDataManager` class has been updated to use the **standardized entity creation pattern** consistent with repository layer improvements.

### Enhanced _ensure_entities_exist() Method

#### Before Standardization
```python
def _ensure_entities_exist(self, tickers: List[str]) -> Dict[str, Any]:
    """Manual entity creation with duplicate checking."""
    for ticker in tickers:
        share = self.company_share_repository.get_by_ticker(ticker)
        if not share:
            # Manual entity creation
            new_share = CompanyShareEntity(...)
            new_share.set_company_name(f"{ticker} Inc.")
            new_share.update_sector_industry("Technology", None)
            created_share = self.company_share_repository.add(new_share)
```

#### After Standardization  
```python
def _ensure_entities_exist(self, tickers: List[str]) -> Dict[str, Any]:
    """Uses standardized _create_or_get_company_share pattern."""
    for ticker in tickers:
        # Use standardized repository method
        share = self.company_share_repository._create_or_get_company_share(
            ticker=ticker,
            exchange_id=1,
            company_id=None,
            start_date=datetime(2020, 1, 1),
            company_name=f"{ticker} Inc.",
            sector="Technology",
            industry=None
        )
```

### Benefits of Integration

1. **Consistency**: Uses same pattern as `BaseFactorRepository._create_or_get_factor()`
2. **Reliability**: Automatic duplicate prevention and error handling
3. **Maintainability**: Single standardized approach across all entity types
4. **Traceability**: Better logging and status reporting

---

## 🏗️ Architecture Integration

### Repository Layer Integration
```python
class FactorEnginedDataManager:
    def __init__(self, database_service: DatabaseService):
        # Repository instances using standardized patterns
        self.company_share_repository = CompanyShareRepositoryLocal(database_service.session)
        self.share_factor_repository = ShareFactorRepository(self.config['DATABASE']['DB_TYPE'])
        self.base_factor_repository = BaseFactorRepository(self.config['DATABASE']['DB_TYPE'])
```

### Standardized Pattern Usage
```python
# Entity creation through standardized repository methods
share = self.company_share_repository._create_or_get_company_share(...)

# Factor creation through existing standardized pattern
factor = self.share_factor_repository._create_or_get_factor(...)

# Base factor creation through original standardized pattern  
base_factor = self.base_factor_repository._create_or_get_factor(...)
```

---

## 📈 Data Flow with Standardized Patterns

### 1. Entity Verification Phase
```
Ticker List Input
    ↓
_ensure_entities_exist()
    ↓
CompanyShareRepository._create_or_get_company_share()
    ↓
Verified Entity Set (existing + newly created)
```

### 2. Factor Creation Phase  
```
Factor Definitions
    ↓
_create_*_factor_definitions()
    ↓
BaseFactorRepository._create_or_get_factor()
    ↓
Factor Definitions Created/Retrieved
```

### 3. Value Calculation Phase
```
Market Data + Entities + Factors
    ↓
_calculate_*_factor_values()
    ↓
Factor Calculation Services
    ↓
Stored Factor Values
```

---

## 🔧 Configuration Integration

### Default Configuration Usage
```python
# Database configuration
self.config['DATABASE']['DB_TYPE']  # 'sqlite' or 'postgresql'

# Entity defaults
self.config['DATA']['DEFAULT_UNIVERSE']  # Default ticker list

# Factor configurations
self.config['FACTORS']['PRICE_FACTORS']     # Price factor definitions
self.config['FACTORS']['MOMENTUM_FACTORS']  # Momentum factor definitions  
self.config['FACTORS']['TECHNICAL_FACTORS'] # Technical factor definitions
```

### Standardized Entity Creation Parameters
```python
# Company Share defaults
ENTITY_DEFAULTS = {
    'exchange_id': 1,
    'start_date': datetime(2020, 1, 1),
    'default_sector': 'Technology',
    'company_name_suffix': 'Inc.'
}
```

---

## 📊 Enhanced Status Reporting

### Before Standardization
```
Basic counts: created vs existing
Limited error details
No standardized messaging
```

### After Standardization
```python
return {
    'verified': existing_count + created_count,
    'existing': existing_count,
    'created': created_count
}

# With improved logging:
print(f"    ✅ Created entity for {ticker}")
print(f"    ❌ Error ensuring entity exists for {ticker}: {str(e)}")
```

---

## 🧪 Testing Integration

### Test Pattern for Standardized Entity Creation
```python
def test_ensure_entities_exist_standardized():
    """Test standardized entity creation in factor manager."""
    
    # Setup
    tickers = ['AAPL', 'GOOGL', 'MSFT']
    manager = FactorEnginedDataManager(database_service)
    
    # Execute
    result = manager._ensure_entities_exist(tickers)
    
    # Verify
    assert result['verified'] == len(tickers)
    assert result['existing'] + result['created'] == len(tickers)
    
    # Verify entities exist in database
    for ticker in tickers:
        shares = manager.company_share_repository.get_by_ticker(ticker) 
        assert len(shares) > 0
```

---

## 🔄 Migration Benefits

### Consistency Improvements
- ✅ All entity creation uses standardized `_create_or_get_*` pattern
- ✅ Consistent error handling across entity types
- ✅ Unified logging and status reporting
- ✅ Predictable behavior for duplicate prevention

### Code Quality Improvements  
- ✅ Reduced code duplication
- ✅ Improved maintainability
- ✅ Better separation of concerns
- ✅ Enhanced testability

### Operational Improvements
- ✅ More reliable entity creation
- ✅ Better error diagnostics  
- ✅ Improved performance through reduced database queries
- ✅ Consistent database transaction handling

---

## 📚 Related Documentation

- `/src/infrastructure/repositories/local_repo/finance/financial_assets/CLAUDE.md` - Financial asset repository patterns
- `/src/infrastructure/repositories/local_repo/geographic/CLAUDE.md` - Geographic repository patterns
- `/src/infrastructure/repositories/local_repo/factor/CLAUDE.md` - Factor repository patterns (original pattern source)
- `/src/application/managers/CLAUDE.md` - Manager layer architecture
- `/CLAUDE.md` - Main project architecture and conventions

---

## 🚀 Future Enhancements

- [ ] Extend standardized pattern to all entity types in the system
- [ ] Add batch entity creation optimizations
- [ ] Implement entity relationship validation
- [ ] Add entity lifecycle management (soft delete, archiving)
- [ ] Integrate with audit logging system
- [ ] Add entity versioning support