# Factor Library — Schema & Parameter Reference

## Purpose

The factor library defines every factor the system knows about: its class, how to create/look up the factor record in the DB, and how to find its dependencies. Each library is a `Dict[str, Dict]` keyed by a short library alias (e.g. `"return_daily"`).

---

## Required Schema for Every Library Entry

Every top-level entry (and every entry under `"dependencies"`) **must** include:

| Key | Type | Notes |
|-----|------|-------|
| `class` | domain entity class | e.g. `CompanyShareFactor` |
| `name` | `str` | name stored in DB `factors.name` column |
| `group` | `str` | must be a key in `Factor.GROUPS` |
| `subgroup` | `str` | must be a key in `Factor.SUBGROUPS` |
| `frequency` | `str` | must be a key in `Factor.FREQUENCIES` |
| `data_type` | `str` | must be a key in `Factor.DATA_TYPES` |
| `dependencies` | `dict` or `[]` | nested dep entries (same schema) |
| `parameters` | `dict` | lag, period, entity-key overrides |

The `description` field is informational and not validated. Top-level entries may also include `source`, `definition`, `factor_type`, `entity_class`, `entity_symbol` for richer DB creation.

### Why all fields are required

`Factor.__init__` validates `group`, `subgroup`, `frequency`, `data_type` at construction time. Any missing or invalid value raises `ValueError` immediately. The DB also has all `factors.*` columns as `nullable=False`, so `None` values cause `IntegrityError` on INSERT.

Repos default missing `frequency` to `"1d"` via `dependency_config.get("frequency", "1d")`. This silently stores the wrong frequency for minute-level factors. Always provide `"frequency"` explicitly.

---

## Valid Parameter Values

### `Factor.FREQUENCIES`
| Key | Description |
|-----|-------------|
| `"1s"` | 1 second |
| `"5s"` | 5 seconds |
| `"1m"` | 1 minute |
| `"5m"` | 5 minutes |
| `"15m"` | 15 minutes |
| `"1h"` | 1 hour |
| `"1d"` | 1 day |
| `"1w"` | 1 week |
| `"1mth"` | 1 month |
| `"1y"` | 1 year |

### `Factor.GROUPS`
| Key | Use |
|-----|-----|
| `"price"` | Market price data (OHLCV) |
| `"return"` | Price return / P&L |
| `"holding"` | Single holding metrics |
| `"portfolio"` | Aggregated portfolio metrics |
| `"value"` | Market value / portfolio value |
| `"momentum"` | Momentum / trend signals |
| `"technical"` | Technical indicator signals |
| `"volatility"` | Risk / volatility metrics (use `"implied"` subgroup for implied vol) |
| `"volume"` | Volume and turnover metrics |
| `"order"` | Order-level factors |
| `"transaction"` | Transaction-level factors |
| `"position"` | Position-level factors |
| `"fundamental"` | Fundamental financial data |
| `"economic"` | Macro-economic indicators |
| `"risk"` | Risk measures (VaR, CVaR…) |
| `"valuation"` | Valuation ratios and metrics |
| `"greek"` | Options Greeks |
| `"liquidity"` | Liquidity metrics |
| `"price_model"` | Option pricing model outputs (BSM, Heston, …) |

> **`"implied_volatility"` is NOT a valid group** — use `group="volatility"` with `subgroup="implied"`.

### `Factor.SUBGROUPS` (selected)
| Key | Typical use |
|-----|-------------|
| `"mid_price_true"` | True mid price |
| `"mid_price"` | Mid price |
| `"ohlc"` | OHLC price |
| `"daily"` | Daily bar |
| `"minutes"` | Minute bar |
| `"weekly"` | Weekly bar |
| `"monthly"` | Monthly bar |
| `"asset"` | Asset-level value (company_share_value, currency_value) |
| `"value"` | Holding / portfolio value |
| `"quantity"` | Quantity |
| `"turnover"` | Volume turnover |
| `"trend"` | Volume trend |
| `"range"` | Price range |
| `"price"` | Price (in order context) |
| `"implied"` | Implied volatility |
| `"realized"` | Realized volatility |
| `"black_scholes"` | BSM pricing model |
| `"binomial_tree"` | CRR binomial tree |
| `"stochastic_volatility"` | Heston / SV models |
| `"stochastic_rates"` | Hull-White |
| `"sabr"` | SABR model |
| `"jump_diffusion"` | Bates jump-diffusion |
| `"local_volatility"` | Dupire local vol |
| `"delta"` … `"rho"` | Greeks |

### `Factor.DATA_TYPES`
| Key | Python type |
|-----|-------------|
| `"decimal"` | `Decimal` — high-precision financial values |
| `"numeric"` | `float` — general floating-point |
| `"integer"` | `int` |
| `"boolean"` | `bool` |
| `"string"` | `str` |
| `"percentage"` | `float` in [0,1] or [0,100] |

---

## Libraries in `FACTOR_LIBRARY`

| Library constant | File | Domain |
|-----------------|------|--------|
| `COMPANY_SHARE_LIBRARY` | `finance/financial_assets/company_share_library.py` | Company share price, return, volume factors |
| `COMPANY_SHARE_OPTION_LIBRARY` | `finance/financial_assets/derivatives/option/company_share_option_library.py` | Option price, return, model factors |
| `FUTURE_INDEX_LIBRARY` | `finance/financial_assets/derivatives/future/future_index_library.py` | Index future price & return |
| `FUTURE_INDEX_OPTION_LIBRARY` | `finance/financial_assets/derivatives/option/future_index_option_library.py` | Index future option price & return |
| `INDEX_LIBRARY` | `finance/financial_assets/index_library.py` | Index price & return |
| `PORTFOLIO_LIBRARY` | `finance/portfolio/portfolio_library.py` | Portfolio / holding / position value chain |
| `TRADING_FACTORS_LIBRARY` | `finance/trading_factors_library.py` | Order → Transaction → Position value lifecycle |
| `CURRENCY_LIBRARY` | `finance/financial_assets/currency_library.py` | Currency value and rate |

---

## Dependency entry frequency rules

Dep `frequency` must match the **parent factor's data cadence**:
- Parent is minute-level (`"1m"`) → deps are `"1m"`
- Parent is daily (`"1d"`) → deps are `"1d"`
- Parent is weekly (`"1w"`) → deps are `"1w"`
- Parent is monthly (`"1mth"`) → deps are `"1mth"`

Omitting `frequency` from a dep entry is wrong even if the repo defaults to `"1d"`: it stores a stale/incorrect frequency in the DB for the dep factor record.

---

## Portfolio value chain (for reference)

```
PortfolioValueFactor (group=value, subgroup=daily, freq=1d)
  └─ CompanySharePortfolioPortfolioHoldingValueFactor (group=holding, subgroup=value, freq=1d)
       └─ CompanySharePortfolioValueFactor (group=value, subgroup=daily, freq=1d)
            └─ CompanySharePortfolioHoldingValueFactor (group=holding, subgroup=value, freq=1d)
```
