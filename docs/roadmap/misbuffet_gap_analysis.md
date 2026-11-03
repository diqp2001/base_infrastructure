# Misbuffet — gap analysis (2026-11-03)

Scope: the areas the live-readiness work (`LIVE_TRADING_READINESS.txt`, P.01–P.07) had not audited:
backtesting and research, the engine beyond one live session, historical market data, accounting, and
operations. The live order path (order lifecycle, partial fills, cancellations, duplicates, reconciliation, crash
recovery, external orders, pre-trade risk, kill switch, streaming quotes) was audited and verified there and is only
summarised here. The remaining work is tracked as phase **P.08** of `LIVE_TRADING_READINESS.txt`; this file is the
evidence behind it.

Method: code read along the actual execution paths (graph built from commit `4a5a10e0`, the same code as `main`
`bc19d77f`), then the cited tests run. 75 tests run on 2026-11-03, all passing:

- `tests/misbuffet/test_backtest_engine.py`
- `test_history_pacing.py`
- `test_history_diagnostics.py`
- `test_streaming_market_data.py`
- `tests/spatio_temporal_momentum/test_stm_lookahead.py`
- `test_stm_data_coverage.py`
- `test_stm_10m_live.py`

Full suite on 2026-11-02: 2078 passed, 126 skipped, 6 expected failures. The six expected failures are SPX
strategy and factor issues, not engine defects.

Statuses:
- **VERIFIED**: code and passing tests.
- **PARTIAL**: works but lacks something important.
- **MISSING**: nothing meaningful found.
- **UNVERIFIED**: not enough evidence to judge.

Kinds:
- **missing**: missing functionality.
- **reliability**: a reliability improvement.
- **refactor**: a refactoring opportunity.
- **optional**: an optional enhancement.

**Progress since the audit:** see P.08 in `LIVE_TRADING_READINESS.txt`. On 2026-11-03:
- GA-A5 (split guard) is done.
- GA-F1 (ntfy alerts), GA-F2 (scheduled backups and restore drill) and GA-E1 (bid/ask fills and commission) are
  implemented and waiting on owner steps.

The statuses below are those of the audit.

## Summary

| ID | Capability | Status | Kind | Priority |
|---|---|---|---|---|
| GA-F1 | Alert delivery (push) | MISSING | missing | HIGH |
| GA-F2 | Scheduled database backup and restore drill | PARTIAL | reliability | HIGH |
| GA-A5 | Corporate actions in stored price series (splits) | MISSING | missing | HIGH |
| GA-E1 | Costs in the engine backtest (commission, spread, slippage) | PARTIAL | missing | HIGH |
| GA-D2 | One live session at a time (single-instance guard) | PARTIAL | reliability | MEDIUM |
| GA-D3 | Daily session start and supervision | PARTIAL | reliability | MEDIUM |
| GA-A3 | Recovery of missing historical bars | PARTIAL | reliability | MEDIUM |
| GA-A4 | Validation of imported bars | MISSING | reliability | MEDIUM |
| GA-C1 | Realized / unrealized P&L per position | MISSING | missing | MEDIUM |
| GA-C3 | Multi-currency books | PARTIAL | missing | MEDIUM (HIGH before a non-USD instrument) |
| GA-C4 | Derivatives lifecycle (expiry, exercise, assignment) | MISSING | missing | MEDIUM (HIGH before live options) |
| GA-E5 | Run reproducibility record | PARTIAL | reliability | MEDIUM |
| GA-E6 | Research-to-production decision parity | PARTIAL | reliability | MEDIUM |
| GA-F6 | Deployment: which code runs live | PARTIAL | reliability | MEDIUM |
| GA-C2 | Fixed mock price in position reporting | PARTIAL | reliability | LOW |
| GA-D1 | Several strategies on one account | MISSING (by design) | missing | LOW (owner decision) |
| GA-E4 | Survivorship bias | MISSING (documented) | missing | LOW |
| GA-E2 | Two unused backtest fill models beside the real one | PARTIAL | refactor | LOW |
| GA-F3 | Schema migrations | PARTIAL | refactor | LOW |
| GA-D4 | Resource management (SQL Server memory) | UNVERIFIED | reliability | LOW |
| GA-A1 | Historical retrieval and IBKR pacing | VERIFIED | — | — |
| GA-A2 | Historical → live handoff (STM live) | VERIFIED | — | — |
| GA-E3 | Look-ahead / point-in-time | VERIFIED | — | — |
| GA-F4 | Secrets and account-mode guards | VERIFIED | — | — |
| GA-F5 | Automated tests and CI | VERIFIED | — | — |

**Already verified in `LIVE_TRADING_READINESS.txt`:**
- streaming, entitlements and stale data (P.02);
- the order lifecycle, partial fills, cancellations and duplicates (P.03);
- reconciliation, crash recovery and external orders (P.04);
- risk limits and the kill switch (P.05);
- paper operation, the monitoring page and the runbook (P.06).

**Still open there:**
- P.03.04: changing a working order in place (cancel and replace is the workaround).
- P.06.13: the first paper cash comparison, due 2026-11-04.
- P.07.08: the owner's figures for a live pilot.

## A. Market data (historical)

**GA-A1 Historical retrieval and request limits: VERIFIED**
- Evidence:
  - `brokers/ibkr/history_pacing.py` waits before sending: at most 60 requests in 10 minutes, and no identical
    request within 15 s.
  - `brokers/ibkr/history_result.py` classifies failures as permission, pacing, no_data, transient or timeout. Only
    transient, pacing and timeout are retried.
  - `MarketDataHistoryService` groups requests by `whatToShow` (`data/market_data_history_service.py:645`).
  - Tests: `tests/misbuffet/test_history_pacing.py`, `test_history_diagnostics.py`.
- Nothing open.

**GA-A2 Historical → live handoff: VERIFIED for STM live, not generic**
- Evidence:
  - The preload registers coverage only up to the last closed bar.
  - `before_step` imports the bar that just closed, with one `1 D` request per ticker, and extends the coverage
    (`spatio_temporal_momentum_project_10m_live/backtesting/base_project_algorithm.py:102`).
  - The gate prices orders on real-time quotes; B2 was resolved on 2026-11-03.
  - Tests: `test_stm_10m_live.py::test_live_preload_registers_coverage_only_up_to_the_last_closed_bar`,
    `::test_before_step_imports_the_new_bar_and_extends_the_coverage`.
- Gap: the handoff lives in the STM live project, not in the engine. A second live strategy would copy it.
- Priority: LOW.

**GA-A3 Missing-data recovery: PARTIAL (reliability, MEDIUM)**
- Already implemented:
  - The coverage report counts missing bars, gaps, off-grid bars and absent assets
    (`test_stm_data_coverage.py::test_coverage_counts_missing_bars_gaps_off_grid_and_absent_assets`).
  - In live, each step re-requests the whole current day, so a bar missed during a disconnection is refilled at the
    next step.
- What's missing:
  - `before_step` calls `preloaded_coverage.extend(step_time)` even when some tickers' imports failed
    (`base_project_algorithm.py:113-117`). The series is then treated as complete through that step.
  - Gaps found in earlier days are reported but never re-requested automatically.
- Impact: a missing bar inside "complete" coverage silently changes features and returns until someone reads the
  coverage report.
- Next action: extend the coverage only for tickers whose import succeeded. At preload, re-request the days the
  coverage report flags as gapped.
- Dependencies: none.

**GA-A4 Validation of imported bars: MISSING (reliability, MEDIUM)**
- Evidence: there is no sanity check on the import path, `EntityService.create_or_get_batch_ibkr`
  (`application/services/data/entities/entity_service.py:317`). Searched `services/data`, `misbuffet/data` and
  `brokers/ibkr` for OHLC, duplicate and outlier validation; the only outlier code is winsorisation of factors
  (`factor_normalizer.py:594`).
- Impact: a bad bar (zero, high < low, a fat-finger print) enters features and the gate's paper-bar prices
  unchecked.
- Next action: validate each bar at import: positive prices, low ≤ open/close ≤ high, volume ≥ 0. Store a rejected
  bar as an anomaly, never as data. A cross-sectional return outlier guard goes with GA-A5.

**GA-A5 Corporate actions in stored price series: MISSING (HIGH)**
- Already implemented:
  - `misbuffet/data/data_normalization.py` defines `CorporateAction` and split and dividend adjustment, but nothing
    imports it. The only references to "normalization" elsewhere are the `DataNormalizationMode` enums.
  - IBKR serves TRADES history split-adjusted as of the request date.
- What's missing:
  - Bars are stored with get-or-create: an existing value is kept, never overwritten
    (`entity_service.py:317-376`).
  - After a split, the stored history (old scale) and newly imported bars (new scale) are mixed in one series.
  - Dividends are not credited in engine backtests. In live they reach the books as financing (P.06.13).
- Impact: a split in a universe name shows up as a −50 % (2:1) or similar one-bar "return". STM live would read it
  as a real move, retrain on it and trade it.
- Next action: at each preload, compare the stored overlap with freshly requested IBKR bars. A constant ratio
  means a split: re-import that ticker's series, or exclude the ticker from decisions until it has been re-imported.
- Dependencies: none.

## B. Order execution (audited in the readiness tracker)

| Area | Status | Where |
|---|---|---|
| Submission, lifecycle, acknowledgment, partial fills, cancels, duplicates, executions | VERIFIED on paper | P.03 and P.06 in the tracker |
| Reconciliation, crash recovery, external orders | VERIFIED on paper | P.04 and P.06 in the tracker |
| Order modification | PARTIAL: cancel and resend only | P.03.04 |

The orderId per-client matching bug (found on 2026-11-03) is fixed, with a regression test in
`test_startup_recovery.py`.

## C. Portfolio and accounting

**GA-C1 Realized / unrealized P&L per position: MISSING (MEDIUM)**
- Evidence:
  - `positions` stores quantity and type only (`infrastructure/models/finance/position.py:19`).
  - `PositionRepository.get_portfolio_value` and `get_portfolio_unrealized_pnl` return `Decimal('0')` (stubs,
    `local_repo/finance/position_repository.py:269-273`).
  - `PositionService.calculate_unrealized_pnl` needs a cost basis from its caller and has no callers.
- Already implemented: portfolio-level value through `PortfolioService.calculate_value`, called from
  `UnifiedPortfolioManager.get_portfolio_value`; performance metrics come from the value series.
- Impact: no per-name attribution and no realized P&L. The monitor shows IBKR's P&L, not the books'.
- Next action: derive average cost and realized P&L from the stored fills (`transactions` and `orders` hold price
  and quantity), with no schema change. Expose both on the Trading page.

**GA-C2 Fixed mock price in position reporting: PARTIAL (reliability, LOW)**
- Evidence: `UnifiedPortfolioManager._calculate_holding_market_value` values every holding at a fixed 100
  (`algorithm/unified_portfolio_manager.py:815-821`). It feeds `get_active_positions()['market_value']`, which
  `QCAlgorithm.get_active_positions` and `get_unified_state` expose (`algorithm/base.py:1169`, `:1199`).
- Not affected: valuation and sizing, which go through `PortfolioService`.
- Next action: value through the same price chain as `set_holdings`, or report "no price" instead of 100. This
  follows the project rule against hard-coded values.

**GA-C3 Multi-currency: PARTIAL (MEDIUM, HIGH before a non-USD instrument)**
- Already implemented (2026-11-03): account values are converted from the base currency (CAD on paper) with IBKR's
  ledger rate, and the cash check reads the USD ledger.
- What's missing:
  - One cash position per book. `TradeManager` writes `currency_id=1` on its transactions
    (`algorithm/trade_manager.py:437`, `:627`).
  - Non-USD commissions are reported, not booked (`algorithm/order_ledger.py:380`).
- Impact: a non-USD instrument would book foreign notional into the USD cash.
- Next action: until multi-currency books exist, the gate should refuse any instrument whose contract currency
  differs from the book currency. That's a cheap, safe guard.

**GA-C4 Derivatives lifecycle: MISSING (MEDIUM, HIGH before live options)**
- Evidence:
  - `QCAlgorithm.on_assignment` is a stub that nothing calls (`algorithm/base.py:168`).
  - Nothing books expiry, exercise or assignment.
  - The SPX projects avoid expiry with a strategy rule (`min_time_to_expiry: 7`,
    `market_making_SPX_call_spread_project_v2/config.py:106`).
- Impact: an option held through expiry stays in the books. An assignment leaves an unexplained stock position,
  which start-up recovery blocks on, so it fails safe but needs a manual fix.
- Next action: before any live options strategy, book expiry and assignment from IBKR's executions and position
  changes.

Dividends and financing in live: done through P.06.13. Dividends in backtests: see GA-A5 and GA-E1.

## D. Engine orchestration

**GA-D1 Several strategies on one account: MISSING by design (LOW, owner decision)**
- Evidence:
  - The cash check assumes a dedicated account (owner decision P.04.04).
  - `PositionReconciler` compares the strategy's quantity with the broker's for each managed ticker, so two
    strategies on one ticker would mismatch.
  - Exposure limits are account-wide.
  - Trading controls already have a strategy scope.
- Next action: decide between one sub-account per strategy and allocation inside one account. Nothing to build
  before that decision.

**GA-D2 Single-instance guard: PARTIAL (reliability, MEDIUM)**
- Evidence: no lock. The only protection is the fixed TWS client id 31 (`config.py` `LIVE['client_id']`), since TWS
  refuses a second connection with the same id, plus the runbook's "one process per day".
- Impact: a second session started with another client id would trade the same book twice.
- Next action: take a database application lock (SQL Server `sp_getapplock`) or an exclusive lock file per strategy
  at `run()` and `check()`. Refuse to start when it's held.

**GA-D3 Scheduling and supervision: PARTIAL (MEDIUM)**
- Already implemented:
  - `LiveClock` with the NYSE calendar and session window.
  - Late steps are skipped.
  - Tests: `test_stm_10m_live.py::test_session_window*`, `::test_the_nyse_calendar_is_read_in_exchange_time`.
- What's missing:
  - The daily start is manual (RUNBOOK §2), and nothing restarts a crashed session.
  - Algorithm-level scheduled events (`algorithm/scheduling.py`) are defined but the engine never runs them; the
    engine steps a fixed interval.
- Next action: owner decision on automation (Windows Task Scheduler or a compose service), then a start script that
  takes the GA-D2 lock and alerts through GA-F1 on failure.

**GA-D4 Resource management: UNVERIFIED (LOW)**
- Known: backtests have frozen when Windows paged out SQL Server (error 701, event 17890).
- Not checked: whether SQL Server's maximum memory is capped on the host that will run live.
- Already in place: per-step timings (`timings.csv`, `[timing]` log line).

**Verified in the tracker:** recovery and restart, shutdown, observability (P.04, P.06).

## E. Backtesting and research

**GA-E1 Costs in the engine backtest: PARTIAL (HIGH)**
- Evidence:
  - In a backtest, `QCAlgorithm._submit_order` only records the order (`algorithm/base.py:425`).
  - `TradeManager.execute_trade` then books the fill at the submission price (`algorithm/trade_manager.py:7`,
    `:108`). That price is the bar close known at the decision (`unified_portfolio_manager.py:1313-1322`).
  - No commission, spread, slippage, volume limit or partial fill is applied.
- Already implemented:
  - Research evaluation does count costs: `stm_backtest` reports returns net of turnover costs at several cost
    levels (`factor/spatio_temporal_momentum/stm_backtest.py:36-48`).
- Impact:
  - The engine backtest, which is the one comparable to the live book, is cost-free.
  - Live costs include IBKR commissions (about 0.005 USD per share, 1 USD minimum, seen on paper as 0.50–2.00 per
    fill) and half the spread on market orders.
  - Live will under-perform the backtest systematically.
- Next action: an explicit cost model on the backtest booking path in `TradeManager`:
  - commission per share with a minimum;
  - a half-spread or slippage in basis points.
  - Both come from the project config, and a missing config fails rather than defaulting.
  - Book the commission like live (`book_commission`), so books from backtest and live are comparable.
- Dependencies: none.

**GA-E2 Unused fill models: PARTIAL (refactor, LOW)**
- `BacktestingTransactionHandler` has 0.1 % slippage and 0.01 USD per share (`engine/transaction_handlers.py:393-394`,
  tested in `test_backtest_engine.py`).
- The engine's fallback `connected_market_order` charges 0.01 USD per share (`engine/misbuffet_engine.py:288`).
- Neither is on the path of `QCAlgorithm`-based strategies. Fold them into GA-E1's model, or remove them once
  GA-E1 exists.

**GA-E3 Look-ahead / point-in-time: VERIFIED**
- Raw IBKR bars are stamped at their start and become usable only once closed. The history frontier is set at each
  step.
- Tests: `tests/spatio_temporal_momentum/test_stm_lookahead.py`, `tests/component/factor_context/*`.

**GA-E4 Survivorship bias: MISSING, documented (LOW)**
- `bank_universe.py` states it: "Today's list applied to the whole history (survivorship bias, as for every universe
  in this code base)." The `universes` table has no membership dates.
- Next action: dated membership when a research question needs it. It doesn't affect live safety.

**GA-E5 Reproducibility: PARTIAL (MEDIUM)**
- Already implemented:
  - Seeds in config (`spatio_temporal_momentum_project_10m/config.py:155`, `:179`).
  - Model artifacts with JSON metadata (`model_artifacts` / `model_trainings`, `stm_artifact_store.py`), including
    the validation end date.
- What's missing: a backtest record holds only name, model and creation date
  (`infrastructure/models/backtest/backtest.py`). It has no config snapshot, code version (git commit) or data
  window, so a result cannot be traced back to what produced it.
- Next action: write a run manifest (config, `git rev-parse HEAD`, dirty flag, data window, artifact ids) into
  `results_dir` with every backtest and live session.

**GA-E6 Research-to-production parity: PARTIAL (MEDIUM)**
- Already implemented: the live strategy is a copy of the 10-minute research project (project policy), and
  `test_stm_10m_live.py::test_same_research_parameters_as_the_10m_backtest` checks that the parameters match.
- What's missing: no check that the same data gives the same targets in research and live. The copies can drift in
  code.
- Next action: a deterministic test that runs both cycles on a fixed SQLite fixture and compares the decided
  weights.

## F. Production operations

**GA-F1 Alert delivery: MISSING (HIGH for a live pilot)**
- Evidence: alerts are computed (`application/services/monitoring/service.py:61` `trading_alerts`) and shown on the
  dashboard only. The tracker already says "No push notification (dashboard only)" under P.06.
- Impact: during a session, these go unnoticed unless someone is watching the page:
  - a blocking discrepancy;
  - a kill;
  - an UNKNOWN submission;
  - a crashed process.
- Next action: owner choice of channel (e-mail, ntfy, Pushover, Telegram). Then one sender, called on critical
  alerts and on session start, stop and failure, with de-duplication.
- Dependencies: owner decision.

**GA-F2 Database backup and recovery: PARTIAL (HIGH before live)**
- Already implemented: manual COPY_ONLY backups before every schema change, with checksum and RESTORE VERIFYONLY
  (2026-10-29, 2026-11-02).
- What's missing: no scheduled backup, no restore drill and no stated recovery point. The books in `base_infra`
  are the strategy's source of truth: positions, cash, the order ledger.
- Next action: a nightly full backup and a scheduled log or differential backup (owner chooses the schedule and
  retention), plus one documented restore onto `base_infra_test`.

**GA-F3 Schema migrations: PARTIAL (refactor, LOW)**
- New tables come from `create_all` at every start, and new columns from hand-written statements in
  `BaseFactory._migrate_schema` (`infrastructure/database/base_factory.py:41`).
- `alembic==1.14.0` is in `requirements.txt` but has no migrations. Workable at the current pace; revisit if
  changes get frequent.

**GA-F4 Secrets and account guards: VERIFIED**
- `.env`, `.env.windows` and `secrets/` are git-ignored, with `.env.example` as a template.
- Database credentials come from the environment (`infrastructure/database/settings.py`).
- Orders to an account of the wrong kind are refused (`brokers/ibkr/ibkr_settings.py::verify_connected_accounts`,
  `test_live_stack.py::test_the_stack_refuses_a_live_account_in_paper_mode_and_delayed_prices_on_live`).
- Optional: secret scanning in CI.

**GA-F5 Automated tests and CI: VERIFIED**
- Three stages in `.github/workflows/python-app.yml`:
  1. architecture and unit tests on every push;
  2. component and contract tests on PRs;
  3. SQL Server integration tests nightly.
- IBKR is never called from CI. There are lint and import-cycle baselines.

**GA-F6 Deployment: PARTIAL (MEDIUM)**
- Already implemented: a Docker stack (app, IBKR gateway, SQL Server, monitor) is documented in `docker/` and
  `docs/MONITORING.md`.
- What's missing: the live session runs by hand from a Windows working tree, so nothing records which commit
  traded.
- Next action: run live only from a clean, tagged commit. The GA-E5 manifest records it, and the start script
  refuses a dirty tree.

## Recommended next task

For a live pilot, the most important gap is **GA-F1, alert delivery**. Every other safety mechanism (blocking
recovery, kill switch, UNKNOWN orders) relies on a human noticing, and today that requires watching a page. It needs
one owner decision: the channel.

If that decision is pending, the next task needing no decision is **GA-A5, split detection**. A split in one of
the 24 banks would feed a false −50 % return into a live decision, and the fix can reuse the existing preload
and coverage code.

**GA-E1, backtest costs**, should follow before any backtest is used to size the live pilot.
