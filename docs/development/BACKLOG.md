# base_infrastructure — development backlog

Baseline audit (BI-001) of 2026-10-20 on `main` @ `8e270b46`. Every status below is backed by evidence that
was checked in the repository or by running the commands listed in [Baseline measurements](#baseline-measurements).
Agent workflow rules: [`AGENTS.md`](../../AGENTS.md). Test conventions: [`docs/TESTING.md`](../TESTING.md).

**Status values** — *complete*: verified done, acceptance criteria met; *partial*: implemented and tested in
part, gaps listed; *missing*: not implemented; *blocked*: needs an external decision, service or approval.
**Size** — S ≤ 1 day, M 2–3 days, L ≥ 1 week of agent work.

---

## Baseline measurements

| Check | Command | Result (2026-10-20) |
|---|---|---|
| Import contracts | `lint-imports` | 4 / 4 kept; ignored (debt): domain 2, application→ORM 60, infrastructure→application 20, interfaces 1 |
| Fast suite + coverage (CI stage 2) | `pytest -m "not integration and not sql_server and not ibkr and not performance" --cov` | 1156 passed, 45 skipped, 10 xfailed (known defects), 0 failed; coverage **34.5 %** (`fail_under` 31.5, recorded baseline 32.0) |
| Full suite | `pytest` | 1158 passed, 97 skipped, 10 xfailed |
| Tests outside `testpaths` | `pytest src/tests` | **329 tests in `src/tests` are never run by CI** (2 more `test_*.py` at the repository root). Run once: without `heston_slv`, 255 passed / **15 failed** (delta-hedge integration 4, factor value chain 5, financial-entity ORM 6 — e.g. `NOT NULL constraint failed: financial_assets.start_date`); `heston_slv` calibration did not finish in 5 min (stopped) — see BI-003 |
| Docker | `docker compose config`, `docker ps` | compose valid; `app`, `monitor` (healthy), `sqlserver` (healthy) up 23 h; `ibkr` not running |
| SQL Server from the container | `tests/integration/test_docker_services.py::…::test_sqlalchemy_reaches_sql_server` | passed (read-only); the write round-trip test was not run against the app database |
| Type checking / linting | — | **none configured** (no mypy, ruff, flake8, pylint) |
| Secrets | `git ls-files`, `git log --diff-filter=A`, credential-pattern scan | no `.env`, `.env.windows`, `secrets/` ever committed; no credential literals in tracked code |
| TODO / FIXME | `git grep` | 4 in `src`; 10 `raise NotImplementedError` |

Known defects pinned as strict expected failures (each flips to a failure when fixed): option trades ignore the
contract multiplier; cash booked in whole dollars (`positions.quantity` INTEGER); `force_recalculate` reuses stored
dependencies; holdings get share-price factors stored; companies linked to placeholder country / industry ids;
SPX v2 universe misses the dated SOFR contract; a position without greeks counts as delta 0; the "call spread"
enters a single naked call; cross-sectional z-score uses future values; one backtest-engine bug
(`tests/misbuffet/test_backtest_engine.py`).

---

## Milestones and execution order

| Milestone | Items (in order) | Goal |
|---|---|---|
| **M0 — Baseline and guard rails** | BI-001 ✔, BI-004 ✔, **BI-003**, BI-005, BI-002 | trustworthy gates, safe configuration, reproducible environment |
| **M1 — Persistence and portfolio correctness** | BI-006, BI-007, BI-008, BI-009, BI-010 | transactions, holdings and portfolio values are correct and atomic |
| **M2 — Factor and market-data correctness** | BI-012, BI-025, BI-013, BI-026, BI-011, BI-014, BI-027 | point-in-time, reproducible factor values from reliable data |
| **M3 — Research and ML** | BI-015, BI-016, BI-017, BI-018, BI-019 | reproducible models, artifacts and backtests |
| **M4 — Broker and operations (paper only)** | BI-020, BI-021, BI-022, BI-023, BI-024 | safe broker lifecycle, risk gate, read-only operations view |

Dependency rules: an item starts only when its dependencies are *complete* (or explicitly waived by the user).
Within a milestone, follow the listed order. M4 items never enable live trading.

**Recommended next issue: BI-003** (all dependencies met, local only, unblocks every later item's definition of done).

GitHub issues created 2026-10-20 for the highest-priority actionable items: #575 (BI-003), #576 (BI-005), #577 (BI-002), #578 (BI-025), #579 (BI-026). The other items are issue-ready in this file.

---

## Items

### BI-001 — Audit repository and record baseline
- **Priority** P0 · **Size** M · **Depends on** — · **Status: complete** (this document, `AGENTS.md`)
- **Scope** modules, tests, architecture rules, CI, TODOs, incomplete implementations; no business-logic changes.
- **Acceptance** baseline measurements recorded with commands; every BI item has a status with evidence; next issue named.
- **Evidence** this file; measurements above.

### BI-002 — Verify clean Linux/Docker startup
- **Priority** P0 · **Size** M · **Depends on** BI-005 · **Status: partial** · **GitHub** #577
- **Scope** dependency install, `docker compose up` from a clean state, database connectivity, app start, VS Code debugging.
- **Acceptance** (1) a clean build of `base_infrastructure-dev:py3.13` from `requirements-dev.txt` succeeds; (2) `docker compose up sqlserver app monitor` reaches healthy; (3) `pip check` clean; (4) the read-only SQL connectivity test passes in `app`; (5) the fast suite passes inside `app`; (6) the VS Code launch configurations start; (7) steps documented in `.devcontainer/README.md`.
- **Evidence** `docker-compose.yml` validates; services up and healthy; SQL test passed in `app`; `pip check` clean in `app` (Python 3.13.16); `.devcontainer/devcontainer.json` (service `app`, `post-start.sh`); `.vscode/launch.json` has 3 configurations (main, Flask, monitoring).
- **Gaps** no clean rebuild verified (recreating `app`/`ibkr` is an approval gate: VS Code attachment, 2FA); the container checkout (`1aa0443c`) is behind `main`; `ibkr` service not running; fast suite not run inside the container in this audit.

### BI-003 — Verify automated quality gates
- **Priority** P0 · **Size** S–M · **Depends on** BI-001 · **Status: partial** · **← next** · **GitHub** #575
- **Scope** fast tests, coverage, import contracts, type checks, linting; repair configuration without weakening thresholds.
- **Acceptance** (1) every test file is either collected by CI or deliberately removed (triage of `src/tests`, 329 tests, and root `test_*.py`, with the decision recorded); (2) `fail_under` raised to the measured floor (34.5 % → 34.0) — never lowered; (3) a linter (ruff) and a type checker (mypy) run in CI in report-only mode with a recorded baseline, failing only on new violations (new dev dependencies need approval); (4) CI stages documented in `docs/TESTING.md` match `.github/workflows/python-app.yml`.
- **Triage input** `src/tests`: 15 failing tests (`unit/market_making/test_delta_hedge.py` 4, `unit/test_factor_value_chain.py` 5, `unit/test_financial_entity_orm.py` 6) — stale against current code or real defects, to be decided per test (fix, move to `tests/` as a pinned xfail with the reason, or delete); `unit/heston_slv/test_heston_slv.py::TestHestonCalibrator` too slow for the fast suite (mark `slow` / `performance`).
- **Evidence** `.github/workflows/python-app.yml` (stage 1 `lint-imports` + unit/architecture; stage 2 fast suite + coverage on PRs; stage 3 SQL Server nightly); `pyproject.toml` markers, `fail_under = 31.5`, import contracts; `testpaths = ["tests"]` excludes `src/tests`; no lint / type-check tooling in `requirements-dev.txt`.

### BI-004 — Document coding-agent rules
- **Priority** P0 · **Size** S · **Depends on** BI-001 · **Status: complete**
- **Acceptance** `AGENTS.md` covers boundaries, commands, branch isolation, retry limits, approval gates, prohibited actions.
- **Evidence** `AGENTS.md` (this change).

### BI-005 — Audit secrets and configuration
- **Priority** P0 · **Size** S–M · **Depends on** BI-001 · **Status: partial** · **GitHub** #576
- **Scope** committed credentials, unsafe defaults, environment validation, accidental live-trading access.
- **Acceptance** (1) no secret in tracked files or history (done); (2) the broker refuses to send orders when the connected account's type (paper `DU…` vs live) does not match `IBKR_ACCOUNT_MODE`, with a test; (3) every IBKR connection path either goes through `ibkr_settings` or is documented as data-only; (4) generated artifacts are untracked (`mlruns/` 424 files, two `.pkl` artifacts under `src/…/implied_vol_ml/artifacts/`) after approval; (5) settings validated at startup with clear errors.
- **Evidence** `.gitignore` covers `.env`, `.env.windows`, `secrets/`, `.monitor/`, `results/`, `weights/`, `mlruns/`; history has no `.env*`/`secrets/` additions; live guard `src/application/services/misbuffet/brokers/ibkr/ibkr_settings.py:55` (`IBKR_ACCOUNT_MODE=live` requires `IBKR_ALLOW_LIVE=yes`), used only by `interactive_brokers_broker.py`; the only `placeOrder` call is `IBTWSClient.py:554`.
- **Gaps** the guard checks environment variables only — the account TWS is logged into is never verified; ~20 hard-coded `7497` connections (project trainers, `market_data.py`, `broker_factory.py`) bypass `ibkr_settings`; `mlruns/` still tracked despite `.gitignore`; CI uses a literal fallback SA password (CI-only service).

### BI-006 — Test SQLAlchemy session and transaction boundaries
- **Priority** P1 · **Size** L · **Depends on** BI-003 · **Status: partial**
- **Acceptance** (1) one documented owner of commit / rollback per use case (repositories stop committing inside multi-step operations, or a unit-of-work wraps them); (2) tests: commit, rollback on failure in any step, nested operations, session reuse after failure; (3) the `TradeManager._book_atomically` workaround replaced by the real boundary with its tests still green.
- **Evidence** `tests/component/portfolio_context/test_resilience.py` (13 tests: atomic booking, rollback, retry), `tests/contracts/test_concurrency.py` (3); repositories commit themselves (327 `session.commit()` in 142 local repository files, 135 `rollback()`); atomic booking works by swapping `session.commit` for `flush` (`src/application/services/misbuffet/algorithm/trade_manager.py:114-150`); no unit-of-work in `src`; ~600 `except Exception` blocks in repositories that print and return `None`.

### BI-007 — Enforce DDD dependency boundaries
- **Priority** P1 · **Size** L (split per module) · **Depends on** BI-003 · **Status: partial**
- **Acceptance** each removed `ignore_imports` entry is deleted from `pyproject.toml` in the same change; behaviour unchanged (tests green); domain list reaches 0 first.
- **Evidence** contracts enforced in CI; debt: domain → infrastructure/application 2 (`domain.database`, `currency_rate_factor`), application → ORM 60 (18 modules incl. `factor_value_resolution_service`, `portfolio_service`, `trade_manager`), infrastructure → application 20 (model providers injected from repositories, `repository_factory → broker_factory`), interfaces 1.

### BI-008 — Add repository contract tests
- **Priority** P1 · **Size** M · **Depends on** BI-006 · **Status: partial**
- **Acceptance** one parametrised contract per port run against the local (SQLite + SQL Server) and IBKR implementations: round trip, missing record, update, delete, mapping of every field.
- **Evidence** `tests/contracts/repositories/test_persistence_contracts.py` (16: factor values, referential integrity; 1 strict xfail for placeholder references), `tests/repositories/test_all_repositories.py` (8: every repository builds, factory registration, factor round trip, discriminator map), `tests/contracts/adapters/test_ibkr_history_adapter.py` (19). Gap: no shared contract run against both local and IBKR implementations of the same port.

### BI-009 — Test transaction-to-holding propagation
- **Priority** P1 · **Size** M · **Depends on** BI-006 · **Status: partial**
- **Acceptance** tests for buy, sell, partial fill, fee / commission, cash movement, duplicate processing (idempotent), average cost basis, realised and unrealised P&L; the two pinned defects fixed (cash cents, option multiplier).
- **Evidence** `tests/component/portfolio_context/test_transaction_valuation_context.py`, `test_value_propagation.py`, `tests/misbuffet/test_trade_manager.py`, `test_set_holdings_chain.py`; cost basis appears in 1 test file; strict xfails `test_cash_keeps_cents` (INTEGER `positions.quantity`), `test_option_trade_and_value_use_the_contract_multiplier`.

### BI-010 — Test sub-portfolio and main portfolio aggregation
- **Priority** P1 · **Size** M · **Depends on** BI-009 · **Status: partial**
- **Acceptance** holdings, cash and market value reconcile at every level (holding → sub-portfolio → main) after trades, price moves, quantity corrections and failures; the two pinned propagation defects fixed.
- **Evidence** `tests/component/portfolio_context/test_portfolio_value_layers.py`, nested sub-portfolio test in `test_transaction_valuation_context.py`; strict xfails in `test_value_propagation.py:237` (`force_recalculate` reuses stored dependencies) and `:256` (share-price factor stored for holdings).

### BI-011 — Test factor dependency resolution
- **Priority** P1 · **Size** M · **Depends on** BI-012 · **Status: partial**
- **Acceptance** ordering, cycle detection (single-value resolver too), missing values, dynamic dependencies, calculation errors, repeated requests — each with a test.
- **Evidence** `tests/component/factor_context/` (wiring: 141 classes, 98 pass, 43 listed as not service-resolvable with reasons; end-to-end values per family); batch resolver has iterative DFS cycle detection + tests (`factor_value_batch_resolution_service.py`, `tests/test_factor_value_batch_resolution.py`). Gap: `FactorValueResolutionService` (recursive) has no cycle guard.

### BI-012 — Enforce point-in-time factor calculations
- **Priority** P1 · **Size** M · **Depends on** BI-003 · **Status: partial**
- **Acceptance** (1) a re-run of a backtest recomputes derived values from current inputs — stored derived values are reused only when their inputs are unchanged (fixes the pinned `force_recalculate` defect); (2) cross-sectional z-score uses only data available at the date (pinned xfail); (3) timezone of stored bars documented and tested (exchange-local naive vs UTC); (4) trading calendar from `pandas_market_calendars` (already a dependency) instead of the hand-written NYSE calendar.
- **Evidence** bar look-ahead guard (`FactorValueRepository.get_latest_available_bar`), `src/domain/entities/factor/bar_calendar.py` + `tests/unit/domain/test_bar_calendar.py`, `tests/spatio_temporal_momentum/test_stm_lookahead.py` (8), `tests/contracts/test_orm_schema.py` (timezone normalisation). Observed 2026-10-20: an SPX v2 re-run reused derived values (mid price, greeks, holding values) stored by an earlier run with stale prices until they were deleted by hand.

### BI-013 — Harden historical market-data persistence
- **Priority** P1 · **Size** M · **Depends on** BI-012 · **Status: partial**
- **Acceptance** duplicates, overlapping downloads, interval boundaries and idempotent updates tested; gaps in a series detected and reported at import (not discovered at decision time); instrument identity stable (conId).
- **Evidence** unique natural key `uq_factor_values_natural_key` + `src/infrastructure/database/factor_value_dedup.py` + `tests/contracts/test_factor_value_unique_key.py`; `tests/contracts/adapters/test_ibkr_history_adapter.py`. Gap: no gap report at import; values stored as `String(255)`.

### BI-014 — Standardize factor definition and value contracts
- **Priority** P1 · **Size** M · **Depends on** BI-012 · **Status: partial**
- **Acceptance** definitions validated (group, subgroup, source, frequency, data type); every stored value carries provenance (computed-at time, source / run id, input version) so stale derived values are detectable; numeric values stored with a numeric type.
- **Evidence** `Factor.__init__` validates `GROUPS` / `SUBGROUPS` / `SOURCES` (`src/domain/entities/factor/factor.py`); definitions keyed by name + frequency; `factor_values` columns: factor_id, entity_id, entity_type, date, value (`String(255)`), currency_id — no provenance.

### BI-015 — Implement model and artifact lifecycle
- **Priority** P2 · **Size** L · **Depends on** BI-014 · **Status: partial**
- **Acceptance** universe, constituents, features, training runs, metrics, artifacts and scores persisted with reproducible metadata (data window, feature hash, config hash, code version); artifacts stored outside `src/` and untracked; safe deserialisation.
- **Evidence** domain chain `MLModel → ModelTraining → ModelArtifact` with repositories; `tests/test_universe_and_ml.py`; two pickled artifacts tracked under `src/application/services/data/entities/factor/implied_vol_ml/artifacts/`; `mlruns/` tracked.

### BI-016 — Complete implied-volatility ML factor lifecycle
- **Priority** P2 · **Size** M · **Depends on** BI-015 · **Status: partial**
- **Acceptance** reuse of a compatible valid artifact, training when missing / invalid, inference inside factor resolution, and failure paths (corrupt artifact, training failure) each tested; errors surfaced, not printed and swallowed.
- **Evidence** `implied_vol_ml_model_provider.py`: regime fingerprint (universe + feature + config hashes) and validity window checked before reuse, training when none matches; factor dependencies are financial only (`company_share_option_implied_vol_ml_factor.py`); provider injected by the repository (infrastructure → application debt); errors handled by `print` + `return None`.

### BI-017 — Build spatio-temporal momentum pipeline
- **Priority** P2 · **Size** M (verification) · **Depends on** BI-015 · **Status: partial (implemented, verification pending)**
- **Acceptance** universe, features, tensors, training, scoring and artifact persistence verified end to end on a deterministic dataset; results reproducible across two runs.
- **Evidence** projects `spatio_temporal_momentum_project{,_5m,_full}`; `tests/spatio_temporal_momentum/` (8 files: dataset, features, look-ahead, model, persistence, report / dashboard, trading cycle, training); `/stm` dashboard and PDF report.

### BI-018 — Establish backtest correctness tests
- **Priority** P2 · **Size** M · **Depends on** BI-010, BI-012 · **Status: partial**
- **Acceptance** historical universe membership, signal timing, execution assumptions, transaction costs, returns, drawdowns and reproducibility tested; the pinned engine defect fixed.
- **Evidence** `tests/misbuffet/test_backtest_engine.py` (11, 1 expected failure), `test_performance_metrics.py` (15), SPX v2 report metrics (`tests/market_making_spx_v2/test_spx_v2_report.py`). Gaps: transaction costs, as-of universe membership, reproducibility check.

### BI-019 — Add factor and portfolio performance benchmarks
- **Priority** P2 · **Size** S–M · **Depends on** BI-011 · **Status: partial (minimal)**
- **Acceptance** query count and time budgets for dependency resolution, batch calculation and portfolio aggregation, recorded before any optimisation.
- **Evidence** `tests/performance/test_query_counts.py` (2 tests, `performance` marker, excluded from the fast suite). An SPX v2 backtest of 18 bars takes ~15 min.

### BI-020 — Harden IBKR connection lifecycle
- **Priority** P3 · **Size** M · **Depends on** BI-005 · **Status: partial**
- **Acceptance** disconnect / reconnect, timeouts, pacing, contract qualification, error handling (error 162 surfaced with the request), data freshness, and a finished run always releasing its client id — each tested.
- **Evidence** `test_resilience.py::TestIBKRConnection` (bounded retries, disconnected broker refuses orders), `tests/integration/test_ibkr_live_readonly.py` (7, opt-in). Observed 2026-10-20: a completed backtest process kept its TWS connection open, so the next run failed with "TWS is not connected"; IBKR returned no option history before ~8 weeks back (error 162) — fetch errors are not reported with the IBKR message.

### BI-021 — Implement order-state and reconciliation tests
- **Priority** P3 · **Size** M · **Depends on** BI-020 · **Status: partial**
- **Acceptance** submitted → acknowledged → partially filled → filled / cancelled / rejected transitions and duplicate-submission protection tested on one order-status model.
- **Evidence** `tests/misbuffet/test_live_order_path.py` (36, 1 expected failure), `test_reconciler_lifecycle.py` (6), `test_order_safety.py` (25); two order-status enums (`src/domain/entities/finance/back_testing/enums.py`, `src/domain/entities/finance/order/order.py`).

### BI-022 — Add pre-trade risk controls
- **Priority** P3 · **Size** M · **Depends on** BI-021 · **Status: missing**
- **Acceptance** one shared gate before paper-order submission: position limit, order size, exposure, available cash, stale market data — each rejection tested and logged.
- **Evidence** only project-specific `check_position_limits` (SPX v2 `strategy/risk_manager.py:57`) and the reconciler's mismatch block (`position_reconciler.py:137`); no shared gate in the order path.

### BI-023 — Complete read-only operational dashboard
- **Priority** P3 · **Size** S–M · **Depends on** BI-020 · **Status: partial (mostly complete)**
- **Acceptance** service health, IBKR connectivity, data freshness, job failures and account summary shown; read-only enforced by tests (no mutating routes, read-only IBKR client, read-only DB login).
- **Evidence** `docs/MONITORING.md`; `tests/monitoring/` (51 tests: read-only API, network exposure, IBKR monitor, staleness, jobs); `ReadOnlyIBKRClient` blocks order calls; compose service `monitor` with `monitor_reader` (db_datareader).

### BI-024 — Add integration and recovery tests
- **Priority** P3 · **Size** L · **Depends on** BI-006, BI-020, BI-002 · **Status: partial (minimal)**
- **Acceptance** database outage, broker disconnection, failed job, restart recovery and reconciliation exercised against isolated test services (`base_infra_test`, paper / mocked broker).
- **Evidence** `tests/integration/test_docker_services.py` (2), `test_resilience.py::TestRestart`; no outage-injection tests.

### BI-025 — Prefer MIDPOINT over TRADES for historical bars *(added 2026-10-20, user request)*
- **Priority** P1 · **Size** S · **Depends on** BI-013 · **Status: partial** · **GitHub** #578
- **Scope** when IBKR MIDPOINT history works for an instrument, request it first and fall back to TRADES, because TRADES bars exist only when a trade happened (less reliable).
- **Acceptance** `what_to_show.resolve_what_to_show` returns MIDPOINT first for price bars of every instrument type where IBKR serves it (volume stays TRADES); fallback to TRADES when MIDPOINT is empty; which type was used is recorded with the value; tests for share, option, future and index.
- **Evidence** done for options on 2026-10-20 (`src/infrastructure/repositories/ibkr_repo/factor/what_to_show.py`, TRADES→MIDPOINT retry for options in `ibkr_factor_value_repository.py`); shares / futures / indices still TRADES.

### BI-026 — Re-run safety: never reuse stale derived values in backtests *(added from the audit)*
- **Priority** P1 · **Size** M · **Depends on** BI-014 · **Status: missing** · **GitHub** #579
- **Acceptance** a backtest re-run over a window produces the same values as a run on an empty derived-value store; a test seeds stale derived values and checks they are not used.
- **Evidence** see BI-012 observation; pinned xfail `test_value_propagation.py:237`.

### BI-027 — Persist option history going forward *(added from the audit)*
- **Priority** P2 · **Size** S · **Depends on** BI-025 · **Status: missing**
- **Acceptance** a scheduled read-only job stores daily MIDPOINT bars for the universe's options so backtests do not depend on IBKR's limited option-history window; gaps reported.
- **Evidence** 2026-10-20: IBKR returned error 162 ("HMDS query returned no data") for `SPY 281215C00775000` before 24 Aug 2026 in MIDPOINT, TRADES and BID_ASK; 11–21 Aug cannot be re-fetched.
