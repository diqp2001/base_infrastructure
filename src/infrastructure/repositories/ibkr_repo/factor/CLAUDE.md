# IBKR Factor Repository Architecture

## 📋 Overview

This module implements the IBKR factor repository architecture that mirrors the `local_repo/factor` structure while adding IBKR-specific data acquisition and business rules.

## 🏗️ Architecture

The IBKR factor repositories follow the **dual repository pattern** with clear separation of concerns:

### Core Principles
1. **IBKR Contract → Instrument → Factor Values → Asset Factor Values**
2. **IBKR repositories handle data acquisition and normalization**
3. **Local repositories handle persistence**
4. **Clean delegation pattern throughout**

## 📁 Structure

```
ibkr_repo/factor/
├── __init__.py
├── CLAUDE.md                                    # This documentation
├── base_ibkr_factor_repository.py              # Base class for IBKR factor repos
├── ibkr_factor_repository.py                   # Factor metadata repository
├── ibkr_factor_value_repository.py             # Factor value repository
├── ibkr_instrument_factor_repository.py        # Instrument-specific factor operations
└── finance/
    ├── __init__.py
    └── financial_assets/
        ├── __init__.py
        └── ibkr_company_share_factor_repository.py  # Company share factors
```

## 🔄 Pipeline Implementation

### Main Pipeline Functions (as requested by user):

#### 1. `get_or_create_factor_value_with_ticks`
```python
def get_or_create_factor_value_with_ticks(
    self, 
    symbol_or_name: str, 
    factor_id: int, 
    time: str,
    tick_data: Optional[Dict[int, Any]] = None
) -> Optional[FactorValue]:
```

**Flow:**
1. Get/create company share entity
2. Check existing factor values
3. Fetch IBKR contract
4. Get contract details
5. **Create instrument from contract + tick data**
6. Retrieve mapped factor values

#### 2. `create_factor_value_from_tick_data`
```python
def create_factor_value_from_tick_data(
    self,
    symbol: str,
    tick_type: IBKRTickType,
    tick_value: Any,
    time: str
) -> Optional[FactorValue]:
```

**Flow:**
1. Convert single tick to tick data dictionary
2. Resolve factor_id from tick mapping
3. Delegate to `get_or_create_factor_value_with_ticks`

#### 3. `get_or_create_factor_value` (Legacy)
```python
def get_or_create_factor_value(
    self, 
    symbol_or_name: str, 
    factor_id: int, 
    time: str
) -> Optional[FactorValue]:
```

**Flow:**
1. Get/create company share entity
2. Check existing factor values
3. Fetch IBKR contract and details
4. Convert directly to factor value
5. Delegate persistence to local repository

## 🔌 Repository Integration

### IBKRCompanyShareRepository Integration
```python
class IBKRCompanyShareRepository:
    def __init__(self, ibkr_client, local_repo, factor_repo=None):
        self.factor_repo = factor_repo
    
    # Factor methods now delegated to factor_repo
    def get_or_create_factor_value_with_ticks(self, ...):
        return self.factor_repo.get_or_create_factor_value_with_ticks(...)
```

### IBKRInstrumentRepository Integration
```python
class IBKRInstrumentRepository:
    def __init__(self, ibkr_client, local_repo, asset_repo, factor_repo=None):
        self.factor_repo = factor_repo
    
    # Factor operations delegated to factor_repo
    def create_factor_values_from_ticks(self, ...):
        return self.factor_repo.create_factor_values_from_ticks(...)
```

## 🎯 Data Flow

### Complete IBKR Factor Pipeline:
```
┌─────────────────┐
│ IBKR Contract   │
└─────────────────┘
         │
         ▼
┌─────────────────┐    ┌─────────────────┐
│ IBKRInstrument  │◄───│ Tick Data       │
└─────────────────┘    └─────────────────┘
         │
         ▼
┌─────────────────┐
│ Instrument      │
│ Factor Values   │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Asset Factor    │
│ Values          │
└─────────────────┘
         │
         ▼
┌─────────────────┐
│ Local Repository│
│ (Database)      │
└─────────────────┘
```

## 🔧 Usage Examples

### Basic Factor Value Creation
```python
# Setup repositories
local_factor_repo = FactorValueRepository(session)
ibkr_factor_repo = IBKRFactorValueRepository(
    ibkr_client=ibkr_client,
    local_factor_value_repo=local_factor_repo,
    ibkr_instrument_repo=instrument_repo
)

# Create factor value with tick data
tick_data = {
    1: 150.20,    # BID_PRICE
    2: 150.25,    # ASK_PRICE  
    4: 150.23,    # LAST_PRICE
}

factor_value = ibkr_factor_repo.get_or_create_factor_value_with_ticks(
    symbol_or_name="AAPL",
    factor_id=4,  # Last price factor
    time="2025-01-14",
    tick_data=tick_data
)
```

### Company Share Factor Integration
```python
# Setup company share repository with factor integration
company_share_repo = IBKRCompanyShareRepository(
    ibkr_client=ibkr_client,
    local_repo=local_company_repo,
    factor_repo=ibkr_company_factor_repo
)

# Use through company share repository
factor_value = company_share_repo.get_or_create_factor_value_with_ticks(
    symbol_or_name="AAPL",
    factor_id=4,
    time="2025-01-14",
    tick_data={4: 150.23}
)
```

## ✅ Benefits Achieved

1. **Clean Separation**: Factor operations separated from financial asset operations
2. **Modular Design**: Each repository has single responsibility
3. **Consistent Interface**: All IBKR repositories follow same delegation pattern  
4. **Extensible**: Easy to add new factor types and asset types
5. **Testable**: Factor operations can be tested independently
6. **IBKR Integration**: Full IBKR tick type mapping with official TWS API support

## 🚀 Next Steps

1. **Add more financial asset factor repositories** (bonds, ETFs, currencies)
2. **Implement advanced factor calculations** (technical indicators, ratios)
3. **Add real-time factor streaming** from IBKR market data
4. **Create factor analysis services** using the factor repositories
5. **Add performance optimization** for high-frequency factor updates

This architecture now provides exactly what was requested: **complete separation of factor operations into dedicated IBKR factor repositories while maintaining the pipeline functionality specified by the user.**