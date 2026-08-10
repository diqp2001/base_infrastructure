# company_share_option — Domain Entities

## Implied vol & implied div yield factors — design contract

### Resolution chain

```
CompanyShareOptionFactor          (Branch B — IBKR leaf, fetches OHLCV price from IBKR)
   └─ CompanyShareOptionImpliedVolFactor       (Branch A — depends on CompanyShareOptionFactor)
   └─ CompanyShareOptionImpliedDivYieldFactor  (Branch A — depends on CompanyShareOptionFactor)
```

Both `CompanyShareOptionImpliedVolFactor` and `CompanyShareOptionImpliedDivYieldFactor` declare:
```python
@property
def calculate_dependencies(self) -> list:
    return ["CompanyShareOptionFactor"]
```

The resolution service resolves `CompanyShareOptionFactor` (the option's raw price from IBKR)
and passes it as `dependencies["CompanyShareOptionFactor"]` — a float or list of floats.

### Current limitation

Newton-Raphson B-S inversion (IV) and put-call parity inversion (q) each require:
- `S` — underlying stock price (from `CompanyShareMidPriceFactor`)
- `K` — option strike (from option contract metadata)
- `r` — risk-free rate (from a rate factor)
- `T` — time to expiry (from option contract metadata)

These are **not yet threaded through the resolution chain**.  Until they are, `calculate()`
returns `None` and no value is persisted.  The full math is available on `compute_iv()`
and `compute_implied_div_yield()` helper methods — call these directly when the other
parameters are available.

### Portfolio-level aggregation

```
CompanySharePortfolioOptionImpliedVolFactor      (Branch A, calculate_dependencies = ["CompanyShareOptionImpliedVolFactor"])
CompanySharePortfolioOptionImpliedDivYieldFactor (Branch A, calculate_dependencies = ["CompanyShareOptionImpliedDivYieldFactor"])
```

The portfolio factors equal-weight average the per-option values delivered in the
`dependencies` dict as a list.

### `or`-fallback rule for `_create_or_get`

All repos here use `kwargs.get('key') or 'default'` (not the two-arg form) so that
`None` values explicitly passed by the resolution service still fall back to the default.

### Defaults

| Factor | group | subgroup | frequency | source |
|--------|-------|----------|-----------|--------|
| `CompanyShareOptionImpliedVolFactor` | `volatility` | `implied` | `1d` | `calculated` |
| `CompanyShareOptionImpliedDivYieldFactor` | `fundamental` | `daily` | `1d` | `calculated` |
| `CompanyShareOptionImpliedCorrFactor` | `volatility` | `implied` | `1d` | `calculated` |
| `CompanyShareOptionVolFactor` | `volatility` | `realized` | `1d` | `calculated` |
| `CompanyShareOptionVarFactor` | `volatility` | `realized` | `1d` | `calculated` |

---

## Additional Branch A factors (added 2026-08-05)

### CompanyShareOptionImpliedCorrFactor

**Resolution branch:** A — `calculate_dependencies = ["CompanyShareOptionFactor"]`

**Purpose:** Source of implied average correlation ρ̄ for the portfolio vol formula.

**Current status:** Returns `None` — ρ̄ requires σ_I (index/portfolio option IV) which is not
yet threaded into the resolution chain as an independent dependency.  Until it is,
`CompanySharePortfolioOptionImpliedVolFactor` falls back to the equal-weight average.

**When ρ̄ is available the inversion formula is:**
```
A  = (1/N²) * Σ σᵢ²
B  = (1/N * Σ σᵢ)² − A
ρ̄ = (σ_I² − A) / B      (clamped to [−1, 1])
```

**Dependency chain (no circular reference):**
```
CompanyShareOptionFactor (Branch B, IBKR)
  └─ CompanyShareOptionImpliedVolFactor  (Branch A, N-R IV)         ─┐
  └─ CompanyShareOptionImpliedCorrFactor (Branch A, ρ̄ — None now)   ─┤
                                                                       ↓
                                          CompanySharePortfolioOptionImpliedVolFactor
                                          = sqrt(A + ρ̄ × B)
                                          fallback: equal-weight avg when ρ̄ is None
```

### CompanyShareOptionVolFactor

**Resolution branch:** A — `calculate_dependencies = ["CompanyShareOptionFactor"]`

**Purpose:** Annualised realised volatility of the option price series.

**Algorithm (fully implemented):**
```
log_returns = [log(p[i] / p[i-1]) for i in 1..n]
annualised_vol = std(log_returns, ddof=1) * sqrt(252)
```

`calculate(dependencies)` receives `dependencies["CompanyShareOptionFactor"]` as a scalar or list
of prices. Returns `None` if fewer than 2 valid prices.

**Chain:** `CompanyShareOptionFactor` (Branch B, IBKR leaf) → `CompanyShareOptionVolFactor` (Branch A)

### CompanyShareOptionVarFactor

**Resolution branch:** A — `calculate_dependencies = ["CompanyShareOptionFactor"]`

**Purpose:** Annualised realised variance of the option price series.

**Algorithm (fully implemented):**
```
log_returns = [log(p[i] / p[i-1]) for i in 1..n]
annualised_var = var(log_returns, ddof=1) * 252
```

`calculate(dependencies)` receives the same price list as `CompanyShareOptionVolFactor`.
Returns `None` if fewer than 2 valid prices.

**Note:** `annualised_var = annualised_vol²` is **not guaranteed** numerically because both use
sample variance (`ddof=1`) and `vol = sqrt(252 * var)` — the relationship holds mathematically.

**Chain:** `CompanyShareOptionFactor` (Branch B, IBKR leaf) → `CompanyShareOptionVarFactor` (Branch A)
