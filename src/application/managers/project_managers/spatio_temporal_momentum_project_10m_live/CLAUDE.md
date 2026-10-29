# CLAUDE.md – spatio_temporal_momentum_project_10m_live

## The 10m STM strategy, deployed live (paper account by default) — 2026-10-29

A copy of `spatio_temporal_momentum_project_10m` wired to IBKR through `build_live_stack` (P.06.01). Strategy,
universe (26 US banks), features, model, windows and retraining are **identical** (a test checks it); backtest and
research stay in `spatio_temporal_momentum_project_10m`. This project only trades.

```python
from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.project_manager import (
    SpatioTemporalMomentum10mLiveProjectManager,
)
m = SpatioTemporalMomentum10mLiveProjectManager()
m.check()   # connect, resume the book, live stack, start-up recovery — NO order, no data import, no model
m.run()     # one session: next 10-minute decision .. the session's last (15:50); Ctrl+C / m.stop() end it early
```

Follow it: `/stm/?project=10m_live` (decisions, timings) and `/monitor/trading` (orders, executions, controls,
discrepancies). Operating it day to day: **RUNBOOK.md**. Kill switch / reduce-only / resolve a discrepancy:
`python -m ...spatio_temporal_momentum_project_10m_live.ops <command>` (database only; the running session reads
the controls before every order).

## How a session runs

1. `session_window` (NYSE calendar, exchange time): today's session if its last decision is ahead, else the next
   one; first decision = the next 10-minute step, last = 15:50 (or close − 10 min on early closes). The history
   start is rolling: `history_calendar_days` (28) before the session.
2. `LiveRunner.run_live` launches the Misbuffet engine with `live_mode=True`, `brokerage=<InteractiveBrokersBroker>`
   (order connection, client id 31; the data connection is the repository factory's, client 1) and
   `live_clock=LiveClock(...)`.
3. `Algorithm.initialize` refuses to run outside live mode, resumes the book
   `Spatio_Temporal_Momentum_10m_Live_Portfolio` (live: `_create_or_get`, never reset), then calls the runner's
   `build_stack`: `build_live_stack` (ledger, reconciler, start-up recovery, pre-trade gate). **A blocked start-up
   recovery stops the run** (resolve the discrepancies, start again). Only then the cycle is built (entities,
   history preload, universe, factors).
4. The engine loop asks the `LiveClock` before each step: it waits until bar close + `bar_close_grace_seconds`
   (20 s), skips a step reached more than `max_step_lag_seconds` (300 s) late (e.g. while the daily retraining
   runs), stops on request.
5. `on_data` → `STMTradingCycle.step(t)` (new bars imported by `BarHistoryUpdater`, reads through the frontier,
   retrain when due, scores, vol-scaled weights) → `set_holdings`: ledger drain, recovery, reconciliation, then market
   orders through the gate.
6. At the end (last decision, stop, Ctrl+C, failure) `LiveStack.shutdown` applies the broker events and cancels
   working orders (`cancel_working_on_shutdown`); positions stay, the next session resumes them.

## Live configuration (`config.LIVE`)

| key | default | note |
|---|---|---|
| account | `DUR314497` (env `STM_LIVE_ACCOUNT`) | paper; a live account also needs `IBKR_ACCOUNT_MODE=live`, `IBKR_ALLOW_LIVE=yes` |
| paper_bar_prices | True | paper login has no US-equity quotes (B2); **must be False for a live account** (refused) |
| limits | order ≤ 1 000 sh / 5 000 USD, position ≤ 2 000 sh, account gross ≤ 31 250 USD, quote age ≤ 1 800 s | quote age: 60 s with real-time quotes |
| TRADING_CAPITAL | 25 000 USD | cash of the book; weights are sized on it, not on the IBKR account |
| max_orders | 60 per 60 s | one rebalance may send an order per bank + liquidations |

## Kept apart from the 10m backtest

Portfolio `Spatio_Temporal_Momentum_10m_Live_Portfolio`, signal factor
`spatio_temporal_momentum_signal_10m_banks_live`, feature / ML prefixes `stm10mlive_`, universe
`stm_us_banks_10m_live`, results `results/spatio_temporal_momentum_10m_live/`, models
`weights/spatio_temporal_momentum_10m_live/`.

## Data during a session (paper smoke run 2026-10-29)

* The preload imports the history but registers it as complete (`preloaded_coverage`) only up to the last bar
  **closed** at that moment; `BarHistoryUpdater.mark_imported(through=that bar)`. Registering up to the session's
  end (the backtest rule) made every decision of the first smoke run see the 12:20 bar: the resolver treated the
  bars of the session as non-existent and never asked IBKR.
* Tickers without an IBKR contract get no entity: the cycle excludes them, and the engine slice / updater do not
  ask for them (each request cost a 15 s timeout). 2026-10-29: BK is listed by IBKR as **BNY** (universe changed,
  owner's decision, here and in the 10m project); CMA has no contract and stays excluded.
* `Algorithm.before_step(t)` (engine hook, live clock only, before the slice): imports the bar that just closed
  (one "1 D" request per ticker) and extends `preloaded_coverage` to *t*, so the slice, the cycle, the valuation and
  the order pricing read locally. Without it one decision made 88 IBKR requests and took 11 minutes.
* Pre-trade gate prices (paper, `bar_prices=algorithm.bar_price`): the close of the bar the step imported, dated at
  its close — the price set_holdings sized with. `LastTradeBarPriceProvider` asked IBKR for 5-minute bars per order
  and per position (36 requests a step) and hit IBKR pacing (60 historical requests / 10 min). A ticker whose new
  bar was not imported has no usable price: the gate refuses its order.
* Shortable check (`live.shortable_check`, `data/shortable_inventory.py`): IBKR's public short-stock file
  (ftp2.interactivebrokers.com/usa.txt, user shortstock) is read once a day; short targets of names with no shares
  to lend are cut to 0 before set_holdings. File unreadable and none loaded -> not restricted (IBKR rejects what it
  cannot lend). 2026-10-29: all 24 tradable banks shortable, 0.85 M to >10 M shares, fee 0.25-0.41 %/yr.
* The first decision of the day retrains (~2.5 min on CPU): its orders leave a few minutes after the decision
  time. Later steps take ~10-40 s.

* Lost connections (P.04.07): the runner's `LiveConnectionGuard` runs first in `before_step`: data connection
  reconnected in place; order connection reconnected and the live stack rebuilt on the new client
  (`build_stack(at_start=False)`: a blocked recovery then refuses orders instead of stopping the session).

## Rules

* Times are naive **New York** times everywhere (engine clock, stored bars, `BarHistoryUpdater.exchange_now`), not
  the machine's local time.
* Never run this project as a backtest (`LiveRunner.run_backtest` and `Algorithm.initialize` refuse).
* Executions not made by this strategy today (manual trades, other tests) block start-up recovery as
  EXTERNAL_EXECUTION: resolve them with a reason (`StartupRecovery.resolve` / `Discrepancy.resolve`).

Tests: `tests/spatio_temporal_momentum/test_stm_10m_live.py`, `tests/misbuffet/test_live_clock.py`.
