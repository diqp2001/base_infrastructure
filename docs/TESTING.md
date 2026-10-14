# Testing

pytest runs every test (the older `unittest`-style files included). Configuration lives in
`pyproject.toml` (pytest, coverage, import-linter); classification and safety rules in
`tests/conftest.py`.

## Quick commands

| What | Command |
|---|---|
| Fast suite (no database server, no IBKR) — what you run while coding | `python -m pytest -m "not integration and not sql_server and not ibkr and not performance"` |
| Same, with coverage (gate: `fail_under` in pyproject) | add `--cov --cov-report=term` |
| Architecture rules | `lint-imports` (or `python -m pytest tests/architecture`) |
| Unit only / component only / contracts only | `-m unit`, `-m component`, `-m contract` |
| Property-based tests (Hypothesis) | `-m property` (vary with `--hypothesis-seed=N`) |
| End-to-end workflows | `-m e2e` |
| SQL Server integration (test database only) | `DB_NAME=base_infra_test python -m pytest -m sql_server` |
| IBKR live, read-only (Gateway logged in) | `IBKR_LIVE_SMOKE=1 python -m pytest -m ibkr` |
| Concurrency (real parallel writers need SQL Server) | `DB_NAME=base_infra_test python -m pytest -m concurrency` |
| Performance (SQL statements per operation) | `python -m pytest -m performance -s` |

In the Docker environment run them inside `app`, e.g.
`docker compose exec -e DB_NAME=base_infra_test app python -m pytest -m sql_server`.

## Markers (assigned from the location in tests/conftest.py)

| Marker | Location / meaning | Needs |
|---|---|---|
| `unit` | `tests/unit/` and every test not classified otherwise | nothing |
| `component` | `tests/component/` and suites on an in-memory SQLite portfolio | nothing |
| `contract` | `tests/contracts/`, `tests/repositories/` — the same behaviour on every implementation | nothing (SQLite variant) |
| `architecture` | `tests/architecture/` — import-linter contracts, import cycles, package layout | nothing |
| `e2e` | `tests/end_to_end/` — workflows across adapter, repositories, services and portfolio | nothing |
| `property` | Hypothesis invariants (pricing, returns, normalisation, metrics) | nothing |
| `performance` | `tests/performance/` — statement-count ceilings | nothing (excluded from the fast suite) |
| `integration` | real infrastructure | see below |
| `sql_server` | SQL Server; also the `[sql_server]` variant of every contract test | `DB_NAME=*_test` |
| `ibkr` | logged-in IB Gateway / TWS, read-only | `IBKR_LIVE_SMOKE=1` |
| `concurrency` | two writers on the same records | SQL Server for the real-thread tests |

## Safety rules (enforced for every test)

- **No IBKR connection** unless the test is marked `ibkr` *and* `IBKR_LIVE_SMOKE=1` — the socket
  (`EClient.connect`) and `RepositoryFactory.create_ibkr_client` are blocked; not-opted-in `ibkr`
  tests are skipped. Live tests replace every order-sending method (`placeOrder`, `cancelOrder`,
  `reqGlobalCancel`, `exerciseOptions`, …) by one that raises: they can only read.
- **Never the application database**: `sql_server` tests run only when `DB_NAME` ends in `_test`
  (skipped otherwise). `tests/persistence.py` refuses any other name, creates the test database
  if missing, rebuilds its schema once per session and empties it before each test.
- No order is ever sent by a test: submissions go to Mocks or blocked clients.

## Persistence backends (`tests/persistence.py`)

`backend` fixture → each contract test runs twice:

- `sqlite` — in-memory, **foreign keys ON** (SQLite ignores them by default; SQL Server does not);
- `sql_server` — the test database (`base_infra_test`; `sqlserver-init` creates it with the
  application database).

In-memory SQLite gives all sessions of one thread the same DBAPI connection, so tests that need two
independent clients (interleaved / parallel writers) run on SQL Server only.

## Test data

- `tests/misbuffet/sqlite_portfolio.py` — `SqlitePortfolio`: a real portfolio tree built through the
  repositories (cash tree, shares, lazy sub-portfolios), `seed_close()` stores raw IBKR-style daily
  bars (stamped at their start), `trade()` books through `TradeManager`, readers for quantities,
  cash, orders, transactions and factor values. `engine=` reuses a prepared backend, `live=True`
  resumes an existing book (restart semantics).
- IBKR responses are constructed callbacks played on a real `IBTWSClient`
  (`tests/contracts/adapters/`, `tests/end_to_end/`).

## Architecture rules

`pyproject.toml` `[tool.importlinter]`:

1. domain does not import infrastructure, application, interfaces, SQLAlchemy or ibapi;
2. application never imports ORM models directly (only through repositories);
3. infrastructure does not import the application layer;
4. only the interfaces layer imports the interfaces layer.

Existing violations (83 imports, 2026-10-14) are listed in `ignore_imports` as known debt — never
add to the lists to make a change pass. `tests/architecture/import_cycles_baseline.json` holds the
10 existing sibling-package cycles; a new cycle fails, a removed one must be removed from the
baseline (`python -m tests.architecture.import_cycles --update`). Every source directory must be a
package (`__init__.py`), otherwise the rules cannot see it.

## CI (`.github/workflows/python-app.yml`)

| Stage | When | Runs |
|---|---|---|
| 1 | every push / PR | `lint-imports`, `pytest -m "unit or architecture"` |
| 2 | pull requests, manual | fast suite with coverage (`coverage.xml` artifact) |
| 3 | nightly, manual | SQL Server service container + `base_infra_test`, `pytest -m sql_server` |

IBKR tests never run in CI.

## Portfolio context (transactions -> holdings -> valuations -> factor values)

Semantics the context tests rely on (`tests/component/portfolio_context/`, `tests/misbuffet/test_set_holdings_chain.py`):

- **Entry points**: `UnifiedPortfolioManager.set_holdings` (targets; repeating a target sends nothing) ->
  `TradeManager.execute_trade`, which books order + transaction + position + cash leg as one database
  transaction and refuses a zero quantity or a non-positive / non-finite price before submitting.
  Side, quantity and fill price are stored on the order; the transaction records its execution.
- **Accounting**: cash moves by exactly `round(|qty| x fill price)`. No fees, commissions, cost basis,
  realised / unrealised P&L, deposits, withdrawals, reversals or multi-currency cash are modelled.
- **Tree**: the main portfolio holds only sub-portfolio links (Currency, CompanyShare, CompanyShareOption);
  share holdings live in the CompanySharePortfolio, which may hold nested CompanySharePortfolios.
- **Valuation** is explicit (no events): `get_portfolio_value` -> `PortfolioService.calculate_value` walks
  the tree, recomputes every leaf holding value (`quantity x last closed price`, `force_recalculate`)
  and stores one total per portfolio and date. Parent = sum of its direct children, so each position
  is counted once. A held position without a price raises: no totals are stored and nothing is traded.
- **Batch resolution** (`FactorValueBatchResolutionService`) plans `DependencySpec` prerequisites of the
  declared factor type first (close -> mid_price -> value) and raises on a dependency cycle.
- **Factor resolution** reuses a stored value for the same (factor, entity, date); after a trade the
  caller must force a recalculation (the valuation always does).
- **Time**: positions are current state only (see the gap below); a valuation writes rows only at its
  own timestamp and never rewrites another date.

## Known gaps (pinned as expected failures — they flip to "unexpected success" when fixed)

| Test | Gap |
|---|---|
| `test_trade_manager::test_cash_keeps_cents` | `positions.quantity` is INTEGER: cash is booked in whole dollars (needs a DECIMAL migration) |
| `test_spx_v2_order_legs::test_call_spread_entry_sends_both_legs_together` | SPX v2 enters a single short call (strategy decision) |
| `test_normalization_and_metrics::test_cross_sectional_zscore_does_not_use_future_values` | `FactorNormalizer._apply_cross_sectional_zscore` uses each ticker's full history (used by other projects' trainers) |
| `test_persistence_contracts::test_natural_key_is_unique`, `test_concurrency::test_two_resolvers_racing…` | `factor_values` has no unique key on (factor, entity, type, date) — needs a migration after de-duplication |
| `test_persistence_contracts::test_company_share_needs_no_placeholder_references` | new companies / exchanges are linked to placeholder country / industry ids |
| `test_transaction_valuation_context::test_revaluing_a_past_date_uses_the_quantities_held_then` | positions have no history: revaluing a past date after a later trade uses today's quantities and overwrites that date's snapshot |
