# Factor Ports — Architecture Reference

## Purpose

Factor ports are **abstract repository interfaces** (ABCs) that decouple domain logic from
infrastructure implementations.  Every factor type has a dedicated port; every concrete
repository in `src/infrastructure/repositories/` implements the matching port.

---

## Directory structure

The `finance/` subdirectory mirrors `src/domain/entities/factor/finance/` exactly.
Only 5 root-level ports live outside `finance/` because their domain entities are not
under `entities/factor/finance/`:

```
src/domain/ports/factor/
├── factor_port.py                         ← FactorPort (base)
├── factor_value_port.py                   ← FactorValuePort
├── factor_dependency_port.py             ← FactorDependencyPort
├── continent_factor_port.py              ← ContinentFactorPort
├── country_factor_port.py                ← CountryFactorPort
│
└── finance/
    ├── financial_assets/
    │   ├── financial_asset_factor_port.py
    │   ├── security_factor_port.py
    │   ├── equity_factor_port.py
    │   ├── index/
    │   │   ├── index_factor_port.py
    │   │   └── index_price_return_factor_port.py
    │   ├── currency/
    │   │   ├── currency_factor_port.py
    │   │   ├── currency_rate_factor_port.py    ← IBKR leaf
    │   │   └── currency_value_factor_port.py
    │   ├── bond_factor/
    │   │   ├── bond_factor_port.py
    │   │   ├── bond_price_factor_port.py
    │   │   ├── bond_yield_factor_port.py
    │   │   ├── bond_duration_factor_port.py
    │   │   ├── bond_convexity_factor_port.py
    │   │   ├── bond_spread_factor_port.py
    │   │   └── bond_interest_rate_factor_port.py
    │   ├── share_factor/
    │   │   ├── share_factor_port.py
    │   │   ├── share_technical_factor_port.py
    │   │   ├── share_momentum_factor_port.py
    │   │   ├── share_volatility_factor_port.py
    │   │   ├── share_target_factor_port.py
    │   │   └── company_share/
    │   │       ├── company_share_factor_port.py
    │   │       ├── company_share_mid_price_factor_port.py    ← IBKR leaf
    │   │       ├── company_share_value_factor_port.py
    │   │       ├── company_share_price_return_factor_port.py
    │   │       ├── company_share_avg_turnover_6m_factor_port.py
    │   │       ├── company_share_monthly_price_range_factor_port.py
    │   │       └── company_share_vpt_52w_20d_lag_factor_port.py
    │   └── derivatives/
    │       ├── derivative_factor_port.py
    │       ├── future/
    │       │   ├── future_factor_port.py
    │       │   ├── future_price_return_factor_port.py
    │       │   ├── future_annualized_price_return_factor_port.py
    │       │   ├── future_annualized_roll_yield_factor_port.py
    │       │   ├── future_discounted_value_factor_port.py
    │       │   ├── future_forward_price_factor_port.py
    │       │   ├── index_future_factor_port.py
    │       │   ├── index_future_price_return_factor_port.py
    │       │   └── bond_future/
    │       │       └── bond_future_factor_port.py
    │       ├── option/
    │       │   ├── option_factor_port.py
    │       │   ├── index_future_option_factor_port.py
    │       │   ├── index_future_option_price_factor_port.py
    │       │   ├── index_future_option_delta_factor_port.py
    │       │   ├── index_future_option_price_return_factor_port.py
    │       │   ├── company_share_option/           ← single-share option greeks + pricing models
    │       │   └── company_share_portfolio_option/ ← portfolio option greeks + pricing models
    │       └── structured_notes/
    │           ├── structured_note_factor_port.py
    │           └── call_spread/
    ├── holding/
    │   ├── holding_factor_port.py
    │   ├── portfolio_holding_value_factor_port.py
    │   ├── currency_portfolio_holding_value_factor_port.py
    │   ├── company_share_portfolio/
    │   │   ├── company_share_portfolio_holding_factor_port.py
    │   │   ├── company_share_portfolio_holding_value_factor_port.py
    │   │   ├── company_share_portfolio_holding_quantity_factor_port.py
    │   │   └── company_share_portfolio_holding_weight_factor_port.py
    │   ├── company_share_portfolio_portfolio/
    │   │   └── company_share_portfolio_portfolio_holding_value_factor_port.py
    │   └── currency_portfolio_portfolio/
    │       └── currency_portfolio_portfolio_holding_value_factor_port.py
    ├── portfolio/
    │   ├── portfolio_factor_port.py
    │   ├── portfolio_value_factor_port.py
    │   ├── currency_portfolio_value_factor_port.py
    │   ├── company_share_portfolio_factor/
    │   │   ├── company_share_portfolio_factor_port.py
    │   │   ├── company_share_portfolio_value_factor_port.py
    │   │   ├── company_share_portfolio_return_factor_port.py
    │   │   ├── company_share_portfolio_correlation_factor_port.py
    │   │   └── company_share_portfolio_variance_factor_port.py
    │   └── derivatives/option/company_share_option_portfolio/
    ├── order/
    │   ├── company_share_order_price_factor_port.py
    │   └── company_share_order_quantity_factor_port.py
    ├── position/
    │   └── company_share_position_value_factor_port.py
    └── transaction/
        └── company_share_transaction_value_factor_port.py
```

---

## Standard abstract interface

Every factor port follows this exact pattern:

```python
from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.XXX import XxxFactor

class XxxFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[XxxFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[XxxFactor]: ...

    @abstractmethod
    def get_all(self) -> List[XxxFactor]: ...

    @abstractmethod
    def add(self, entity: XxxFactor) -> Optional[XxxFactor]: ...

    @abstractmethod
    def update(self, entity: XxxFactor) -> Optional[XxxFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[XxxFactor]: ...
```

**Optional additional methods** (include when semantically meaningful for that factor type):

| Method | When to add |
|--------|-------------|
| `get_by_group(group: str)` | Base/abstract factor types (financial_asset, derivative, share, etc.) |
| `get_by_subgroup(subgroup: str)` | Factors with multiple subgroup variants (return, momentum, volatility) |

---

## `_create_or_get` contract

This is the **central method** called by `FactorValueResolutionService` Branch A when wiring
dependency factors.  It must:

1. Look up the factor by `primary_key` (usually `name`) in the DB
2. If found → return existing domain entity
3. If not found → create with the kwargs supplied (`group`, `subgroup`, `frequency`, `data_type`)
4. Never infer missing fields from context — if a field is absent, use the domain entity's
   own default (obtained via `entity_cls().field_name`)

**Do not** default `frequency` to `'1d'` in the repo unless the domain entity's default is
`'1d'`.  Wrong frequency defaults corrupt factor value integrity.

---

## IBKR leaf factor ports

The following ports represent **terminal (leaf) factors** fetched directly from IBKR.  Their
repos must implement both the local port AND the IBKR port interface:

| Port | Factor | IBKR data |
|------|--------|-----------|
| `CompanyShareMidPriceFactorPort` | `CompanyShareMidPriceFactor` | Bid/ask midpoint |
| `CompanyShareOptionMidPriceFactorPort` | `CompanyShareOptionMidPriceFactor` | Option bid/ask midpoint |
| `CurrencyRateFactorPort` | `CurrencyRateFactor` | FX spot rate |
| `IndexFuturePriceReturnFactorPort` | `IndexFuturePriceReturnFactor` | Price return via IBKR |

---

## Adding a new factor port

1. Create the file under `finance/<matching-entity-path>/<factor_name>_port.py`
2. Follow the standard interface pattern above
3. Register the concrete repo in `src/infrastructure/repositories/repository_factory.py`
4. Import directly from the structured path — do **not** add flat shims
