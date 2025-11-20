# Finance Repositories - CLAUDE.md

## 📁 Repository Layer Architecture

This directory contains repository implementations for finance-related entities, following Domain-Driven Design (DDD) principles and standardized patterns.

---

## 🏗️ Repository Structure

```
finance/
├── company_repository.py          # NEW: Company entity CRUD operations
├── sector_repository.py          # Sector entity CRUD operations  
├── industry_repository.py        # Industry entity CRUD operations
└── financial_assets/
    ├── company_share_repository.py    # CompanyShare entity CRUD operations
    └── company_share_factor_repository.py  # Factor-specific operations
```

---

## 🔧 Recent Enhancements (2025-11-20)

### ✅ **CompanyRepository Implementation**

**New File**: `/src/infrastructure/repositories/local_repo/finance/company_repository.py`

#### Key Features:
- **Standardized Pattern**: Follows `_create_or_get_*` pattern consistent with BaseFactorRepository
- **Sequential ID Generation**: `_get_next_available_company_id()` method
- **Duplicate Prevention**: Checks existence by company name before creation
- **Domain/Infrastructure Mapping**: Proper entity conversions using BaseRepository pattern

#### Core Methods:
```python
# Standardized entity creation (follows BaseFactorRepository pattern)
company = repository._create_or_get_company(
    name="AAPL Inc.",
    legal_name="Apple Inc.",
    country_id=1,
    industry_id=1
)

# Standard CRUD operations
companies = repository.get_all()
company = repository.get_by_id(company_id)
company = repository.get_by_name("AAPL Inc.")
```

### 🔗 **Enhanced Company-Share Linkage**

The EntityExistenceService now properly creates companies first, then links them to shares:

1. **Create Company** → Get company_id from database
2. **Create CompanyShare** → Set company_id from step 1  
3. **Link Entities** → Proper foreign key relationships

This fixes the "0 tickers processed" issue in factor processing pipelines.

---

## 🎯 Repository Patterns Used

### 1. **Standardized Entity Creation** (`_create_or_get_*`)
All repositories implement the same pattern:
```python
def _create_or_get_entity(self, unique_field, **kwargs):
    # 1. Check if entity exists by unique identifier
    if self.exists_by_unique_field(unique_field):
        return self.get_by_unique_field(unique_field)
    
    # 2. Generate sequential ID
    next_id = self._get_next_available_*_id()
    
    # 3. Create new entity
    entity = create_new_entity(id=next_id, **kwargs)
    
    # 4. Add to database with error handling
    return self.add(entity)
```

### 2. **Domain/Infrastructure Separation**
- **Domain Entities**: Pure business logic, no SQLAlchemy dependencies
- **Infrastructure Models**: SQLAlchemy ORM models with database mappings
- **Mappers**: Convert between domain and infrastructure layers

### 3. **Sequential ID Management** 
- Database-driven ID generation prevents conflicts
- Chronological ordering maintained
- Graceful fallback to ID=1 if no records exist

---

## 📊 Database Relationships

```
Company (companies table)
├── id (PK)
├── name (unique)
├── legal_name  
├── country_id (FK → countries.id)
├── industry_id (FK → industries.id)
├── start_date
└── end_date

CompanyShare (company_shares table)  
├── id (PK)
├── ticker (unique)
├── exchange_id (FK → exchanges.id)
├── company_id (FK → companies.id)  ← Fixed linkage!
├── start_date
└── end_date
```

---

## 🚀 Usage Examples

### Creating Linked Entities via EntityExistenceService
```python
from application.services.data.entities.entity_existence_service import EntityExistenceService

# Initialize service
service = EntityExistenceService(database_service)

# Create companies and shares with proper linkage
results = service.ensure_entities_exist(['AAPL', 'TSLA', 'MSFT'])

# Results show proper company_id assignment
print(results['companies']['created'])    # Companies created
print(results['company_shares']['created'])  # Shares created with company_id
```

### Direct Repository Usage
```python
from infrastructure.repositories.local_repo.finance.company_repository import CompanyRepository

# Initialize repository
repo = CompanyRepository(session)

# Create or get company
company = repo._create_or_get_company(
    name="Apple Inc.",
    country_id=1,  # USA
    industry_id=1   # Technology
)

# Use company_id for share creation
share_repo.create_company_share(ticker="AAPL", company_id=company.id)
```

---

## 🧪 Testing Integration

The enhanced repositories integrate with:
- **Factor Processing Pipelines**: No more "0 tickers processed" errors  
- **Model Training**: Proper data linkage prevents "No objects to concatenate" errors
- **Entity Verification**: Comprehensive entity dependency checking
- **Backtest Systems**: Full entity lifecycle management

---

## 🔮 Future Enhancements

### Planned Improvements:
- [ ] Exchange repository with `_create_or_get_exchange`
- [ ] Enhanced company data enrichment via external APIs
- [ ] Bulk operations optimization for large datasets
- [ ] Company merger/acquisition history tracking
- [ ] Industry classification hierarchy support

### Integration Targets:
- [ ] Real-time market data pipeline integration
- [ ] Corporate actions processing (splits, dividends)
- [ ] ESG (Environmental, Social, Governance) data linkage
- [ ] Earnings and financial statements integration

---

*This documentation follows the standardized CLAUDE.md format and reflects the architecture decisions implemented on 2025-11-20 to resolve entity linkage issues.*