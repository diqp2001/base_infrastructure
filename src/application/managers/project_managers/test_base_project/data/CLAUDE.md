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

---

## 💡 Recent Enhancement: Database-Driven Price Data Extraction (2025-11-20)

### Problem Addressed
Previously, factor calculations required external preparation of price data as raw `List[float]` parameters, violating DDD principles and creating tight coupling between data preparation and calculation logic.

### Solution Implemented
Updated `FactorEnginedDataManager` to use the new **database-driven price data extraction pattern** from `FactorCalculationService`:

#### Before Enhancement
```python
def _calculate_momentum_factor_values(self, tickers: List[str], ...):
    for ticker in tickers:
        company = self.company_share_repository.get_by_ticker(ticker)[0]
        
        # Manual price data extraction
        factorentityClose = self.share_factor_repository.get_by_name('Close')
        df = self.share_factor_repository.get_factor_values_df(
            factor_id=int(factorentityClose.id), 
            entity_id=company.id
        )
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)
        df["value"] = df["value"].astype(float)
        
        # Manual data preparation
        prices = df["value"].tolist()
        dates = df.index.tolist()
        
        # Factor calculation with raw data
        momentum_results = self.factor_calculation_service.calculate_and_store_momentum(
            factor=factor,
            entity_id=company.id,
            entity_type='share',
            prices=prices,    # Raw price list
            dates=dates,      # Raw date list
            overwrite=overwrite
        )
```

#### After Enhancement
```python
def _calculate_momentum_factor_values(self, tickers: List[str], ...):
    for ticker in tickers:
        company = self.company_share_repository.get_by_ticker(ticker)[0]
        
        # Simplified: service handles price extraction internally
        momentum_results = self.factor_calculation_service.calculate_and_store_momentum(
            factor=factor,
            entity_id=company.id,
            entity_type='share',
            ticker=ticker,      # Optional ticker for logging
            overwrite=overwrite
        )
        
        # Updated result handling
        values_stored = momentum_results.get('stored_values', 0) if momentum_results else 0
```

### Key Benefits

1. **Domain-Driven Design Compliance**: Price data is now encapsulated in `PriceData` domain entity
2. **Reduced Code Duplication**: No more manual price data extraction in multiple places
3. **Improved Maintainability**: Price extraction logic centralized in service layer
4. **Better Error Handling**: Standardized error responses from service layer
5. **Enhanced Testability**: Service-level testing of price extraction logic

### Integration with Standardized Patterns

This enhancement builds upon the existing standardized entity creation patterns:

```python
# Entity creation (existing standardized pattern)
share = self.company_share_repository._create_or_get_company_share(...)

# Factor creation (existing standardized pattern)  
factor = self.share_factor_repository._create_or_get_factor(...)

# Factor calculation (NEW: database-driven pattern)
results = self.factor_calculation_service.calculate_and_store_momentum(
    factor=factor, entity_id=share.id, ticker=ticker
)
```

---

## 🚀 Future Enhancements

- [ ] Extend standardized pattern to all entity types in the system
- [ ] Add batch entity creation optimizations
- [ ] Implement entity relationship validation
- [ ] Add entity lifecycle management (soft delete, archiving)
- [ ] Integrate with audit logging system
- [ ] Add entity versioning support
- [ ] Extend database-driven extraction to volatility and technical factor calculations

---

## 💫 Latest Enhancement: EntityExistenceService Integration (2025-11-20)

### Refactoring Goal
Transform the `_ensure_entities_exist` method from a manager-specific implementation into a reusable service that follows the same standardized patterns as other repository operations.

### New Architecture: EntityExistenceService

#### Service Creation
Created `/src/application/services/data/entities/entity_existence_service.py` with:

```python
class EntityExistenceService:
    """Centralized service for ensuring entity dependencies exist."""
    
    def __init__(self, database_service: DatabaseService):
        self.company_share_repository = CompanyShareRepository(database_service.session)
        self.country_repository = CountryRepository(database_service.session)  
        self.sector_repository = SectorRepository(database_service.session)
        self.industry_repository = IndustryRepository(database_service.session)
    
    def ensure_entities_exist(self, tickers: List[str]) -> Dict[str, Any]:
        """
        Ensure all required entities exist for tickers.
        Verifies CompanyShare, Company, and related entities.
        """
```

#### Enhanced Entity Verification
The service now verifies multiple entity types:

1. **CompanyShare entities** - Uses existing `_create_or_get_company_share` pattern
2. **Company entities** - Placeholder for future CompanyRepository implementation
3. **Country entities** - Uses `CountryRepository._create_or_get_country`
4. **Sector entities** - Uses `SectorRepository._create_or_get_sector`  
5. **Industry entities** - Placeholder for future development

### Manager Integration

#### Updated FactorEnginedDataManager
```python
class FactorEnginedDataManager:
    def __init__(self, database_service: DatabaseService):
        # NEW: EntityExistenceService injection
        self.entity_existence_service = EntityExistenceService(database_service)
        
    def populate_momentum_factors(self, tickers=None, overwrite=False):
        # NEW: Use service for entity verification
        entities_summary = self.entity_existence_service.ensure_entities_exist(tickers)
        
        # Existing factor creation logic continues...
        momentum_factors_ = self._create_momentum_factor_definitions()
        
    def _ensure_entities_exist(self, tickers: List[str]) -> Dict[str, Any]:
        """
        DEPRECATED: Use EntityExistenceService.ensure_entities_exist() instead.
        Kept for backward compatibility.
        """
        return self.entity_existence_service.ensure_entities_exist(tickers)
```

### Company Entity Enhancement

#### Current State
- `Company` domain entity exists but no dedicated repository
- Companies referenced through `CompanyShare.company_id`
- EntityExistenceService includes placeholder for company verification

#### Future Implementation Path
```python
# 1. Create CompanyRepository following standardized pattern
class CompanyRepository:
    def _create_or_get_company(self, name: str, legal_name: str, 
                              country_id: int, industry_id: int) -> Company:
        """Follow same pattern as BaseFactorRepository._create_or_get_factor"""
        
# 2. Update EntityExistenceService to use CompanyRepository  
def _ensure_company_exists_for_share(self, share: CompanyShareEntity):
    """Use CompanyRepository for actual company verification"""
    company = self.company_repository._create_or_get_company(...)
```

### Enhanced Reporting

#### Before (Simple Counts)
```python
return {
    'verified': existing_count + created_count,
    'existing': existing_count, 
    'created': created_count
}
```

#### After (Comprehensive Entity Breakdown)
```python
return {
    'company_shares': {'verified': 3, 'existing': 2, 'created': 1},
    'companies': {'verified': 3, 'existing': 3, 'created': 0}, 
    'countries': {'verified': 1, 'existing': 1, 'created': 0},
    'sectors': {'verified': 1, 'existing': 0, 'created': 1},
    'industries': {'verified': 0, 'existing': 0, 'created': 0},
    'errors': []  # Detailed error collection
}
```

### Benefits of Service Refactoring

1. **Reusability**: Other managers can use EntityExistenceService
2. **Consistency**: Same standardized patterns across all entity types  
3. **Company Verification**: Added company entity verification (with future enhancement path)
4. **Separation of Concerns**: Entity management separated from factor management
5. **Enhanced Reporting**: Comprehensive statistics by entity type
6. **Backward Compatibility**: Existing code continues to work unchanged

### Integration Points

The service is now integrated into all factor population methods:
- `populate_price_factors()` ✅
- `populate_momentum_factors()` ✅  
- `populate_technical_indicators()` ✅
- `populate_volatility_factors()` (future)
- `populate_target_factors()` (future)