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
