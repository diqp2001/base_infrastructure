# Portfolio Value Factor Repositories

## Repos in this directory

| File | Factor type | DB `factor_type` |
|------|-------------|-----------------|
| `currency_portfolio_value_factor_repository.py` | `CurrencyPortfolioValueFactor` | `currency_portfolio_value_factor` |
| `portfolio_value_factor_repository.py` | `PortfolioValueFactor` | `portfolio_value_factor` |
| `company_share_portfolio/company_share_portfolio_value_factor_repository.py` | `CompanySharePortfolioValueFactor` | `company_share_portfolio_value_factor` |

Holding-level counterparts live in `../holding/`:
- `currency_portfolio_holding_value_factor_repository.py`
- `currency_portfolio_portfolio_holding_value_factor_repository.py`
- `company_share_portfolio_holding_value_factor_repository.py`
- `company_share_portfolio_portfolio_holding_value_factor_repository.py`
- `portfolio_holding_value_factor_repository.py`

---

## Critical: `or`-fallback for all factor fields in `_create_or_get`

The resolution service passes **all** kwargs from the factor library config dict, including
fields that are absent in the config (they arrive as explicit `None`). A bare
`kwargs.get(key, default)` returns `None` when the key exists with value `None` — the
default is **never used** in that case.

**Always use the `or` form**, not the two-argument `dict.get`:**

```python
# WRONG — returns None when resolution service passes frequency=None
frequency = kwargs.get('frequency', '1d')

# CORRECT — falls back to '1d' even when the key is present with value None
frequency = kwargs.get('frequency') or '1d'
```

This applies to every factor field that has a NOT NULL column in the DB:
`frequency`, `data_type`, `source`, `subgroup`, `definition`.

The `group` field is also validated by `Factor.__init__`, so apply the same pattern there.

### Required `or` pattern for every portfolio / holding value factor `_create_or_get`:

```python
domain_factor = self.get_factor_entity()(
    name=primary_key,
    group=kwargs.get('group') or '<canonical_group>',
    subgroup=kwargs.get('subgroup') or '<canonical_subgroup>',
    frequency=kwargs.get('frequency') or '1d',
    data_type=kwargs.get('data_type') or 'numeric',
    source=kwargs.get('source') or 'calculated',
    definition=kwargs.get('definition') or f'...',
)
```

Canonical defaults per factor type (driven by the domain entity's `__init__` defaults):

| Factor | group | subgroup | frequency | data_type | source |
|--------|-------|----------|-----------|-----------|--------|
| `CurrencyPortfolioValueFactor` | `value` | `value` | `1d` | `numeric` | `calculated` |
| `PortfolioValueFactor` | `value` | `daily` | `1d` | `numeric` | `calculated` |
| `CompanySharePortfolioValueFactor` | `value` | `value` | `1d` | `decimal` | `calculated` |
| `CurrencyPortfolioHoldingValueFactor` | `holding` | `value` | `1d` | `decimal` | `calculated` |
| `CurrencyPortfolioPortfolioHoldingValueFactor` | `holding` | `value` | `1d` | `decimal` | `calculated` |
| `CompanySharePortfolioHoldingValueFactor` | `holding` | `value` | `1d` | `numeric` | `calculated` |
| `CompanySharePortfolioPortfolioHoldingValueFactor` | `holding` | `value` | `1d` | `numeric` | `calculated` |
| `PortfolioHoldingValueFactor` | `holding` | `value` | `1d` | `numeric` | `calculated` |

---

## Entity `__init__` must accept every kwarg the repo passes

When `_create_or_get` constructs `self.get_factor_entity()(name=..., frequency=..., ...)`,
the domain entity's `__init__` signature **must accept every keyword argument** that the repo
passes — otherwise Python raises `TypeError: __init__() got an unexpected keyword argument`.

The resolution service (Branch A) calls:
```python
dep_defaults = dep_repo.get_factor_entity()()   # entity with all defaults
dep_repo._create_or_get(
    dep_repo.get_factor_entity(),
    primary_key=dep_defaults.name,
    group=getattr(dep_defaults, 'group', None),
    subgroup=getattr(dep_defaults, 'subgroup', None),
    data_type=getattr(dep_defaults, 'data_type', None),
    frequency=getattr(dep_defaults, 'frequency', None),
)
```

Every factor entity that a repo manages **must have `frequency` in its `__init__`** and pass it
to `super().__init__()`, so the value flows into `Factor.frequency` and survives mapper
round-trips via `to_orm` / `to_domain`.

Entities fixed for missing `frequency` (2026-07-31):
- `CurrencyPortfolioHoldingValueFactor` — `frequency` kwarg added to `__init__`
- `CurrencyFactor` — `frequency` kwarg added to `__init__` (fixes the entire `CurrencyValueFactor` chain)
- `CurrencyValueFactor` — removed post-`super()` workaround; `frequency` now flows through the MRO
- `CompanySharePortfolioHoldingFactor` — `frequency` kwarg added to `__init__` and passed to `super()` (intermediate parent; blocked the whole subclass chain)
- `CompanySharePortfolioHoldingValueFactor` — `frequency` kwarg added to `__init__` (default `"1d"`)
- `PortfolioHoldingValueFactor` — `frequency` kwarg added to `__init__` (default `"1d"`)

---

## Mapper `to_orm` must map every NOT NULL column

The mapper's `to_orm` is the only place where a domain entity attribute becomes a DB column
value.  Any attribute left out of `to_orm` inserts `NULL`, which fails `NOT NULL` constraints.

Mappers fixed for missing `frequency` in `to_orm` and `to_domain` (2026-07-31):
- `CompanySharePortfolioValueFactorMapper` — `frequency` added to both `to_orm` and `to_domain`
- `CurrencyPortfolioHoldingValueFactorMapper` — `frequency` added to both `to_orm` and `to_domain`
- `PortfolioHoldingValueFactorMapper` — `frequency` added to both `to_orm` and `to_domain`
- `CompanySharePortfolioHoldingValueFactorMapper` — `frequency` added to both `to_orm` and `to_domain`

Checklist when writing a new mapper `to_orm`:
- `name`, `group`, `subgroup`, `frequency`, `data_type`, `source`, `definition` — all mapped?
- `factor_type` set to the correct `polymorphic_identity` string?

---

## Entity `group` default must match the repo/mapper canonical value

The resolution service reads the entity's default `group` via `dep_defaults.group` and passes it
as `group=...` to `_create_or_get`.  If the entity's default `group` doesn't match the repo's
expected group (used in `get_by_all` lookup), every run creates a new duplicate factor record.

Entity defaults corrected (2026-07-31):
- `CompanySharePortfolioValueFactor` — `group` changed from `'portfolio'` to `'value'`
  (the DB lookup key and the canonical value used by downstream resolution)

---

## Leaf factor entity rules (applies to every "price / rate" leaf factor)

A **leaf factor** is a factor with no `@property calculate_dependencies` — its value
comes from IBKR or another external source (Branch B in the resolution service).

Examples: `CompanyShareMidPriceFactor`, `CurrencyRateFactor`.

### Rule 1 — `frequency` default must not be `None`

The resolution service calls `get_factor_entity()()` (no args) to read the entity's
defaults, then passes those defaults to `_create_or_get`.  If `frequency=None` is the
default, `None` reaches the DB `factors.frequency` column (NOT NULL) → `IntegrityError`.

```python
# WRONG
frequency: Optional[str] = None

# CORRECT — use the factor's standard cadence
frequency: Optional[str] = "1d"
```

Leaf factors fixed for `frequency=None` default (2026-07-31):
- `CompanyShareMidPriceFactor` — changed from `None` to `"1d"`

### Rule 2 — `source` default must be in `Factor.SOURCES`

`Factor.__init__` validates `source` against the whitelist.  A default of `"multiple"`
(not in the whitelist) causes `ValueError` the moment the entity is instantiated.

```python
# WRONG
source: Optional[str] = "multiple"

# CORRECT
source: Optional[str] = "ibkr"   # primary source for this factor
```

Leaf factors fixed for invalid `source` default (2026-07-31):
- `CurrencyRateFactor` — changed from `"multiple"` to `"ibkr"`

### Rule 3 — `frequency` must be passed to `super().__init__()`, not set after

Setting `self.frequency = frequency` after `super().__init__()` is a fragile workaround.
Pass it directly to `super()` so `Factor.frequency` is set through the normal MRO.

```python
# WRONG
super().__init__(name=name, group=group, ...)   # frequency omitted
self.frequency = frequency                       # post-super workaround

# CORRECT
super().__init__(name=name, group=group, frequency=frequency, ...)
```

Leaf factors cleaned up (2026-07-31):
- `CurrencyRateFactor` — removed post-`super()` workaround

### Rule 4 — repo `_create_or_get` must use `or`-fallback for all NOT NULL fields

Use `kwargs.get(key) or default`, not `kwargs.get(key, default)`.
The two-arg form returns `None` when the key exists with value `None`;
the `or` form always falls back to default when the value is falsy.

```python
# WRONG — returns None if resolution service passes frequency=None
frequency=kwargs.get('frequency', '1d')

# CORRECT
frequency=kwargs.get('frequency') or '1d'
```

Repos fixed for missing `or`-fallback (2026-07-31):
- `CurrencyRateFactorRepository` — `source` and `frequency`

---

## calculate() dependency key rule (applies to every factor with calculate_dependencies)

The resolution service keys each resolved dependency value by the **dep class name**
(a string like `'CurrencyRateFactor'`), not by the factor_library alias
(`'currency_mid_price_factor'`).  `calculate()` must use the same key.

```python
# WRONG — key is the library alias, never found in the dict → default 0 or 1
raw = dependencies.get('currency_mid_price_factor', Decimal('1'))

# CORRECT — key is the class name
raw = dependencies.get('CurrencyRateFactor') or Decimal('1')
```

The `or Decimal('1')` form handles `None` in the dict (dep resolved but had no value)
as well as the key being absent.  Use `or Decimal('0')` for value factors where
"no price data" should propagate as zero rather than identity.

Factors fixed for wrong dependency key (2026-07-31):
- `CurrencyValueFactor.calculate()` — `'currency_mid_price_factor'` → `'CurrencyRateFactor'`

Factors verified correct (class name already used):
- `CompanyShareValueFactor.calculate()` — `'CompanyShareMidPriceFactor'` ✓

---

## Regression test coverage

`src/tests/unit/test_factor_value_chain.py` covers all four rules above:
- `TestLeafFactorDefaults` — entity defaults are valid (frequency, source)
- `TestCalculateDependencyKeys` — calculate() uses class name as key; wrong key gives 0; None rate falls back to 1
- `TestHoldingValueChainNonZero` — holding value = price × quantity (non-zero when both non-zero)

Run with: `python -m unittest src.tests.unit.test_factor_value_chain`

---

## Session rollback cascade

A single `IntegrityError` (e.g. `NULL` in a NOT NULL column) marks the SQLAlchemy session
as rolled back. **Every subsequent operation on the same session fails** with:

> `This Session's transaction has been rolled back due to a previous exception during flush.`

That is why a single bad `_create_or_get` call produces dozens of downstream errors in the
log (`Error in IBKR _create_or_get for symbol AAPL`, etc.). The root cause is always the
**first** error message — the rest are session-cascade noise.

Fix the root cause (missing or NULL field), not the cascades.

---

## Subgroup and group validation

`Factor.__init__` validates both `group` and `subgroup` against whitelists. Invalid values
raise `ValueError` immediately — before any DB write. See
`src/domain/entities/factor/CLAUDE.md` for the full lists.

Portfolio value factors use:
- `group = "value"` (added 2026-07-29 — was missing, caused `Invalid group 'value'` errors)
- `subgroup = "value"` or `"daily"` (both valid)
