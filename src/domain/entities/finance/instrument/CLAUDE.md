# CLAUDE.md - Instrument Domain Entity

## 🎯 Overview

The **Instrument** entity represents a financial instrument that references a `FinancialAsset`. It serves as a bridge between financial assets and their data sources, capturing when and where instrument data was recorded. This follows the Domain-Driven Design (DDD) pattern established in the codebase.

---

## 📁 Structure

```
src/domain/entities/finance/instrument/
├── __init__.py                # Module initialization
├── instrument.py              # Core Instrument domain entity
├── instrument_factor.py       # InstrumentFactor domain entity
└── CLAUDE.md                  # This documentation
```

---

## 🧱 Core Entities

### 1. **Instrument**
```python
class Instrument:
    def __init__(self, id: Optional[int], asset: FinancialAsset, 
                 source: str, date: datetime)
```

**Purpose**: Represents a financial instrument with its associated asset, data source, and timestamp.

**Key Attributes**:
- `id`: Unique identifier (auto-generated if None)
- `asset`: Reference to the underlying FinancialAsset
- `source`: Data source (e.g., 'Bloomberg', 'Reuters', 'Yahoo')
- `date`: Date when instrument data was recorded

**Key Methods**:
- `asset_id`: Property to get the underlying asset ID
- `asset_type`: Property to get the underlying asset type
- `is_valid()`: Validates that the instrument has required data
- `__eq__()`, `__hash__()`: Enables proper entity comparison and hashing

### 2. **InstrumentFactor**
```python
class InstrumentFactor(Factor):
    def __init__(self, name: str, group: str, ...)
```

**Purpose**: Represents instrument-specific factors following the unified factor pattern.

**Inheritance**: Extends the base `Factor` class with instrument-specific attributes.

**Additional Attributes**:
- `instrument_id`: Associated instrument ID
- `asset_type`: Type of underlying asset (Stock, Bond, Commodity, etc.)
- `data_provider`: Specific data provider
- `frequency`: Data frequency (real-time, daily, hourly, etc.)
- `currency`: Currency denomination
- `last_updated`: Last update timestamp

**Utility Methods**:
- `is_market_factor()`: Check if it's a market-related factor
- `is_risk_factor()`: Check if it's a risk-related factor
- `is_fundamental_factor()`: Check if it's a fundamental analysis factor
- `is_technical_factor()`: Check if it's a technical analysis factor
- `validate_frequency()`: Validate frequency values
- `validate_currency()`: Validate ISO 4217 currency codes
- `is_stale(threshold_hours)`: Check if factor data is stale

---

## 🔌 Infrastructure Integration

### **Port Interface**
- Location: `src/domain/ports/finance/instrument_port.py`
- Defines contract for repository implementations
- Methods: CRUD operations plus specialized queries

### **SQLAlchemy Model**
- Location: `src/infrastructure/models/finance/instrument.py`
- Table: `instruments`
- Relationships: Connects to `financial_assets` table

### **Repository Implementation**
- Location: `src/infrastructure/repositories/local_repo/finance/instrument_repository.py`
- Inherits from `BaseLocalRepository`
- Implements `InstrumentPort` interface

### **Mapper**
- Location: `src/infrastructure/repositories/mappers/finance/instrument_mapper.py`
- Converts between domain entities and ORM models
- Handles timestamp management and relationship mapping

---

## 🎮 Usage Examples

### **Creating an Instrument**
```python
from src.domain.entities.finance.instrument.instrument import Instrument
from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset
from datetime import datetime

# Create or get a financial asset
asset = FinancialAsset(id=1, start_date=None, end_date=None)

# Create an instrument
instrument = Instrument(
    id=None,  # Auto-generated
    asset=asset,
    source='Bloomberg',
    date=datetime.now()
)

# Validate the instrument
if instrument.is_valid():
    print(f"Valid instrument: {instrument}")
```

### **Using the Repository**
```python
from src.infrastructure.repositories.local_repo.finance.instrument_repository import InstrumentRepository
from sqlalchemy.orm import Session

# With database session
session = Session()
repo = InstrumentRepository(session)

# Add instrument
saved_instrument = repo.add(instrument)

# Query instruments
all_instruments = repo.get_all()
bloomberg_instruments = repo.get_by_source('Bloomberg')
asset_instruments = repo.get_by_asset_id(1)
```

### **Creating InstrumentFactor**
```python
from src.domain.entities.finance.instrument.instrument_factor import InstrumentFactor

# Create a market price factor
price_factor = InstrumentFactor(
    name='Current Price',
    group='Market',
    subgroup='Pricing',
    data_type='decimal',
    source='Bloomberg',
    instrument_id=1,
    asset_type='Stock',
    currency='USD',
    frequency='real-time'
)

# Validate and use
if price_factor.validate_currency() and price_factor.validate_frequency():
    print(f"Valid price factor: {price_factor}")
```

---

## 🔗 Integration Points

### **Financial Assets**
- Each Instrument MUST reference a valid FinancialAsset
- Relationships are enforced at the database level
- Cascade deletes supported (deleting asset removes instruments)

### **Factor System**
- InstrumentFactor extends the base Factor architecture
- Integrates with existing factor repositories and services
- Supports all factor groups (Market, Risk, Fundamental, Technical)

### **Data Sources**
- Supports multiple data providers (Bloomberg, Reuters, Yahoo, etc.)
- Source-specific querying and filtering
- Unique source tracking and validation

---

## ✅ Validation Rules

### **Instrument Validation**
1. **Asset Reference**: Must have a valid FinancialAsset
2. **Source**: Must be non-empty string
3. **Date**: Must be a valid datetime object
4. **Uniqueness**: Combination of asset, source, and date should be unique

### **InstrumentFactor Validation**
1. **Frequency**: Must be from accepted values (real-time, minute, hourly, daily, weekly, monthly, quarterly, annual)
2. **Currency**: Must follow ISO 4217 standard (3 uppercase letters)
3. **Factor Rules**: Inherits all base Factor validation rules

---

## 🚀 Future Enhancements

### **Planned Features**
1. **Time Series Integration**: Connect instruments to time series data
2. **Pricing Models**: Support for various pricing methodologies
3. **Risk Metrics**: Built-in risk calculation methods
4. **Market Data Feeds**: Real-time data integration
5. **Historical Analysis**: Time-based instrument performance tracking

### **Extension Points**
- Custom data source adapters
- Specialized instrument types (e.g., DerivativeInstrument, BondInstrument)
- Advanced factor calculations
- Integration with external pricing services

---

## 📊 Database Schema

```sql
-- Instruments table
CREATE TABLE instruments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    asset_id INTEGER NOT NULL REFERENCES financial_assets(id),
    source VARCHAR(255) NOT NULL,
    date DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_instruments_asset_id ON instruments(asset_id);
CREATE INDEX idx_instruments_source ON instruments(source);
CREATE INDEX idx_instruments_date ON instruments(date);
CREATE UNIQUE INDEX idx_instruments_unique ON instruments(asset_id, source, date);
```

---

## 🔧 Error Handling

### **Common Exceptions**
- `ValueError`: Invalid instrument data (empty source, null asset)
- `IntegrityError`: Duplicate instrument (same asset/source/date)
- `ForeignKeyError`: Invalid asset_id reference

### **Best Practices**
1. Always validate instruments with `is_valid()` before persistence
2. Handle database session rollbacks in repository methods
3. Use bulk operations for large datasets
4. Check for existing instruments before creation to avoid duplicates

---

## 🧪 Testing

### **Unit Tests Location**
- Domain entities: `tests/domain/entities/finance/instrument/`
- Repository: `tests/infrastructure/repositories/finance/`
- Integration: `tests/integration/finance/`

### **Test Coverage Areas**
1. **Entity Creation**: Valid and invalid instrument construction
2. **Validation**: All validation rules and edge cases
3. **Repository CRUD**: All CRUD operations and specialized queries
4. **Mapper Logic**: Domain ↔ ORM conversions
5. **Factor Integration**: InstrumentFactor specific functionality

---

This Instrument entity provides a robust foundation for managing financial instruments with proper separation of concerns, comprehensive validation, and full integration with the existing DDD architecture.