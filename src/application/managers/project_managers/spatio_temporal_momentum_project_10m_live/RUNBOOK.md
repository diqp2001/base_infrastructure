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
4. `ops status` must show `trading: ENABLED`, no BLOCKING discrepancy, no open order, and no `BACKUP ALERT`
   (backups: `docs/operations/BACKUPS.md`).
5. **Alerts on the phone** (P.08.01): the ntfy app subscribed to the topic `NTFY_TOPIC` of `.env.windows`. A session
   pushes its start, end and crash, and every new critical alert (trading disabled, blocking discrepancy, order
   submission UNKNOWN / INTENT, split guard, stale backup) once. Without `NTFY_TOPIC` the session logs a warning and
   alerts stay on the dashboard. Check the phone setup with `ops notify-test`.
6. Optional, no orders: `SpatioTemporalMomentum10mLiveProjectManager().check()` — connects, resumes the book, runs
   start-up recovery.

## 2. Start the session (09:20 – 09:30)

**Automatic (P.08.06, Docker):** the compose service `trader` starts the session by itself at 09:20 ET on every NYSE
trading day (holidays and weekends skipped, early closes handled), restarts a crashed session at most 3 times a day
(60 s apart, never in the last 10 minutes) and pushes every crash, then "session down for the day", to the phone.

```
docker compose --profile trading up -d trader     # once; it then runs every trading day (restart: unless-stopped)
docker compose logs -f trader                     # the session's log
docker compose stop trader                        # ends the session cleanly before its next step, no restart
```

* The `trading` profile keeps it out of a plain `docker compose up`: it sends orders.
* IBKR: its own Gateway `ibkr-paper` (same profile, started with it), logged into the PAPER username; the `ibkr`
  service keeps its own login. Before the first start, in the WSL clone, replace `CHANGE_ME` in the two git-ignored
  files (never commit them, never paste them anywhere):
  * `secrets/ibkr_paper.env`: `TWS_USERID=<paper username>` (IBKR Account Management -> Paper Trading Account);
  * `secrets/ibkr_paper_password.txt`: the paper password alone, one line.

  One username = one session: `ibkr-paper` takes the paper session at start (`IBKR_PAPER_EXISTING_SESSION_ACTION`,
  default `primary`), so a Windows TWS on the same paper login is disconnected. Run paper either in Docker or on
  Windows, not both. `docker compose --profile trading logs -f ibkr-paper` shows the login.
* Paper only: `IBKR_ACCOUNT_MODE=paper` / `IBKR_ALLOW_LIVE=no` are pinned in the service, not read from `.env`. A
  Gateway logged into the live account makes every order refused. Book = the stack's SQL Server `DB_NAME`.
* Status: `results/spatio_temporal_momentum_10m_live/STM_10M_BANKS.supervisor.json` (state, rewritten every minute;
  the container is unhealthy when it is older than 3 minutes).
* A session already running (e.g. started by hand) is not doubled: the supervisor alerts "not started" and waits for
  the next day.
* `supervise once` (today only, waits for 09:20) and `supervise session` (one session, as below) run it without the
  container.
* Committed code only (P.08.11): a session refuses to start when tracked files have uncommitted changes (alert "not
  started", no restart). Commit first; on PAPER only, `RUN_MANIFEST_ALLOW_DIRTY=yes` overrides it (recorded). Every
  session writes `results/spatio_temporal_momentum_10m_live/run_manifest.json` (commit, config, models).

**By hand** (Windows, TWS):

```
python -c "from src.application.managers.project_managers.spatio_temporal_momentum_project_10m_live.project_manager import SpatioTemporalMomentum10mLiveProjectManager as M; M().run()"
```

* It refuses to start when start-up recovery is blocked: see §4.
* About 5 minutes of history import before the first decision; the first decision (09:40) retrains the model
  (~2.5 min CPU), so its orders leave around 09:43. Later decisions take 10–15 s.
* Started later in the day, it begins at the next 10-minute step. Started after 15:50, it waits for the next session.
* One process per day. It ends by itself after the 15:50 decision. A second `run()` or a `check()` while it runs
  is refused ("another live session holds ...", with its pid); the lock goes away with the process, even after a
  crash.

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
  re-read at every start, so settle them before starting:
  * the trade belongs to the strategy (e.g. you flattened a strategy position by hand): **adopt** it, with the
    session STOPPED — the fill is booked into the strategy's book (order, transaction, position, cash, USD commission
    in one database transaction) and the discrepancy is resolved:
    ```
    ops adopt <exec id> "<why>"          # exec id = the discrepancy's key; portfolios default to the strategy's
    ```
  * it does not (another account activity, a test outside the strategy's names): `ops resolve <id> "<why>"`.
* `position_mismatch`: IBKR position ≠ book. A manual trade in a strategy name causes it together with an
  `external_execution`: `ops adopt` that execution and the mismatch resolves itself at the next start. IBKR returns
  only **today's** executions: a manual trade from an earlier day cannot be adopted and must be corrected in the
  database. Avoid manual trades in the strategy's 24 names.
* `order_closed_on_recovery`: an order the book thought working was no longer at IBKR (e.g. cancelled at shutdown
  before IBKR answered); informational.
* `cash_drift` (never blocking): the first start of each day compares IBKR's USD cash change (USD ledger, not the CAD base-currency total) since the
  previous day's start with the book's. Up to 250 USD the difference is booked by itself as financing (interest,
  borrow fees, dividends; `ops status` shows the last `cash` line). Above 250 USD nothing is booked: check the IBKR
  statement, then, with the session STOPPED,
  * financing / dividend / fee posting: `ops cash-book <amount> "<what it is>"` (+ credit, − debit), then
    `ops resolve <id> "<what was booked>"`;
  * deposit / withdrawal (not strategy money): `ops resolve <id> "<why>"` only;
  * a trade the book missed: it shows as a `position_mismatch` too — see above.
* `split guard` (critical alert, P.08.03): a bank's stored 10-minute closes contain a jump of a split ratio (2:1,
  3:2, 1:10 ...). It usually means a stock split: IBKR serves history adjusted to the new scale while the stored bars
  keep the old one. That ticker is not traded and the model is retrained without it. Check the split in TWS / the news,
  then re-import the ticker's bars: with the session STOPPED and after a COPY_ONLY backup, delete that ticker's
  stored 10-minute `close/open/high/low/volume` factor values and let the next start's preload import them again. A
  real crash of that size is excluded too (the safe side); it becomes eligible again once the jump leaves the loaded
  history.

## 5. Stopping

* **Normal**: the session stops after 15:50. Positions are **kept overnight** (borrow fees on shorts, dividends on
  ex-dates).
* **Early**: Ctrl+C in the session window. Shutdown applies pending broker events and cancels working orders.
* **Emergency, no new risk**: `ops kill "<reason>"` (every order refused), or `ops reduce-only "<reason>"` (only
  reductions allowed). Both apply to the next order of the running session.
* **Emergency, flatten everything**: there is no `ops` command for it. `ops kill`, stop the session, then flatten in
  TWS. The book will then disagree with IBKR (§4 `position_mismatch`): start the session once (recovery records each
  manual fill as `external_execution` and blocks), stop it, `ops adopt` each execution the SAME DAY, then start
  again.

## 6. After a crash or a lost connection

**Lost connection during a session** (TWS restarted, network): nothing to do. Before each step the session
checks both IBKR connections; a dropped one is reconnected, the order path is rebuilt and start-up recovery runs
again before the next order. Log lines: `IBKR order connection lost: reconnecting` / `re-established` / `live stack
rebuilt`. While TWS is down, steps run without orders (`reconnect failed: no order this step`). If recovery is
blocked after the reconnect, the session keeps running without orders until §4 is done. Verified by dropping the
sockets; a real TWS restart has not been exercised yet — watch the first one.

**Crash** (process died): under the `trader` service it is restarted by itself (§2) up to 3 times; after "session
down for the day", or when started by hand: start again (§2). Start-up recovery reads IBKR's open orders, today's executions and
positions, books missed fills once, and blocks on anything it cannot explain.

## 7. Reference

* Config: `config.py` `LIVE` (account, limits, quote age, capital 25 000 USD) — see `CLAUDE.md`.
* Live account: only with `IBKR_ACCOUNT_MODE=live`, `IBKR_ALLOW_LIVE=yes`, `STM_LIVE_ACCOUNT=<account>`,
  `paper_bar_prices=False` and real-time US-equity data for the API. **Not ready**: `LIVE_TRADING_READINESS.txt` P.07.
