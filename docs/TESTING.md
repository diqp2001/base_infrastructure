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

Every test lives under `tests/` (`testpaths`); a test file anywhere else is never collected. The former
`src/tests` suites were moved in BI-003 (2026-10-20): `tests/unit/application/heston_slv/` (the calibrator class is
`slow` + `performance`, minutes per test), `tests/market_making_spx/` (original SPX project strategy and hedging),
`tests/unit/test_factor_value_chain.py`, `tests/unit/test_entity_factor_mapping.py`,
`tests/unit/domain/test_trading_factors.py`, and the SQLite repository / ORM suites in `tests/repositories/`
(component marker).

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
- **Time**: positions.quantity is the current state; a valuation at a past date reads the quantity held
  then, rebuilt from the fills executed after it (`PositionRepository.get_quantity_at`: current quantity
  minus the BUY / SELL orders with an EXECUTED transaction after the date). A valuation writes rows only
  at its own timestamp and never rewrites another date.

## Factor resolution coverage (every `calculate()`)

Factor classes are discovered from `src/domain/entities/factor` (`tests/component/factor_context/factor_catalog.py`),
so a new factor is covered automatically.

- `test_factor_dependency_wiring.py` — one test per class (141, incl. classes whose `calculate()` comes from a
  mixin such as `SeriesPriceReturn` / `OptionModelPrice`): buildable with defaults, a local repository,
  `calculate_dependencies` declared, every `calculate()` parameter fillable by the service, every dependency
  resolvable (DependencySpec: repository + a definition that satisfies the spec; string: a buildable factor
  type or an entity attribute such as `Position`).
- `test_factor_resolution_end_to_end.py` — every wired factor resolved through `FactorValueResolutionService`
  in a fresh SQLite market (`factor_world.py`: 300 daily bars, a portfolio with shares and options, USD,
  the dated SOFR future (expiry 18 Mar 2026), an option, and on demand SPX / ESH6 / an ESH6 call with 30 bars): `calculate()` must receive every declared dependency and return a
  finite number; independent value checks for prices, holdings, portfolios, rates, implied vol and delta.
  ML factors get a stand-in model provider (the service must hand it the dependencies).

Factor definitions are identified by name **and frequency**: every repository `_create_or_get` passes the
requested frequency to its lookup and creates the definition at that frequency when it does not exist
(e.g. `mid_price` at 1d next to 5m). A spec with `frequency=SELF` therefore always finds or creates its
dependency — this used to make resolution order decide whether delta / gamma / vega resolved.

Price-history factors (returns, moving averages, momentum, slopes, Sharpe / Sortino, drawdowns, z-scores) declare
`DependencySpec(CompanyShareFactor, group='price', name_in=['close'], lookback=N)`: the service delivers the N
latest closed daily closes, oldest first, ending at the bar a single-value lookup would use (no look-ahead, same
staleness rule); `lookback='ytd'` delivers the last close of the previous year + every close of the year. A window
not fully stored gives no value. Tests: `test_history_factor_receives_its_window_of_trailing_closes`,
`test_value_of_history_factor`, `test_a_bar_still_open_at_the_target_is_never_in_the_series`.

Former library-route factors (two prices with lags as stored `FactorDependency` rows) read windows of closed
bars the same way (`DependencySpec.lookback`, `key=` names the entry in `calculate(dependencies)` when two specs
share a factor type):

| Factor | Inputs |
|---|---|
| `*PriceReturn` (CompanyShare, CompanyShareOption, Index, IndexFuture, IndexFutureOption) — `SeriesPriceReturn` | the instrument's closes over its subgroup window: daily 2, weekly 6, monthly 22 (minutes: 2 opens) |
| `CompanyShareAvgTurnover6m` | mean of the last 126 volumes |
| `CompanyShareMonthlyPriceRange` | high 1 bar ago − low 21 bars ago |
| `CompanyShareVpt52w20dLag` | volume 20 bars ago × (close 20 bars ago / close 272 bars ago − 1) |
| `BondFutureDiscountedValue` / `BondFutureForwardPrice` — `FutureCarryInputs` | last close, the settlement currency's `CurrencyYieldFactor` (`BondFutureRepository.get_related_entities` → its currency), years to the future's expiry |

Option pricing models (`OptionModelPrice`: Heston, Heston-SLV, Bates, SABR, Hull-White, Dupire) take S, σ, r from
data and K, T, call/put from the option (as BSM / CRR); their model parameters (`v0`, `kappa`, `theta`, `xi`, `rho`,
`lambda_j`, `alpha`, `beta`, `nu`, `a`, `sigma_r`, ...) come from the factor-library entry's `"parameters"`, which the
service passes as `dependencies['parameters']` (`factor_definition_config.library_parameters`, for factors with
`LIBRARY_PARAMETERS`). A required parameter missing from the entry gives no value — the library entries do not
set them yet, so these factors produce nothing until they are calibrated / configured. Tests: each model reduced
to Black-Scholes reprices the option's market price; without parameters, no value.

Classes the service is not meant to feed are listed in `factor_catalog.NOT_SERVICE_RESOLVABLE` with the reason
and skipped (basket / share-portfolio options, option-portfolio model prices, implied correlation and implied
dividend yield, generic Option* / Future* / IndexFutureOption* / Swap models, `PortfolioHoldingValue`, position /
transaction value, `ConstituentScore`, `CurrencyRate`, `BondFutureAnnualizedRollYield` — no front → deferred contract
relation).

Gaps still pinned as strict xfails: `CompanySharePortfolioPriceReturn` (no stored portfolio prices) and option
trades ignoring the contract multiplier (`TradeManager` cash leg, option holding value).

## factor_values natural key

`(factor_id, entity_id, entity_type, date)` is unique (`uq_factor_values_natural_key`): new databases get it
from `FactorValueModel`; an existing database gets the index at startup (`BaseFactory._migrate_schema`) only
when it has no duplicates — otherwise a warning asks for the explicit clean-up, which keeps the most recent
row of each key:

    python -m src.infrastructure.database.factor_value_dedup            # dry run
    python -m src.infrastructure.database.factor_value_dedup --apply    # delete duplicates + create the index

`FactorValueRepository.add` with a key already stored (e.g. two resolvers racing) stores nothing and returns
the stored value; `update` replaces a value. Tests: `tests/contracts/test_factor_value_unique_key.py`.

## Known gaps (pinned as expected failures — they flip to "unexpected success" when fixed)

| Test | Gap |
|---|---|
| `test_trade_manager::test_cash_keeps_cents` | `positions.quantity` is INTEGER: cash is booked in whole dollars (needs a DECIMAL migration) |
| `test_spx_v2_order_legs::test_call_spread_entry_sends_both_legs_together` | SPX v2 enters a single short call (strategy decision) |
| `test_normalization_and_metrics::test_cross_sectional_zscore_does_not_use_future_values` | `FactorNormalizer._apply_cross_sectional_zscore` uses each ticker's full history (used by other projects' trainers) |
| `test_persistence_contracts::test_company_share_needs_no_placeholder_references` | new companies / exchanges are linked to placeholder country / industry ids |
