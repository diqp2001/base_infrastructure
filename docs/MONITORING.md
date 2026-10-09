# Read-only monitoring dashboard

A mobile-friendly website that shows the real state of the trading infrastructure — application,
IB Gateway, SQL Server, account, positions, open orders, market-data freshness, factors, jobs and
logs — **without any login and without any way to trade or change anything**.

```
phone ──(Tailscale, private)──► Windows: tailscale serve ──► 127.0.0.1:8050 ──► monitor container
                                                                               │  GET-only Flask app
                                                       read-only SQL login ◄───┤
                                         IBKR read-only client (client id 90) ◄┘
```

The environment itself (WSL2, Docker Desktop, VS Code, the `app` / `ibkr` / `sqlserver` services) is
described in [.devcontainer/README.md](../.devcontainer/README.md).

---

## 1. Start it

The dashboard is the `monitor` compose service (started with the dev container, or by hand):

```bash
cd ~/code/base_infrastructure
docker compose up -d monitor          # also starts sqlserver (+ the one-shot sqlserver-init)
docker compose ps monitor             # wait for "healthy"
docker compose logs -f monitor        # gunicorn + collector logs
docker compose restart monitor        # after changing its code (it does not auto-reload)
```

It does not need IB Gateway to run: when `ibkr` is down the dashboard shows it as disconnected.

## 2. Open it

| From | URL |
|---|---|
| The development computer (Windows browser) | http://127.0.0.1:8050/ |
| VS Code debug run ("Python: Monitoring Dashboard", F5) | http://localhost:8051/ |
| The development Flask app (also mounts the pages) | http://localhost:5000/monitor/ |
| A phone, remotely | `https://<windows-machine>.<tailnet>.ts.net/` through Tailscale (below) |

Pages: Overview · IBKR & account · Infrastructure · Market data · Factors & jobs · Logs · Settings.
Sections refresh themselves (no page reload) and have a Refresh button; every section shows when its
data was collected and turns **Stale** when that is too old.

### Phone access with Tailscale (recommended)

The dashboard has no login, so it must only be reachable from your own devices. Tailscale creates a
private network between them; nothing is opened on your router or the internet.

1. Install Tailscale on Windows (`winget install -e --id Tailscale.Tailscale`) and on the phone
   (App Store / Play Store); sign in to the same tailnet on both.
2. On Windows, publish the dashboard **inside the tailnet only**:
   ```powershell
   tailscale serve --bg 8050
   tailscale serve status        # shows https://<machine>.<tailnet>.ts.net/
   ```
   `tailscale serve` proxies tailnet HTTPS to `127.0.0.1:8050`; the dashboard itself stays bound to
   localhost. **Never use `tailscale funnel`** — that publishes to the public internet.
3. Open the `https://…ts.net/` address on the phone. Optionally restrict which devices can reach it
   with a Tailscale ACL. To stop: `tailscale serve --https=443 off`.

### Local network (optional, not recommended)

Only on a trusted network: set `DASHBOARD_BIND=0.0.0.0` in `.env`, `docker compose up -d monitor`,
and allow TCP 8050 in Windows Firewall for the **Private** profile and your subnet only, e.g.
`New-NetFirewallRule -DisplayName "monitor 8050 LAN" -Direction Inbound -Protocol TCP -LocalPort 8050 -Profile Private -RemoteAddress 192.168.2.0/24 -Action Allow`.
Anyone on that network can then read the dashboard.

## 3. Read-only security model

The dashboard can be used to inspect the system, not to act on it. Protections, from the outside in:

| Layer | Protection |
|---|---|
| Network | Published on `127.0.0.1` only (compose `ports`); remote access only through a private network (Tailscale). SQL Server (`127.0.0.1:14333`) and the IBKR API (`127.0.0.1:4002`) are also localhost-only; the dashboard never exposes them. |
| Process | The `monitor` service runs `monitoring_app.py`, which registers **only** the monitoring routes (no upload / backtest / trading routes of the development app). |
| HTTP | Every request that is not GET / HEAD / OPTIONS is rejected with **405** before any handler runs; no forms, no generic SQL / command / file endpoints; query parameters validated and bounded. |
| Frontend | No order, cancel, start/stop or configuration controls; Content-Security-Policy `default-src 'self'; form-action 'none'`, no external scripts, `Cache-Control: no-store`. |
| IBKR | `ReadOnlyIBKRClient` (not `IBTWSClient`): `placeOrder`, `cancelOrder`, `reqGlobalCancel`, `exerciseOptions`, `reqAutoOpenOrders`, `requestFA`, `replaceFA`, `reqIds` raise. It only sends `reqCurrentTime`, `reqAccountSummary`, `reqAccountUpdates`, `reqPositions`, `reqAllOpenOrders`; it uses its own client id (90), one background connection; browser requests only read its snapshot. Gateway-side, `IBKR_READ_ONLY_API=yes` additionally blocks orders for every API client. |
| Database | Login `monitor_reader` (created by `sqlserver-init`): member of `db_datareader` only, `INSERT/UPDATE/DELETE/ALTER/EXECUTE/REFERENCES` denied — enforced by SQL Server. The engine also refuses any statement that is not SELECT/WITH/SET, and queries use SQLAlchemy Core (no ORM session, nothing to flush). The Infrastructure page shows "Read-only login (SQL Server enforced)". |
| Container | `read_only: true` root filesystem, repository mounted `:ro`, `cap_drop: ALL`, `no-new-privileges`, no Docker socket, no secrets mounted, no SA or IBKR password in its environment. |
| Data | Responses and log lines are redacted (passwords, `PWD={…}`, URL-encoded connection strings, tokens, API keys, values of `*PASSWORD*/*SECRET*/*TOKEN*/*KEY*` variables). Missing values are shown as *Unavailable*, never as 0. |

## 4. What each page shows and where it comes from

| Page | Source |
|---|---|
| Overview | aggregation of the sections below; overall = worst of application / database / IBKR |
| IBKR & account | read-only IBKR connection: heartbeat, configured vs detected paper/live mode, account summary (`$LEDGER:ALL` per currency, currencies never combined), positions merged with portfolio market values, open orders of all clients (view only) |
| Infrastructure | dashboard process health, SQL Server health / latency / version via the read-only login, IBKR API state, TCP reachability of `sqlserver` / `ibkr` (network level, kept separate from application readiness). Container uptime is intentionally unavailable (no Docker API). |
| Market data | latest `factor_values` observation per non-calculated factor and instrument, age, expected frequency (`Factor.frequency_seconds`), stale flags, market-data warnings from the logs. "Last historical retrieval" / "last live update" are *Unavailable*: the schema stores observation times, not download times. |
| Factors & jobs | factor value counts / first / last dates per factor, calculated factors, backtest jobs recorded by `BaseBacktestRunner.run_backtest` (start, end, duration, error) and existing project `progress.json` files under `results/*/` |
| Logs | WARNING/INFO/ERROR records of application processes (`.monitor/logs/*.jsonl`, written by `ProjectManager` / backtest runs) and of the dashboard; filters: level, component, period, text |
| Settings | non-secret configuration only |

Collection intervals (seconds, `.env`): `MONITOR_HEALTH_INTERVAL=10`, `MONITOR_ACCOUNT_INTERVAL=30`,
`MONITOR_POSITIONS_INTERVAL=30`, `MONITOR_DATA_INTERVAL=30`, `MONITOR_LOGS_INTERVAL=15`.
Data older than 3 × its interval is reported **Stale**. IBKR is queried by one background loop,
never per browser request.

## 5. API (all GET, JSON)

```
/monitor/api/health                /monitor/api/status               /monitor/api/status/connections
/monitor/api/status/database       /monitor/api/status/ibkr          /monitor/api/account/summary
/monitor/api/account/positions     /monitor/api/account/orders       /monitor/api/market-data/status?limit=&stale_only=&q=
/monitor/api/factors/status?limit=&q=   /monitor/api/jobs/status?limit=   /monitor/api/logs/recent?level=&component=&since_minutes=&q=&limit=
/monitor/api/config
```
Each section response: `{status, stale, age_seconds, stale_after_seconds, updated_at, last_success,
error, data, generated_at}` with `status` one of healthy · degraded · disconnected · error · unknown · stale.

## 6. Tests

```bash
docker compose exec app python -m pytest tests/monitoring -v      # unit tests, no live services
docker compose exec app python -m pytest tests/integration -v     # app -> sqlserver / ibkr connectivity
```
`tests/monitoring` checks: GET-only routes and 405 on every mutating method, only monitoring routes in
the dashboard app, no INSERT/UPDATE/DELETE issued and row counts unchanged while every endpoint is
called, forbidden IBKR methods raise and the monitor loop only sends read requests (≤ 2 account-summary
subscriptions, IBKR's limit), secrets never appear in responses or logs, zero vs unavailable values,
currency separation, stale / disconnected states, configuration validation, and that compose publishes
nothing beyond 127.0.0.1 and hardens the `monitor` container.

## 7. Troubleshooting

| Symptom | Check |
|---|---|
| IB Gateway "disconnected" | `docker compose ps ibkr` (healthy?), `docker compose logs --tail 100 ibkr` (login, 2FA), `IBKR_PORT` (4004 paper / 4003 live) |
| Account values Unavailable | not yet received after (re)connection, or not provided by IBKR for this account (e.g. SettledCash) |
| Database "error" / "disconnected" | `docker compose ps sqlserver`; the read-only login exists only after `sqlserver-init` ran: `docker compose up -d sqlserver-init` |
| Dashboard unreachable from phone | `tailscale serve status` on Windows; both devices in the same tailnet; `curl http://127.0.0.1:8050/monitor/api/health` on Windows |
| No application logs | logs appear once an application process (`src/main.py`, a backtest) ran with `MONITOR_STATE_DIR` — they are written to `.monitor/logs/` (git-ignored) |
