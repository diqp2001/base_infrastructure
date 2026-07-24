# src/ — Master Context Navigation

This file maps **task type → relevant CLAUDE.md files** so you start in the right place
without reading the entire codebase.  Each section lists the minimum set of files to
read for that task, in reading order.

---

## 1. Creating a new Factor

A factor is a computed or fetched numeric value attached to a domain entity (e.g. price,
value, rate, return).  Every factor requires **8 artefacts** across 5 layers.

| Step | Artefact | Location |
|------|----------|----------|
| 1 | Domain entity (`*Factor` class with optional `calculate` + `@property calculate_dependencies`) | `src/domain/entities/factor/` |
| 2 | Factor library entry (config dict wiring the factor) | `src/application/services/data/entities/factor/` |
| 3 | ORM model (`*FactorModel` with `polymorphic_identity`) | `src/infrastructure/models/` |
| 4 | Mapper (`*FactorMapper` with `discriminator`, `to_domain`, `to_orm`) | `src/infrastructure/repositories/mappers/factor/` |
| 5 | Domain port (`*FactorPort` interface) | `src/domain/ports/factor/` |
| 6 | Local repo (`*FactorRepository` with `_create_or_get`, `get_by_all`) | `src/infrastructure/repositories/local_repo/factor/` |
| 7 | IBKR repo (`IBKR*FactorRepository`) | `src/infrastructure/repositories/ibkr_repo/factor/` |
| 8 | Factory registration (local + IBKR dicts) | `src/infrastructure/repositories/repository_factory.py` |

**Read in this order:**
- [`src/domain/entities/factor/CLAUDE.md`](domain/entities/factor/CLAUDE.md) — full step-by-step with code templates
- [`src/infrastructure/repositories/local_repo/factor/CLAUDE.md`](infrastructure/repositories/local_repo/factor/CLAUDE.md)
- [`src/infrastructure/repositories/ibkr_repo/factor/CLAUDE.md`](infrastructure/repositories/ibkr_repo/factor/CLAUDE.md)
- [`src/infrastructure/repositories/mappers/CLAUDE.md`](infrastructure/repositories/mappers/CLAUDE.md)
- [`src/infrastructure/models/CLAUDE.md`](infrastructure/models/CLAUDE.md)
- [`src/application/services/data/entities/factor/CLAUDE.md`](application/services/data/entities/factor/CLAUDE.md)

**Critical rules:**
- `discriminator` in mapper must be **PascalCase** matching the DB `polymorphic_identity`.
- `polymorphic_identity` on the ORM model must match the mapper `discriminator` exactly.
- Every `elif` branch in `FactorMapper.to_domain` needs to cover each new `polymorphic_identity`;
  missing cases silently return `GenericFactor` — see [`src/infrastructure/repositories/mappers/factor/CLAUDE.md`](infrastructure/repositories/mappers/factor/CLAUDE.md).
- If the factor has `calculate_dependencies`, it uses **Branch A** of the resolution service
  (no IBKR call).  Without it (or with `get_dependencies` instead of `@property calculate_dependencies`),
  the service falls through to IBKR — see Factor Value Resolution below.

---

## 2. Creating a new Financial Entity (Asset / Holding / Portfolio)

**Read in this order:**
- [`src/domain/entities/finance/CLAUDE.md`](domain/entities/finance/CLAUDE.md) — entity hierarchy
- [`src/infrastructure/repositories/CLAUDE.md`](infrastructure/repositories/CLAUDE.md) — repository base pattern
- [`src/infrastructure/repositories/local_repo/finance/CLAUDE.md`](infrastructure/repositories/local_repo/finance/CLAUDE.md)
- [`src/infrastructure/repositories/local_repo/finance/financial_assets/CLAUDE.md`](infrastructure/repositories/local_repo/finance/financial_assets/CLAUDE.md) — financial asset specifics
- [`src/infrastructure/models/CLAUDE.md`](infrastructure/models/CLAUDE.md) — ORM / polymorphic inheritance

**For holding entities specifically** — see the Portfolio section below.

---

## 3. Factor Value Resolution — how a factor value is computed

The `FactorValueResolutionService` is the single entry point for computing and persisting
factor values.  It has two branches:

| Branch | Trigger | Path |
|--------|---------|------|
| **A — dynamic dependencies** | factor entity has `@property calculate_dependencies` | `_resolve_dynamic_dependencies` → recursively resolves each dep, then calls `calculate()` |
| **B — direct lookup** | no `calculate_dependencies` | DB lookup → IBKR fallback |

**Read:**
- [`src/application/services/data/entities/factor/CLAUDE.md`](application/services/data/entities/factor/CLAUDE.md) — full Branch A / B explanation with recursion diagram

**Common mistakes:**
- Naming the method `get_dependencies` instead of `@property calculate_dependencies` silently
  routes to Branch B (IBKR) even when Branch A is intended.
- Discriminator substring check was a historical bug — the check is now exact (`removesuffix('Model') == discriminator`).
- `_create_or_get` for a dependency uses the **dependency's own defaults** for `subgroup`,
  `data_type`, `frequency` — never the parent factor's attributes.

---

## 4. Portfolio / Holding hierarchy and `get_related_entities` contracts

**Portfolio type → holding types it contains:**

| Portfolio class | Holding types it contains |
|----------------|--------------------------|
| `CurrencyPortfolio` | `CurrencyPortfolioHolding` |
| `CompanySharePortfolio` | `CompanySharePortfolioHolding` |
| `Portfolio` (base) | `*PortfolioPortfolioHolding` (any sub-portfolio holding) |

**Naming rule:** A holding of a **sub-portfolio** inside a base `Portfolio` always ends
with `PortfolioPortfolioHolding` (double "Portfolio").  Examples:
- `CurrencyPortfolioPortfolioHolding` — a CurrencyPortfolio held inside a Portfolio
- `CompanySharePortfolioPortfolioHolding` — a CompanySharePortfolio held inside a Portfolio

**`get_related_entities` contract per repository:**

| Repository | `get_related_entities(id)` semantics |
|------------|--------------------------------------|
| `PortfolioRepository` | Queries `holdings` by `container_id`, dispatches via `holding_type` discriminator to typed repos, returns `*PortfolioPortfolioHolding` domain entities |
| `CurrencyPortfolioRepository` | Returns `CurrencyPortfolioHolding` domain entities for that portfolio |
| `CompanySharePortfolioRepository` | Returns `CompanySharePortfolioHolding` domain entities for that portfolio |
| `CurrencyPortfolioPortfolioHoldingRepository` | Returns the `CurrencyPortfolioModel` **asset** the holding points to |
| `CompanySharePortfolioPortfolioHoldingRepository` | Returns the `CompanySharePortfolioModel` **asset** the holding points to |
| `CurrencyPortfolioHoldingRepository` | Returns the `CurrencyModel` **asset** (currency) the holding holds |
| `CompanySharePortfolioHoldingRepository` | Returns `CompanySharePortfolioHolding` domain entities filtered by `company_share_portfolio_id` |

**Factor value resolution chain for a base Portfolio:**
```
PortfolioValueFactor.calculate_dependencies = [
    "CurrencyPortfolioPortfolioHoldingValueFactor",
    "CompanySharePortfolioPortfolioHoldingValueFactor",
]
  → _get_related_entities(Portfolio:N) → [CurrencyPortfolioPortfolioHolding:X, ...]
    → resolve CurrencyPortfolioPortfolioHoldingValueFactor for each holding
        → _get_related_entities(CurrencyPortfolioPortfolioHolding:X) → [CurrencyPortfolioModel:Y]
          → resolve CurrencyPortfolioValueFactor for CurrencyPortfolioModel:Y (already in DB)
      → CurrencyPortfolioPortfolioHoldingValueFactor.calculate({'CurrencyPortfolioValueFactor': V}) = V
  → PortfolioValueFactor.calculate({'CurrencyPortfolioPortfolioHoldingValueFactor': V}) = V
```

**Read:**
- [`src/infrastructure/repositories/local_repo/finance/portfolio/CLAUDE.md`](infrastructure/repositories/local_repo/finance/portfolio/CLAUDE.md) — naming convention + `get_related_entities` contracts

---

## 5. Adding a new Algorithm / Backtest / Live-trading project

**Read in this order:**
- [`src/application/managers/CLAUDE.md`](application/managers/CLAUDE.md)
- [`src/application/managers/project_managers/CLAUDE.md`](application/managers/project_managers/CLAUDE.md)
- Look at an existing project for patterns:
  - [`src/application/managers/project_managers/market_making_SPX_call_spread_project/CLAUDE.md`](application/managers/project_managers/market_making_SPX_call_spread_project/CLAUDE.md)
  - [`src/application/managers/project_managers/test_base_project/CLAUDE.md`](application/managers/project_managers/test_base_project/CLAUDE.md)
- [`src/application/services/misbuffet/algorithm/CLAUDE.md`](application/services/misbuffet/algorithm/CLAUDE.md)
- [`src/application/services/misbuffet/algorithm_framework/CLAUDE.md`](application/services/misbuffet/algorithm_framework/CLAUDE.md)
- [`src/application/services/misbuffet/engine/CLAUDE.md`](application/services/misbuffet/engine/CLAUDE.md)

---

## 6. Adding a web route or API endpoint

**Read:**
- [`src/interfaces/CLAUDE.md`](interfaces/CLAUDE.md)
- [`src/interfaces/flask/CLAUDE.md`](interfaces/flask/CLAUDE.md)
- [`src/application/services/api_service/CLAUDE.md`](application/services/api_service/CLAUDE.md)

---

## 7. ORM models and polymorphic inheritance

**Read:**
- [`src/infrastructure/models/CLAUDE.md`](infrastructure/models/CLAUDE.md) — discriminator column, single-table vs joined-table inheritance, `column_property` for shared columns across parent+subclass tables

**Critical:** when two joined-table models share a column name (e.g. `asset_id`, `container_id`),
add a `column_property` in `__mapper_args__["properties"]` to unify them — otherwise only
the base table column is written on INSERT and the subclass column stays NULL.

---

## 8. Repository / Port / Mapper pattern

**Read:**
- [`src/infrastructure/repositories/CLAUDE.md`](infrastructure/repositories/CLAUDE.md) — base pattern, CRUD, sequential ID generation
- [`src/infrastructure/repositories/mappers/CLAUDE.md`](infrastructure/repositories/mappers/CLAUDE.md) — `to_domain` / `to_orm`, discriminator dispatch
- [`src/domain/entities/CLAUDE.md`](domain/entities/CLAUDE.md) — what belongs in the domain layer

**Rule:** domain entities must be framework-agnostic (no SQLAlchemy).  All ORM logic lives
in models + mappers + repos.

---

## 9. Application Services

**Read:**
- [`src/application/services/CLAUDE.md`](application/services/CLAUDE.md) — service categories, patterns
- [`src/application/services/data/entities/CLAUDE.md`](application/services/data/entities/CLAUDE.md) — entity CRUD services
- Specific services as needed:
  - [`src/application/services/database_service/CLAUDE.md`](application/services/database_service/CLAUDE.md)
  - [`src/application/services/data_service/CLAUDE.md`](application/services/data_service/CLAUDE.md)
  - [`src/application/services/portfolio_service/CLAUDE.md`](application/services/portfolio_service/CLAUDE.md)

---

## 10. Testing

**Read:**
- [`src/tests/CLAUDE.md`](tests/CLAUDE.md)
- Domain logic: unit tests, no DB
- Infrastructure: mocks or local SQLite
- Run all: `python -m unittest discover tests`

---

## Layer map (quick reference)

```
src/
├── domain/              Pure Python — entities, ports, business rules
│   ├── entities/        Domain models (no SQLAlchemy)
│   └── ports/           Abstract interfaces (repository contracts)
├── infrastructure/      SQLAlchemy, IBKR, external systems
│   ├── models/          ORM models (joined-table inheritance)
│   ├── repositories/
│   │   ├── mappers/     Domain ↔ ORM conversion
│   │   ├── local_repo/  DB-backed implementations
│   │   └── ibkr_repo/   IBKR-backed implementations
│   └── repository_factory.py  Wires all repos together
├── application/         Orchestration (no framework coupling)
│   ├── services/        Use cases, factor resolution, portfolio valuation
│   └── managers/        Project-level runners (backtest, live trading)
└── interfaces/          Flask web + REST API
```
