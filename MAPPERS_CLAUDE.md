# MAPPERS_CLAUDE.md - Complete Mapper Inventory and Get-Or-Create Implementation

## 📋 Complete Mapper Inventory

This document provides a comprehensive list of all mappers in the base_infrastructure project and tracks implementation of get_or_create functionality for related models.

---

## 🗂️ Mapper Categories and Files

### 1. Geographic Mappers (2)
```
src/infrastructure/repositories/mappers/
├── continent_mapper.py          # Continent domain ↔ ORM mapping
└── country_mapper.py            # Country domain ↔ ORM mapping
```

**Dependencies:** Country depends on Continent

### 2. Financial Asset Core Mappers (17)
```
src/infrastructure/repositories/mappers/finance/financial_assets/
├── financial_asset_mapper.py    # Base financial asset mapping
├── currency_mapper.py           # Currency ↔ ORM (needs Country get_or_create)
├── company_share_mapper.py      # Company shares (needs Company, Exchange get_or_create)
├── options_mapper.py            # Options derivatives (needs Currency get_or_create)
├── bond_mapper.py               # Bonds (needs Currency, Company get_or_create)
├── commodity_mapper.py          # Commodities (needs Currency get_or_create)
├── crypto_mapper.py             # Cryptocurrencies (needs Currency get_or_create)
├── equity_mapper.py             # Equities (needs Currency, Exchange get_or_create)
├── etf_share_mapper.py          # ETF shares (needs Currency, Exchange get_or_create)
├── future_mapper.py             # Futures (needs Currency, Exchange get_or_create)
├── index_mapper.py              # Market indices (needs Currency get_or_create)
├── security_mapper.py           # Securities (needs Currency, Exchange get_or_create)
├── share_mapper.py              # Shares (needs Currency, Exchange get_or_create)
├── cash_mapper.py               # Cash assets (needs Currency get_or_create)
├── derivative_mapper.py         # Derivatives base (needs Currency get_or_create)
├── forward_contract_mapper.py   # Forward contracts (needs Currency get_or_create)
├── swap_mapper.py               # Swaps (needs Currency get_or_create)
└── swap_leg_mapper.py           # Swap legs (needs Currency get_or_create)
```

### 3. Finance Core Mappers (8)
```
src/infrastructure/repositories/mappers/finance/
├── company_mapper.py            # Company ↔ ORM (needs Country get_or_create)
├── exchange_mapper.py           # Exchange ↔ ORM (needs Country get_or_create)
├── instrument_mapper.py         # Instrument mapping
├── market_data_mapper.py        # Market data mapping
├── portfolio_mapper.py          # Portfolio mapping
├── position_mapper.py           # Position mapping
├── portfolio_company_share_option_mapper.py
└── back_testing/
    ├── bar_mapper.py            # Backtesting bar data
    └── symbol_mapper.py         # Symbol mapping
```

### 4. Financial Statements Mappers (4)
```
src/infrastructure/repositories/mappers/finance/financial_statements/
├── financial_statement_mapper.py
├── balance_sheet_mapper.py
├── cash_flow_statement_mapper.py
└── income_statement_mapper.py
```

### 5. Holdings & Portfolio Mappers (6)
```
src/infrastructure/repositories/mappers/finance/holding/
├── holding_mapper.py
├── portfolio_company_share_holding_mapper.py
├── security_holding_mapper.py
└── portfolio_holding_mapper.py

src/infrastructure/repositories/mappers/finance/portfolio/
├── portfolio_company_share_mapper.py
└── portfolio_derivative_mapper.py
```

### 6. Factor System Mappers (2)
```
src/infrastructure/repositories/mappers/factor/
├── factor_mapper.py             # Factor entities mapping
└── factor_value_mapper.py       # Factor values mapping
```

### 7. Time Series Mappers (3)
```
src/infrastructure/repositories/mappers/
├── time_series_mapper.py
└── time_series/
    ├── stock_time_series_mapper.py
    └── financial_asset_time_series_mapper.py
```

### 8. Classification Mappers (2)
```
src/infrastructure/repositories/mappers/
├── sector_mapper.py             # Industry sector mapping
└── industry_mapper.py           # Industry classification mapping
```

---

## 🔗 Dependency Chain Analysis

### Primary Dependency Chains:

1. **Option → Currency → Country → Continent**
   ```
   Options requires Currency
   Currency requires Country  
   Country requires Continent
   ```

2. **Company Share → Company + Exchange + Currency**
   ```
   CompanyShare requires Company
   CompanyShare requires Exchange
   Exchange requires Country
   Currency requires Country
   Country requires Continent
   ```

3. **Financial Assets → Currency → Country → Continent**
   ```
   Most financial assets require Currency
   Currency requires Country
   Country requires Continent
   ```

---

## 🚀 Get-Or-Create Implementation Status

### ✅ COMPLETED (Before this update)
- `continent_mapper.py` - No dependencies
- `factor_mapper.py` - Self-contained factor mapping
- `factor_value_mapper.py` - References existing factors

### 🔄 REQUIRES GET-OR-CREATE IMPLEMENTATION

#### High Priority (Core Dependencies)
1. **country_mapper.py**
   - ✅ Already has `_create_or_get` functionality
   - Dependencies: Continent (low priority as most reference default continent)

2. **currency_mapper.py** 
   - ❌ Needs Country get_or_create
   - Pattern: When creating currency, ensure country_id exists

3. **company_mapper.py**
   - ❌ Needs Country get_or_create  
   - Pattern: When creating company, ensure country exists

4. **exchange_mapper.py**
   - ❌ Needs Country get_or_create
   - Pattern: When creating exchange, ensure country exists

#### Medium Priority (Financial Assets)
5. **options_mapper.py**
   - ❌ Needs Currency get_or_create
   - Pattern: When creating option, ensure underlying currency exists

6. **company_share_mapper.py**
   - ❌ Needs Company + Exchange get_or_create
   - Pattern: When creating company share, ensure company and exchange exist

7. **bond_mapper.py**
   - ❌ Needs Currency + Company get_or_create (if corporate bond)

8. **commodity_mapper.py**
   - ❌ Needs Currency get_or_create

9. **crypto_mapper.py** 
   - ❌ Needs Currency get_or_create

10. **equity_mapper.py**
    - ❌ Needs Currency + Exchange get_or_create

11. **etf_share_mapper.py**
    - ❌ Needs Currency + Exchange get_or_create

12. **future_mapper.py**
    - ❌ Needs Currency + Exchange get_or_create

13. **index_mapper.py**
    - ❌ Needs Currency get_or_create

14. **security_mapper.py**
    - ❌ Needs Currency + Exchange get_or_create

15. **share_mapper.py**
    - ❌ Needs Currency + Exchange get_or_create

16. **cash_mapper.py**
    - ❌ Needs Currency get_or_create

17. **derivative_mapper.py**
    - ❌ Needs Currency get_or_create

18. **forward_contract_mapper.py**
    - ❌ Needs Currency get_or_create

19. **swap_mapper.py**
    - ❌ Needs Currency get_or_create

20. **swap_leg_mapper.py**
    - ❌ Needs Currency get_or_create

---

## 💡 Implementation Pattern

### Standard Get-Or-Create Pattern for Mappers

```python
from src.infrastructure.repositories.local_repo.geographic.country_repository import CountryRepository
from src.infrastructure.repositories.local_repo.finance.financial_assets.currency_repository import CurrencyRepository

class FinancialAssetMapper:
    """Base pattern for financial asset mappers with get_or_create dependencies."""
    
    @staticmethod
    def to_orm(domain_obj: DomainEntity, session, orm_obj: Optional[ORMModel] = None) -> ORMModel:
        """Convert domain entity to ORM model with dependency creation."""
        if orm_obj is None:
            orm_obj = ORMModel()
        
        # Basic field mapping
        orm_obj.id = domain_obj.id
        orm_obj.name = domain_obj.name
        
        # Get-or-create dependencies
        if hasattr(domain_obj, 'currency_id') and domain_obj.currency_id:
            currency_repo = CurrencyRepository(session)
            currency = currency_repo.get_by_id(domain_obj.currency_id)
            if not currency:
                # Create default currency or raise exception
                pass
        
        if hasattr(domain_obj, 'country_id') and domain_obj.country_id:
            country_repo = CountryRepository(session)
            country = country_repo.get_by_id(domain_obj.country_id) 
            if not country:
                # Use existing get_or_create pattern
                country = country_repo._create_or_get(
                    name="Unknown Country",
                    iso_code="XX"
                )
                orm_obj.country_id = country.id if country else None
        
        return orm_obj
```

### Dependency Injection Pattern
```python
class OptionsMapper:
    def __init__(self, session):
        self.session = session
        self.country_repo = CountryRepository(session)
        self.currency_repo = CurrencyRepository(session)
    
    def to_orm_with_dependencies(self, domain_obj: DomainOptions) -> ORMOptions:
        """Create options with all dependencies resolved."""
        # Ensure currency exists
        if domain_obj.currency_code:
            currency = self.currency_repo.get_or_create_by_code(domain_obj.currency_code)
            domain_obj.currency_id = currency.id
        
        return self.to_orm(domain_obj)
```

---

## 🧪 Testing Strategy

### Test Cases for Each Mapper
```python
def test_mapper_get_or_create_dependencies():
    """Test that mapper creates missing dependencies."""
    # Test missing currency creation
    options = DomainOptions(currency_code="EUR", ...)
    mapper = OptionsMapper(session)
    
    # Should create EUR currency if doesn't exist
    orm_options = mapper.to_orm_with_dependencies(options)
    
    # Verify currency was created
    currency = session.query(CurrencyModel).filter_by(iso_code="EUR").first()
    assert currency is not None
    assert orm_options.currency_id == currency.id
```

---

## 🎯 Implementation Priority Order

### Phase 1: Core Dependencies
1. Enhance `currency_mapper.py` - Country get_or_create
2. Enhance `company_mapper.py` - Country get_or_create  
3. Enhance `exchange_mapper.py` - Country get_or_create

### Phase 2: High-Usage Financial Assets
4. Enhance `options_mapper.py` - Currency get_or_create
5. Enhance `company_share_mapper.py` - Company + Exchange get_or_create
6. Enhance `bond_mapper.py` - Currency + Company get_or_create

### Phase 3: Remaining Financial Assets
7-20. All remaining financial asset mappers

### Phase 4: Validation & Testing
21. Add comprehensive test suite
22. Update documentation
23. Performance optimization

---

## 📝 Current Implementation Notes

- Most mappers follow a simple bidirectional pattern (to_domain/to_orm)
- No existing get_or_create patterns except in CountryRepository
- Session management is typically handled at repository level, not mapper level
- Need to decide: Should mappers take session parameter, or should get_or_create be at repository level?

**Recommendation:** Implement get_or_create at repository level, with mappers remaining stateless for better separation of concerns.

---

## 🔄 Next Steps

1. Update mappers to support dependency injection
2. Add get_or_create methods to repositories
3. Update existing repositories to use enhanced mappers
4. Add comprehensive testing
5. Update documentation with examples

**Total Mappers:** 42
**Mappers Needing Enhancement:** ~20
**Estimated Implementation Time:** 2-3 days

---

*Last Updated: 2026-01-20*
*Status: Analysis Complete, Implementation Required*