# RUNBOOK — STM 10m live deployment (STM_10M_BANKS)

For the operator running the strategy day to day. Times are New York (ET). Default account: paper `DUR314497`.
`ops` below means:

```
python -m src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.ops
```

`ops` writes to the database only, never to IBKR. A running session reads the trading controls before every order,
so `ops kill` / `ops reduce-only` take effect from the next order without restarting anything.

## 1. Before the open (by 09:20)

1. **TWS** logged into the paper account, API port 7497, API **not** read-only, "Bypass Order Precautions for API
   Orders" **on** (otherwise TWS holds API orders silently behind a dialog). TWS auto-restart time **outside**
   09:00–16:30 (the session keeps one connection all day).
2. **SQL Server** `base_infra` up.
3. **Dashboard**: `python -m src.interfaces.flask.app`, then open `http://127.0.0.1:5000/monitor/trading` (orders,
   executions, controls, alerts) and `http://127.0.0.1:5000/stm/?project=10m_live` (decisions, timings).
4. `ops status` must show `trading: ENABLED`, no BLOCKING discrepancy, no open order.
5. Optional, no orders: `SpatioTemporalMomentum10mLiveProjectManager().check()` — connects, resumes the book, runs
   start-up recovery.

## 2. Start the session (09:20 – 09:30)

```
python -c "from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.project_manager import SpatioTemporalMomentum10mLiveProjectManager as M; M().run()"
```

* It refuses to start when start-up recovery is blocked: see §4.
* About 5 minutes of history import before the first decision; the first decision (09:40) retrains the model
  (~2.5 min CPU), so its orders leave around 09:43. Later decisions take 10–15 s.
* Started later in the day, it begins at the next 10-minute step. Started after 15:50, it waits for the next session.
* One process per day. It ends by itself after the 15:50 decision.

## 3. During the session

Every 10 minutes the dashboard log shows a `[timing]` line. Normal: `total` 10–15 s, `ibkr 0 req`.

| Alert / symptom | Meaning | Action |
|---|---|---|
| critical `control … DISABLED` | someone killed trading | intended? else `ops unkill` / `ops enable "<reason>"` |
| critical `discrepancy … blocking` | books and IBKR disagree; no order until resolved | §4 |
| critical `order … submission UNKNOWN / INTENT` | an order may or may not have reached IBKR | look in TWS (Orders / Trades). Never re-send by hand; the next recovery matches it |
| warning `no broker event for N min` | order working without news | check TWS; a market order should fill in seconds |
| warning `execution(s) stored but not booked` | a fill no strategy order explains (manual trade, other client) | §4 |
| log `orders not placed for [...]` | the gate refused them (reasons in the log: price age, limits, account values) | read the reason; repeated -> `ops reduce-only` and investigate |
| log `step … skipped, reached Ns late` | a decision came more than 5 min late | normal once after the retrain; repeated -> machine / IBKR too slow |
| `[timing]` `ibkr` > 0 req or total > 60 s | data requests inside the step | IBKR pacing; report it |

## 4. Discrepancies

`ops status` lists them with their id. Check in TWS what really happened, then:

```
ops resolve <id> "<what you checked and did>"
```

The running session re-checks IBKR before its next order. Typical cases:

* `external_execution`: a trade not made by this strategy (manual trade in TWS, a test). Today's executions are
  re-read at every start, so resolve them before starting.
* `position_mismatch`: IBKR position ≠ book. **The book is not corrected by `ops`**: a manual trade that changes a
  strategy position leaves the book wrong until it is corrected in the database. Avoid manual trades in the
  strategy's 24 names.
* `order_closed_on_recovery`: an order the book thought working was no longer at IBKR (e.g. cancelled at shutdown
  before IBKR answered); informational.

## 5. Stopping

* **Normal**: the session stops after 15:50. Positions are **kept overnight** (borrow fees on shorts, dividends on
  ex-dates).
* **Early**: Ctrl+C in the session window. Shutdown applies pending broker events and cancels working orders.
* **Emergency, no new risk**: `ops kill "<reason>"` (every order refused), or `ops reduce-only "<reason>"` (only
  reductions allowed). Both apply to the next order of the running session.
* **Emergency, flatten everything**: there is no `ops` command for it. `ops kill`, stop the session, then flatten in
  TWS. The book will then disagree with IBKR (§4 `position_mismatch`): the book must be corrected before the next
  start.

## 6. After a crash or a lost connection

Start again (§2). Start-up recovery reads IBKR's open orders, today's executions and positions, books missed fills
once, and blocks on anything it cannot explain. A connection lost **during** a session has not been tested with this
runner (readiness P.04.07): stop the session and start it again rather than letting it continue.

## 7. Reference

* Config: `config.py` `LIVE` (account, limits, quote age, capital 25 000 USD) — see `CLAUDE.md`.
* Live account: only with `IBKR_ACCOUNT_MODE=live`, `IBKR_ALLOW_LIVE=yes`, `STM_LIVE_ACCOUNT=<account>`,
  `paper_bar_prices=False` and real-time US-equity data for the API. **Not ready**: `LIVE_TRADING_READINESS.txt` P.07.
