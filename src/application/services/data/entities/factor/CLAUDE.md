# FactorValueResolutionService — Architecture & Dependency Materialization

## Responsibility

`FactorValueResolutionService` is the single entry point for computing and persisting
factor values across the system. It walks the dependency graph of every factor,
materialises each node (factor record + factor value) bottom-up, and stores the
results so that higher-level factors can use them.

---

## Core Entry Point

```
resolve_factor_value(factor_entity, entity, time_date, repository_type)
```

Returns a persisted `FactorValue` for `(factor_entity, entity, time_date)`.  
If the value already exists in the DB it is returned immediately.  
Otherwise dependencies are resolved first, then `calculate()` is called and the
result is persisted.

---

## Dependency Resolution — Two Branches

### Branch A — `calculate_dependencies` property present (Source 2)

Used when a factor's value depends on **another factor's stored FactorValue** rather
than raw related-entity data (e.g. `CurrencyPortfolioHoldingValueFactor` needs the
already-computed `CurrencyValueFactor` value for the underlying currency asset).

`calculate_dependencies` returns a list of factor class name strings:

```python
@property
def calculate_dependencies(self) -> List[str]:
    return ['CurrencyValueFactor']
```

**Resolution algorithm (per dep_name):**

1. **Get repo** — `factory.get_local_repository(dep_name)`
2. **Ensure factor record exists** — `dep_repo._create_or_get(...)` with the
   holding factor's own `subgroup` / `data_type` / `frequency`.  Creates the
   factor row in DB if it is missing.
3. **Ensure factor value exists** — call `resolve_factor_value(dep_factor, related_entity, ...)`
   This is the same recursive entry point, so if `dep_factor` itself has
   `calculate_dependencies` the whole process recurses until a leaf factor with
   no declared dependencies is reached.
4. **Store result** — `dependency_values[dep_name] = resolved_value`

### Branch B — no `calculate_dependencies` (Source 1)

Used when a factor's value is derived from **related entity data** (positions,
holdings, etc.) rather than another factor's stored value.

Uses `_find_matching_factors` to find factor records sharing the same metadata
as the holding factor, then resolves their values for each related entity.

---

## Full Recursive Materialization Example

```
CurrencyPortfolioHoldingValueFactor.calculate_dependencies = ['CurrencyValueFactor']

resolve_factor_value(CurrencyPortfolioHoldingValueFactor, holding, date)
  │
  ├─ _resolve_dynamic_dependencies  [Branch A]
  │    │
  │    ├─ dep_name = 'CurrencyValueFactor'
  │    ├─ dep_repo._create_or_get(...)          # ensure CurrencyValueFactor row exists
  │    └─ resolve_factor_value(CurrencyValueFactor, currency_asset, date)  [recurse]
  │         │
  │         ├─ _resolve_dynamic_dependencies  [Branch A]
  │         │    │
  │         │    ├─ dep_name = 'CurrencyRateFactor'
  │         │    ├─ dep_repo._create_or_get(...)   # ensure CurrencyRateFactor row exists
  │         │    └─ resolve_factor_value(CurrencyRateFactor, currency_asset, date) [recurse]
  │         │         └─ no calculate_dependencies → Branch B / raw data lookup
  │         │              → calculate() + persist FactorValue
  │         │
  │         └─ CurrencyValueFactor.calculate({'CurrencyRateFactor': <rate>})
  │              → persist FactorValue
  │
  └─ CurrencyPortfolioHoldingValueFactor.calculate({'CurrencyValueFactor': <value>})
       → persist FactorValue
```

---

## Key Design Rules

| Rule | Reason |
|------|--------|
| Always call `_create_or_get` on the dep repo before resolving the value | Guarantees the factor row exists before any value is stored against it |
| Always use `resolve_factor_value` as the recursive call (not `_check_existing_value` alone) | It handles value lookup, recursive dependency materialization, calculate, and persist in one call |
| `calculate_dependencies` uses class name strings, not instances | Allows the factory to dispatch to the correct repo without coupling domain to infra |
| Dependency dict is keyed by dep class name | `calculate()` receives `{'CurrencyValueFactor': 1.23}` and looks up by the same key |

---

## Adding a New Factor with Dynamic Dependencies

1. Add `@property calculate_dependencies` returning the list of dep class names.
2. Update `calculate(self, dependencies: dict)` to look up values by those names.
3. Register the dep factor's repo in `RepositoryFactory` under its class name key.
4. No changes needed in `FactorValueResolutionService` — the recursive algorithm
   handles arbitrary depth automatically.
