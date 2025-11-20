# CLAUDE.md - Geographic Repositories

## 🌍 Geographic Entity Repository Layer

This directory contains repository implementations for geographic entities (Countries, Sectors, Industries), providing standardized data persistence following Domain-Driven Design (DDD) principles.

---

## 📁 Directory Structure

```
geographic/
├── geographic_repository.py      # Base repository for geographic entities
├── country_repository.py         # Country entity persistence
├── sector_repository.py          # Sector entity persistence
├── industry_repository.py        # Industry entity persistence
└── continent_repository.py       # Continent entity persistence
```

---

## 🎯 Standardized Entity Creation Pattern Implementation

### Pattern Applied

All geographic repositories now implement the **standardized entity creation pattern** consistent with `BaseFactorRepository._create_or_get_factor()`:

### CountryRepository
```python
def _create_or_get_country(self, name: str, iso_code: Optional[str] = None,
                          continent: Optional[str] = None, currency: Optional[str] = None):
    """Create country if not exists, return existing otherwise."""
    # Check by name (primary unique identifier)
    existing_country = self.get_by_name(name)
    if existing_country:
        return existing_country
    
    # Also check by ISO code if provided (secondary unique identifier)  
    if iso_code:
        existing_by_iso = self.get_by_iso_code(iso_code)
        if existing_by_iso:
            return existing_by_iso
    
    # Create new entity with sequential ID
    next_id = self._get_next_available_country_id()
    # ... creation logic
```

### SectorRepository
```python
def _create_or_get_sector(self, name: str, classification_system: Optional[str] = None,
                         description: Optional[str] = None):
    """Create sector if not exists, return existing otherwise."""
    # Uses 'name' as unique identifier
    # Supports GICS, ICB, and other classification systems
```

### IndustryRepository
```python
def _create_or_get_industry(self, name: str, sector_name: Optional[str] = None,
                           classification_system: Optional[str] = None,
                           description: Optional[str] = None):
    """Create industry if not exists, return existing otherwise."""
    # Links industries to sectors via sector_name
    # Maintains classification system consistency
```

---

## 🔑 Key Features

### Unique Identifier Handling
- **Country**: Primary by `name`, secondary by `iso_code`
- **Sector**: By `name` within `classification_system`
- **Industry**: By `name` within `sector_name` and `classification_system`

### Sequential ID Generation
```python
def _get_next_available_{entity}_id(self) -> int:
    """Get next sequential ID for entity creation."""
    try:
        max_id_result = self.session.query(EntityModel.id).order_by(EntityModel.id.desc()).first()
        return max_id_result[0] + 1 if max_id_result else 1
    except Exception as e:
        print(f"Warning: Could not determine next available {entity} ID: {str(e)}")
        return 1
```

### Error Handling
- Database rollback on creation failures
- Graceful logging of errors
- None return for failed operations

---

## 🏛️ Entity Relationships

```
Country
├── iso_code (unique)
├── continent
└── currency

Sector  
├── name (unique per classification_system)
├── classification_system (GICS, ICB, etc.)
└── description

Industry
├── name (unique per sector)
├── sector_name (FK relationship)
├── classification_system
└── description
```

---

## 📊 Classification Systems Supported

### Sector Classification
- **GICS** (Global Industry Classification Standard)
- **ICB** (Industry Classification Benchmark)  
- **NAICS** (North American Industry Classification System)
- **Custom** classifications

### Usage Examples
```python
# Create sector with GICS classification
tech_sector = sector_repo._create_or_get_sector(
    name="Information Technology",
    classification_system="GICS",
    description="Technology companies and services"
)

# Create industry within sector
software_industry = industry_repo._create_or_get_industry(
    name="Software",
    sector_name="Information Technology", 
    classification_system="GICS",
    description="Software development and services"
)

# Create country with full details
usa_country = country_repo._create_or_get_country(
    name="United States",
    iso_code="US",
    continent="North America",
    currency="USD"
)
```

---

## 🔄 Migration Impact

### Before Standardization
- Manual entity existence checking
- Inconsistent ID generation
- Varied error handling patterns
- No standard duplicate prevention

### After Standardization
- ✅ Consistent `_create_or_get_*` pattern
- ✅ Automatic duplicate prevention  
- ✅ Sequential ID collision avoidance
- ✅ Standardized error handling
- ✅ Multiple unique identifier support (name + iso_code for countries)

---

## 🧪 Testing Patterns

```python
def test_geographic_entity_creation():
    """Test standardized geographic entity creation."""
    
    # Test country creation with dual uniqueness
    country1 = country_repo._create_or_get_country("United States", iso_code="US")
    country2 = country_repo._create_or_get_country("USA", iso_code="US")  # Same ISO
    assert country1.id == country2.id  # Should return same entity
    
    # Test sector classification consistency
    sector = sector_repo._create_or_get_sector("Technology", "GICS")
    assert sector.classification_system == "GICS"
    
    # Test industry-sector relationship
    industry = industry_repo._create_or_get_industry(
        "Software", sector_name="Technology", classification_system="GICS"
    )
    assert industry.sector_name == "Technology"
```

---

## 📈 Usage in Application Layer

Geographic repositories integrate with financial asset repositories for complete entity linking:

```python
# In CompanyShareRepository
def _create_or_get_company_share(self, ticker: str, ..., sector: str = None):
    """Creates company share and links to geographic entities."""
    
    # Create/get sector if provided
    if sector:
        sector_entity = self.sector_repository._create_or_get_sector(
            name=sector,
            classification_system="GICS"
        )
        # Link company to sector
```

---

## 🌐 International Support

### Country Data
- ISO 3166-1 alpha-2 country codes
- Continent groupings
- Currency associations
- Multi-language country names (future)

### Sector/Industry Localization
- Support for regional classification systems
- Multi-market sector mappings
- Industry translations (future enhancement)

---

## 📚 Related Documentation

- `/src/infrastructure/repositories/local_repo/finance/financial_assets/CLAUDE.md` - Financial asset repositories
- `/src/infrastructure/repositories/local_repo/factor/CLAUDE.md` - Factor repository patterns
- `/src/infrastructure/repositories/CLAUDE.md` - Repository layer overview
- `/CLAUDE.md` - Main project architecture

---

## 🚀 Future Enhancements

- [ ] Add hierarchical sector/industry relationships
- [ ] Implement geographic region groupings
- [ ] Add support for historical sector changes
- [ ] Implement multi-language entity names
- [ ] Add economic indicator integration
- [ ] Support for regulatory jurisdiction mapping