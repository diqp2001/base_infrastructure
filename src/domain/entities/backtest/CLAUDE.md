# Backtest Domain Entities

## Overview

This package contains the domain entities that model the backtest infrastructure:
a **Model** (algorithm/strategy), a **Backtest** run, a **Universe** of assets, a
**BacktestFactor** (the factor-layer counterpart), and the **BacktestFactorBacktest**
join table that links factors to backtests.

---

## Entity Summary

| Domain entity | Table | Key columns |
|---|---|---|
| `Model` | `models` | `id`, `name` |
| `Backtest` | `backtests` | `id`, `name`, `model_id` (FK → models), `creation_date` |
| `Universe` | `universes` | `id`, `name`, `creation_date`, `description` |
| `BacktestFactor` | `factors` (STI, discriminator `backtest_factor`) | standard factor columns |
| `BacktestFactorBacktest` | `backtest_factor_backtests` | `id`, `backtest_id` (FK → backtests), `backtest_factor_id` (FK → factors) |

---

## File locations per layer

### 1. Domain entities
```
src/domain/entities/backtest/
├── model.py                        # Model(Entity)
├── backtest.py                     # Backtest(Entity)
├── universe.py                     # Universe(Entity)
└── backtest_factor_backtest.py     # BacktestFactorBacktest(Entity)

src/domain/entities/factor/backtest/
└── backtest_factor.py              # BacktestFactor(Factor)
```

### 2. ORM models
```
src/infrastructure/models/backtest/
├── model.py                        # ModelModel  →  table: models
├── backtest.py                     # BacktestModel  →  table: backtests
├── universe.py                     # UniverseModel  →  table: universes
└── backtest_factor_backtest.py     # BacktestFactorBacktestModel  →  table: backtest_factor_backtests

src/infrastructure/models/factor/factor.py
└── BacktestFactorModel(FactorModel)  polymorphic_identity = 'backtest_factor'
```

### 3. Ports (interfaces)
```
src/domain/ports/backtest/
├── model_port.py
├── backtest_port.py
├── universe_port.py
└── backtest_factor_backtest_port.py

src/domain/ports/factor/backtest/
└── backtest_factor_port.py
```

### 4. Mappers
```
src/infrastructure/repositories/mappers/backtest/
├── model_mapper.py
├── backtest_mapper.py
├── universe_mapper.py
└── backtest_factor_backtest_mapper.py

src/infrastructure/repositories/mappers/factor/backtest/
└── backtest_factor_mapper.py       discriminator = 'BacktestFactor'
```

`FactorMapper.to_domain()` dispatches `factor_type == 'backtest_factor'` →
`BacktestFactor`.

### 5. Local repositories
```
src/infrastructure/repositories/local_repo/backtest/
├── model_repository.py
├── backtest_repository.py
├── universe_repository.py
└── backtest_factor_backtest_repository.py

src/infrastructure/repositories/local_repo/factor/backtest/
└── backtest_factor_repository.py
```

### 6. IBKR repository
```
src/infrastructure/repositories/ibkr_repo/factor/backtest/
└── ibkr_backtest_factor_repository.py   # delegates everything to local repo
```

### 7. Factory keys (RepositoryFactory)
| Key | Repo class |
|---|---|
| `'Model'` | `ModelRepository` |
| `'Backtest'` | `BacktestRepository` |
| `'Universe'` | `UniverseRepository` |
| `'BacktestFactorBacktest'` | `BacktestFactorBacktestRepository` |
| `'BacktestFactor'` | `BacktestFactorRepository` (local) / `IBKRBacktestFactorRepository` (ibkr) |

---

## Relationships

```
Model  1──*  Backtest
Backtest  *──*  BacktestFactor   (via BacktestFactorBacktest join table)
```

`BacktestFactor` lives in the `factors` table alongside all other factors
(single-table inheritance). It carries the standard factor fields
(`name`, `group`, `subgroup`, `frequency`, `data_type`, `source`, `definition`)
and is linked to specific `Backtest` rows through the `backtest_factor_backtests`
join table.

---

## BacktestFactor — factor layer notes

- **No `calculate_dependencies`**: not a computed factor; it is metadata.
- **Discriminator**: `backtest_factor` (stored in `factors.factor_type`).
- **Default group**: `fundamental`; default subgroup: `backtest`.
- **No IBKR data**: the IBKR repo delegates all operations to local repo.
- Not added to `ENTITY_FACTOR_MAPPING` (no domain entity it represents).

---

## Usage example

```python
# Get repos from factory
model_repo    = factory._local_repositories['Model']
backtest_repo = factory._local_repositories['Backtest']
factor_repo   = factory._local_repositories['BacktestFactor']
join_repo     = factory._local_repositories['BacktestFactorBacktest']

# Create model + backtest
model    = model_repo._create_or_get(name='momentum_v1')
backtest = backtest_repo._create_or_get(name='bt_2026_q1', model_id=model.id)

# Create a factor and attach it to the backtest
factor   = factor_repo._create_or_get(entity_cls=None, primary_key='mom_20d',
                                       group='momentum', subgroup='backtest')
join_repo._create_or_get(backtest_id=backtest.id, backtest_factor_id=factor.id)
```
