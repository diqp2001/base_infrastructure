# CLAUDE.md – Algorithm

## General Role
The `Algorithm` folder contains core trading strategy logic. It defines user-created algorithms, specifying how data is processed and trades are executed. These algorithms subclass the `QCAlgorithm` class.

## Dependencies
- **Depends On**: 
  - `Common`: For base classes like `QCAlgorithm`, `Security`, and indicators.
  - `Data`: For receiving data streams into the algorithm.
- **Depended On By**:
  - `Engine`: To run the logic during backtesting or live trading.
  - `Launcher`, `Optimizer`: To run and analyze the user’s algorithm.

## Use
This is the folder where strategies are implemented, typically using `Initialize()` and `OnData()` methods in a class that inherits from `QCAlgorithm`.

## Invocation
Called by `Engine` through dynamic loading when a backtest or live run begins.

---

## Order Creation – Domain Entity Dependency Chain

When `UnifiedPortfolioManager.set_holdings()` triggers a trade, `TradeManager` must persist a chain of domain entities in strict dependency order. Each step requires the previous one to exist first.

```
1. Portfolio          portfolios.id           — must already exist (created at algo init)
2. FinancialAsset     financial_assets.id     — looked up by ticker symbol; no holding without it
3. Position           positions.portfolio_id  — created before holding (no holding_id FK on position)
4. Holding            holdings.asset_id       — references FinancialAsset + Position
                      holdings.container_id   — = portfolio_id
                      holdings.position_id    — FK → positions.id (position created first)
5. Account            accounts.id             — must already exist; resolved by first-available query
6. Order              orders.holding_id       — FK → holdings.id  (NOT NULL)
                      orders.account_id       — FK → accounts.id  (NOT NULL)
7. Transaction        transactions.order_id   — FK → orders.id
```

### Key Rules

- **Position comes before Holding** — `HoldingModel.position_id` is a FK to `positions.id`, so the
  position row must be flushed to the DB (to get its PK) before the holding INSERT.
- **PositionModel is intentionally minimal** — columns are `(portfolio_id, quantity, position_type)`
  only. There is no `symbol`, `is_active`, or `holding_id` on the model. Quantity updates are
  navigated via `Holding.position_id`, not by symbol lookup.
- **String names for SQLEnum columns** — pass `’LONG’`, `’MARKET’`, `’BUY’`, `’FILLED’` etc.
  as string literals, not enum instances. SQLAlchemy’s `Enum(PythonEnum)` column calls `.upper()`
  internally on string values; passing an enum object causes `AttributeError: has no attribute ‘upper’`.
- **`TradeManager` is called only by `UnifiedPortfolioManager`** — never directly from `QCAlgorithm`.
  `UnifiedPortfolioManager` is the orchestrator; `TradeManager` is the persistence executor.

### Orchestration Flow

```
QCAlgorithm.on_data(data)
  └─ UnifiedPortfolioManager.set_holdings(ticker, pct, data)
       ├─ resolves price from Slice.bars[symbol].close
       ├─ computes order_qty = target_qty - current_qty
       └─ TradeManager.execute_trade(ticker, order_qty, price, portfolio_id, ...)
            ├─ submit_order_fn(ticker, qty)          → OrderTicket  (QC in-memory)
            ├─ _register_order(ticket, portfolio_id, ticker)
            │    ├─ _resolve_holding_id(ticker, portfolio_id)
            │    │    ├─ lookup FinancialAsset by symbol
            │    │    ├─ return existing Holding if found
            │    │    ├─ INSERT Position (flush → get position.id)
            │    │    └─ INSERT Holding  (commit)
            │    ├─ _resolve_account_id()             → accounts.id
            │    └─ order_repo._create_or_get(...)    → Order entity
            ├─ _record_fill(...)                      → Transaction entity
            └─ _update_position(ticker, qty, portfolio_id)
                 └─ navigate Holding.position_id → UPDATE positions.quantity
```

---

## Portfolio Value FactorValue Snapshot Pattern

Called from `get_portfolio_value()` at the start of each `set_holdings` call
(guarded by `_last_pv_snapshot_time` — at most once per algorithm bar).

### Resolution Chain

```
UnifiedPortfolioManager.get_portfolio_value()
  └─ fv_repo.resolution_service.resolve_factor_value(
         portfolio_value_factor, portfolio_entity, current_time
     )
       └─ _resolve_factor_with_dependencies()
            └─ dependency 'holding_value' not in DB
                 └─ _handle_missing_dependency(factor_id=holding_value_id, portfolio_entity)
                      └─ _get_related_entities(portfolio_entity)
                           └─ PortfolioRepository.get_related_entities(portfolio_id)
                                └─ HoldingRepository.get_by_container_id(portfolio_id)
                      └─ for each holding → _resolve_holding_value_factor()
                           ├─ price  = _get_asset_price_for_holding_value()
                           │    └─ Strategy 3: currency asset → price = 1.0
                           └─ qty    = _get_holding_quantity()
                                └─ holding.position.quantity (via position_rel)
                      └─ returns transient FactorValue(value=sum(price×qty))
            └─ portfolio_value_factor.calculate({'holding_value': total}) → Decimal
            └─ _create_factor_value() → persisted FactorValue ✓
```

### Sub-Portfolio Holdings (e.g. `CompanySharePortfolioPortfolioHolding`)

A holding's `asset` can itself be another portfolio — not a financial instrument.
`CompanySharePortfolioPortfolioHolding` stores a `CompanySharePortfolio` as its
asset inside a parent `Portfolio`.  This creates a tree:

```
Portfolio (main)
  └─ CompanySharePortfolioPortfolioHolding
       └─ asset = CompanySharePortfolio (sub-portfolio)
            ├─ Holding A  →  AAPL position
            ├─ Holding B  →  GOOGL position
            └─ Holding C  →  MSFT position
```

When computing market value for such a holding, price × quantity is **not**
meaningful at the top level.  The correct approach is:

1. Detect that `holding.asset` is a `Portfolio` / `CompanySharePortfolio` subtype
   (check `type(holding.asset).__name__` or use `isinstance`).
2. Recursively call `_get_related_entities(holding.asset)` to retrieve all
   holdings of the sub-portfolio.
3. Compute each sub-holding's market value (`price × position.quantity`) and sum
   them — that sum is the market value of the sub-portfolio holding.
4. Propagate this value upward to the parent portfolio total.

**Key rule**: `_resolve_holding_value_factor` must check whether the holding's
asset is a portfolio type before attempting a price lookup.  If it is, delegate
to sub-holding aggregation instead of a direct FactorValue price lookup.

### Key Invariants

- The cash holding (currency asset, `quantity = initial_cash`) **must exist** before
  the first call.  Created by `PortfolioRepository._create_cash_holding()` during
  `_create_or_get()`.  If missing, `_get_related_entities` returns `[]` and the
  snapshot silently fails.
- `PositionModel` has **no** `holding_id` column — columns are
  `(id, portfolio_id, quantity, position_type)` only.  The FK link is
  one-directional: `HoldingModel.position_id → positions.id`.
- Currency holdings resolve price = 1.0 via Strategy 3 in
  `_get_asset_price_for_holding_value`.

---

## Portfolio Tree Traversal — Position Lookup

### Domain hierarchy (3 layers)

```
Portfolio                               ← top-level container (portfolios table)
  ├─ PortfolioHolding                   ← holds a FinancialAsset directly
  │    container = Portfolio
  │    asset     = FinancialAsset       ← HoldingModel.asset_id → financial_assets.id
  │    position  = Position (qty)
  │
  └─ CompanySharePortfolioPortfolioHolding   ← holds another portfolio
       container = Portfolio
       asset     = CompanySharePortfolio     ← asset_id → company_share_portfolios.id
                    ├─ PortfolioHolding → AAPL position
                    ├─ PortfolioHolding → GOOGL position
                    └─ PortfolioHolding → MSFT position
```

### ORM FK distinction

`HoldingModel.asset_id` declares `ForeignKey('financial_assets.id')`.
`CompanySharePortfolioPortfolioHoldingModel` **overrides** this column with
`ForeignKey('company_share_portfolios.id')` — pointing to a different table.

Consequence: a flat join of `holdings → financial_assets` on `asset_id` will
**miss** every ticker that lives inside a sub-portfolio because those `asset_id`
values point to `company_share_portfolios`, not `financial_assets`.

### Correct traversal rule (implemented in `_qty_in_container` / `_tickers_in_container`)

```
def _qty_in_container(ticker, container_id):
    total = 0
    # 1. Direct: HoldingModel(container_id=X, asset_id=financial_asset.id matching ticker)
    #            → sum Position.quantity
    # 2. Sub-portfolio: CompanySharePortfolioPortfolioHoldingModel(container_id=X)
    #            → for each sh: recurse _qty_in_container(ticker, sh.asset_id)
    return total
```

`_get_current_position_qty(ticker)` delegates to `_qty_in_container(ticker, main_portfolio.id)`.
`_get_all_held_tickers()` delegates to `_tickers_in_container(main_portfolio.id)` which applies
the same two-step pattern to collect every tradeable symbol across the full tree.

### Why this matters for `set_holdings`

`set_holdings(target_weights)` must:
1. Know the **actual current qty** of each ticker (including those inside sub-portfolios)
   before computing `order_qty = target_qty - current_qty`.
2. Discover tickers **currently held but absent from target_weights** so it can
   generate sell orders to liquidate them.

Both require full tree traversal — a flat single-level query is incorrect.
