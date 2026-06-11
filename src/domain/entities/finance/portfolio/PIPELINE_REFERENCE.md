# Asset-Portfolio Pipeline Reference

This document describes the canonical 12-component pattern used to create a fully-typed
sub-portfolio pipeline for any asset class.  CompanyShare was the first implementation;
Currency follows the identical pattern.  Use this as the blueprint for every future asset type.

---

## Conceptual Hierarchy

Every asset-portfolio pipeline produces a 3-layer portfolio tree:

```
Portfolio (main)
  └─ <Asset>PortfolioPortfolioHolding          ← layer 2 holding (portfolio-in-portfolio)
       └─ asset = <Asset>Portfolio             ← layer 2 sub-portfolio
            └─ <Asset>PortfolioHolding         ← layer 3 holding (asset-in-sub-portfolio)
                 └─ asset = <Asset>            ← leaf financial asset (CompanyShare, Currency…)
```

The main portfolio holds *sub-portfolios* as assets (not raw shares/currencies).
Each sub-portfolio exclusively holds one asset type.

---

## The 12 Components

### Layer 1 — Domain entities  (3 files)

| # | Class | File | Purpose |
|---|-------|------|---------|
| 1 | `<Asset>Portfolio(Portfolio)` | `domain/entities/finance/portfolio/<asset>_portfolio.py` | Typed sub-portfolio; identification only |
| 2 | `<Asset>PortfolioHolding(PortfolioHolding)` | `domain/entities/finance/holding/<asset>_portfolio_holding.py` | Leaf holding: asset inside sub-portfolio |
| 3 | `<Asset>PortfolioPortfolioHolding(PortfolioHolding)` | `domain/entities/finance/holding/<asset>_portfolio_portfolio_holding.py` | Bridge holding: sub-portfolio inside main portfolio |

**Component 1 — `<Asset>Portfolio`**
```python
class CurrencyPortfolio(Portfolio):
    def __init__(self, id, name, start_date, end_date=None):
        super().__init__(id=id, name=name, start_date=start_date, end_date=end_date)
```
- No extra fields; just a typed subclass of `Portfolio`.

**Component 2 — `<Asset>PortfolioHolding`**
```python
class CurrencyPortfolioHolding(PortfolioHolding):
    def __init__(self, id, asset: Currency, portfolio: CurrencyPortfolio,
                 position: Position, start_date, end_date=None):
        super().__init__(id=id, asset=asset, container=portfolio,
                         position=position, start_date=start_date, end_date=end_date)
```
- `asset` = the leaf asset (Currency / CompanyShare / …)
- `container` = the typed sub-portfolio

**Component 3 — `<Asset>PortfolioPortfolioHolding`**
```python
class CurrencyPortfolioPortfolioHolding(PortfolioHolding):
    def __init__(self, id, portfolio: Portfolio, currency_portfolio: CurrencyPortfolio,
                 position: Position, start_date, end_date=None):
        super().__init__(id=id, portfolio=portfolio, asset=currency_portfolio, ...)
        self.currency_portfolio = currency_portfolio
```
- `asset` = the sub-portfolio (not a financial instrument)
- `container` = the main portfolio

---

### Layer 2 — Infrastructure ORM models  (3 files)

| # | Class | Table | Inherits | Key FKs |
|---|-------|-------|----------|---------|
| 4 | `<Asset>PortfolioModel` | `<asset>_portfolios` | `PortfolioModel` | `id → portfolios.id` |
| 5 | `<Asset>PortfolioHoldingModel` | `<asset>_portfolio_holdings` | `HoldingModel` | `id → holdings.id`, `asset_id → <assets>.id`, `<asset>_portfolio_id → <asset>_portfolios.id` |
| 6 | `<Asset>PortfolioPortfolioHoldingModel` | `<asset>_portfolio_portfolio_holdings` | `PortfolioHoldingsModel` | `id → portfolio_holdings.id`, `asset_id → <asset>_portfolios.id` (**FK override**) |

**Critical FK override in component 6:**
`PortfolioHoldingsModel` (and its parent `HoldingModel`) declares
`asset_id = ForeignKey('financial_assets.id')`.  The portfolio-in-portfolio model
**overrides** this column to point at the sub-portfolio table instead:
```python
asset_id = Column(Integer, ForeignKey('<asset>_portfolios.id'), nullable=False)
```
This is the only place where a holding's `asset_id` does not reference `financial_assets`.

**Relationships wiring (component 4 ↔ 5 ↔ 6):**
```
CurrencyPortfolioModel
  .currency_portfolio_holdings        back_populates ← CurrencyPortfolioHoldingModel.currency_portfolios
  .currency_portfolio_portfolio_holdings  back_populates ← CurrencyPortfolioPortfolioHoldingModel.currency_portfolio

CurrencyModel
  .currency_portfolio_holdings        back_populates ← CurrencyPortfolioHoldingModel.currencies
```

---

### Layer 3 — Domain ports  (2 files)

| # | Class | File |
|---|-------|------|
| 7 | `<Asset>PortfolioPort(ABC)` | `domain/ports/finance/portfolio/<asset>_portfolio_port.py` |
| 8 | `<Asset>PortfolioHoldingPort(ABC)` | `domain/ports/finance/holding/<asset>_portfolio_holding_port.py` |

Ports are currently minimal (no abstract methods enforced).
Add `@abstractmethod` stubs as the repository contract matures.

---

### Layer 4 — Mappers  (2 files)

| # | Class | File |
|---|-------|------|
| 9 | `<Asset>PortfolioMapper` | `infrastructure/repositories/mappers/finance/portfolio/<asset>_portfolio_mapper.py` |
| 10 | `<Asset>PortfolioHoldingMapper` | `infrastructure/repositories/mappers/finance/holding/<asset>_portfolio_holding_mapper.py` |

Each mapper exposes `to_domain(orm) → entity` and `to_orm(entity) → orm`.
The holding mapper creates *placeholder* domain objects for `asset` and `container`
(id-only) when reconstructing from ORM — load the full graph only when needed.

---

### Layer 5 — Repositories  (2 files)

| # | Class | File |
|---|-------|------|
| 11 | `<Asset>PortfolioRepository(<Asset>PortfolioPort)` | `infrastructure/repositories/local_repo/finance/portfolio/<asset>_portfolio_repository.py` |
| 12 | `<Asset>PortfolioHoldingRepository(BaseLocalRepository, <Asset>PortfolioHoldingPort)` | `infrastructure/repositories/local_repo/finance/holding/<asset>_portfolio_holding_repository.py` |

Both repositories follow the same interface:
- `_create_or_get(name, **kwargs)` — idempotent creation
- `get_by_id`, `get_by_name`, `get_all`, `add`, `update`, `delete`
- `get_related_entities(portfolio_id)` — delegates to `HoldingRepository.get_by_container_id`

---

## Checklist for a New Asset Type

Replace `<Asset>` / `<asset>` throughout with your new type (e.g. `Bond` / `bond`):

- [ ] `domain/entities/finance/portfolio/<asset>_portfolio.py`
- [ ] `domain/entities/finance/holding/<asset>_portfolio_holding.py`
- [ ] `domain/entities/finance/holding/<asset>_portfolio_portfolio_holding.py`
- [ ] `infrastructure/models/finance/portfolio/<asset>_portfolio.py`
- [ ] `infrastructure/models/finance/holding/<asset>_portfolio_holding.py`
- [ ] `infrastructure/models/finance/holding/<asset>_portfolio_portfolio_holding.py`
- [ ] `domain/ports/finance/portfolio/<asset>_portfolio_port.py`
- [ ] `domain/ports/finance/holding/<asset>_portfolio_holding_port.py`
- [ ] `infrastructure/repositories/mappers/finance/portfolio/<asset>_portfolio_mapper.py`
- [ ] `infrastructure/repositories/mappers/finance/holding/<asset>_portfolio_holding_mapper.py`
- [ ] `infrastructure/repositories/local_repo/finance/portfolio/<asset>_portfolio_repository.py`
- [ ] `infrastructure/repositories/local_repo/finance/holding/<asset>_portfolio_holding_repository.py`
- [ ] Add `<asset>_portfolio_holdings` relationship to the leaf asset ORM model (`<Asset>Model`)

---

## Implemented Pipelines

| Asset type | Sub-portfolio table | Leaf holding table | Portfolio-in-portfolio table |
|------------|--------------------|--------------------|------------------------------|
| CompanyShare | `company_share_portfolios` | `company_share_portfolio_holdings` | `company_share_portfolio_portfolio_holdings` |
| Currency | `currency_portfolios` | `currency_portfolio_holdings` | `currency_portfolio_portfolio_holdings` |
