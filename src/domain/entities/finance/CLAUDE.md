# Finance Domain Entities - CLAUDE.md

## 📖 Overview

This directory contains domain entities related to financial concepts and data structures. These entities represent core business objects that are independent of infrastructure concerns and frameworks.

---

## 🏗️ Architecture

This module follows Domain-Driven Design (DDD) principles:

- **Pure Domain Logic**: No dependencies on frameworks or infrastructure
- **Business Rule Enforcement**: Domain entities encapsulate business rules
- **Immutable Data Structures**: Where appropriate, entities are designed to be immutable
- **Rich Domain Models**: Entities contain behavior, not just data

---

## 📁 Directory Structure

```
finance/
├── CLAUDE.md                    # This documentation file
├── price_data.py               # Price data domain entity for factor calculations
├── company.py                  # Company domain entity
├── exchange.py                 # Exchange domain entity
├── portfolio.py                # Portfolio domain entity
├── position.py                 # Position domain entity
└── financial_assets/           # Financial asset entities
    ├── company_share.py        # Company share entity
    ├── equity.py              # Equity entity
    ├── bond.py                # Bond entity
    ├── derivatives/           # Derivative financial instruments
    └── ...                    # Other financial assets
```

---

## 🆕 Recent Enhancements (2025-11-20)

### ✅ PriceData Domain Entity

**File**: `price_data.py`

**Purpose**: Encapsulates price data extracted from the database for factor calculations.

**Key Features**:
- **Data Validation**: Ensures price and date arrays have matching lengths
- **Historical Access**: `get_historical_prices()` method for lookback operations
- **Date-based Queries**: `get_price_at_date()` for specific date lookups
- **Metadata Tracking**: Includes ticker symbol and entity_id for traceability

**Usage Example**:
```python
from src.domain.entities.finance.price_data import PriceData
from datetime import date

# Create price data domain object
price_data = PriceData(
    prices=[100.0, 102.5, 101.8, 105.2],
    dates=[date(2024, 1, 1), date(2024, 1, 2), date(2024, 1, 3), date(2024, 1, 4)],
    ticker="AAPL",
    entity_id=123
)

# Access methods
latest_price = price_data.get_latest_price()  # 105.2
historical = price_data.get_historical_prices(3)  # [102.5, 101.8, 105.2]
price_on_date = price_data.get_price_at_date(date(2024, 1, 2))  # 102.5
date_range = price_data.get_date_range()  # (date(2024, 1, 1), date(2024, 1, 4))
```

**Integration Points**:
- Used by `FactorCalculationService` to standardize price data handling
- Replaces raw `List[float]` price parameters in factor calculations
- Enables database-driven factor calculations following DDD patterns

---

## 🎯 Design Principles

### Domain Purity
- No SQLAlchemy imports or database-specific code
- No framework dependencies (Flask, FastAPI, etc.)
- Pure Python business logic

### Validation and Business Rules
- Data consistency validation in domain constructors
- Business rule enforcement through domain methods
- Clear error messages for invalid operations

### Rich Behavior
- Domain entities contain behavior relevant to their concepts
- Methods that encapsulate domain-specific logic
- Avoid anemic domain models (entities with only getters/setters)

---

## 📊 Usage Patterns

### 1. Price Data Extraction Pattern
```python
# In application services
price_data = repository.extract_price_data(entity_id)
momentum_value = factor.calculate_momentum(price_data.prices)
```

### 2. Domain Validation Pattern
```python
# Domain entities validate their own consistency
try:
    price_data = PriceData(prices=[], dates=[date.today()])
except ValueError as e:
    # Handle validation error: "Price data cannot be empty"
```

### 3. Business Logic Encapsulation
```python
# Business logic lives in domain entities
if price_data.get_latest_price() > threshold:
    # Execute business logic
```

---

## 🔗 Related Components

- **Infrastructure Layer**: `src/infrastructure/repositories/` - Database persistence
- **Application Layer**: `src/application/services/` - Use case orchestration
- **Factor Calculation**: Uses PriceData for momentum, volatility, and technical calculations

---

## 📝 Contributing Guidelines

When adding new finance domain entities:

1. **Keep Pure**: No external dependencies beyond standard library
2. **Validate Early**: Add validation in constructors
3. **Rich Behavior**: Include domain-relevant methods
4. **Document Well**: Add comprehensive docstrings
5. **Test Thoroughly**: Create unit tests for domain logic

Example entity template:
```python
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class MyFinanceDomainEntity:
    \"\"\"
    Domain entity for [purpose].
    
    This class encapsulates [business concept] and provides
    [key functionality] following DDD principles.
    \"\"\"
    required_field: str
    optional_field: Optional[int] = None
    
    def __post_init__(self):
        \"\"\"Validate entity consistency.\"\"\"
        if not self.required_field:
            raise ValueError("Required field cannot be empty")
    
    def domain_specific_method(self) -> bool:
        \"\"\"Implement business logic specific to this domain.\"\"\"
        # Business logic here
        return True
```

---

## TargetPortfolio and portfolio construction (added 2026-11-20, refactor phase P3)

```
Factor values -> TradingStrategy.evaluate -> StrategySignals
              -> PortfolioConstructionService.construct(signals, method) -> TargetPortfolio
              -> (P4) rebalancing against what the account holds -> trade instructions -> execution
```

- `portfolio/target_portfolio.py`: `TargetPortfolio` (as_of, strategy name, construction name, positions sorted by
  symbol, one per asset) and `TargetPortfolioPosition` (symbol, signed `target_weight` = fraction of portfolio
  value, optional `asset_type`, `financial_asset_id`, `target_quantity`). Immutable, in memory, never persisted.
  It is what the strategy WANTS; `Position` / `PortfolioHolding` are what the account HOLDS. Never mix them.
- `portfolio/construction/steps.py`: pure, deterministic steps (ties broken by symbol).
  - selection (scores -> sides): `AllAssets`, `QuantileLongShort`, `TopBottomN`, `Threshold`, `Buckets` (scores that
    are bucket labels, e.g. quintile 1-5);
  - weighting (sides -> weights): `EqualWeighting`, `ScoreWeighting`, `InverseVolatilityWeighting`;
  - adjustments (in order): `VolatilityScaling`, `DivideByCount`, `Normalise`, `NormaliseSides`, `GrossExposureCap`
    (down only), `NetExposureLimit`, `AssetWeightLimit`, `ExposureLimit` (e.g. delta; a missing loading is an error).
- `portfolio/construction/construction_method.py`: `PortfolioConstructionMethod(name, selection, weighting,
  adjustments)` plus ready-made methods. `volatility_targeted_signals` reproduces STM's `signals_to_weights` and
  `quantile_long_short_inverse_volatility` reproduces CSM's `long_short_weights`: golden tests in
  `tests/strategy/test_portfolio_construction.py` pin both. `bucket_long_short` is long Q5 / short Q1.
- Application: `src/application/services/portfolio_construction/portfolio_construction_service.py`. It only gathers
  the inputs (scores from the signals, volatility and loadings from the caller or `signals.context`).
- `portfolio/construction/delta_hedge.py` (2026-11-23): the delta-hedge overlay on ACTUAL holdings. It provides
  `aggregate_book_greeks` (option exposures to book delta / gamma, |gamma|-weighted IV and expiry) and
  `delta_hedge_decision` (inside the band no trade; outside, hedge back to delta 0). `hedge_target_portfolio`
  gives the hedge instrument as a quantity target. The band width is the caller's model (SPX: WW, Zakamouline,
  WW-NTBN).
- Construction never submits orders, reads or updates positions, creates transactions or uses broker code. A test
  checks, in a fresh interpreter, that no execution module is loaded.
