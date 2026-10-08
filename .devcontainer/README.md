# Linux development environment: WSL2 + Docker + VS Code Dev Containers

```
Windows ── VS Code ── WSL2 (Ubuntu) ── Docker ──┬── app        Python 3.13, base_infrastructure, debugpy
                                                 ├── ibkr       IB Gateway (paper), headless (IBC + Xvfb)
                                                 └── sqlserver  SQL Server 2022 Developer
                       network base_infrastructure_net:  app → sqlserver:1433,  app → ibkr:4004
```

Each service is its own container and can be started, stopped and restarted on its own.
VS Code attaches to `app`; Python, the debugger and the tests run in Linux.

---

## 1. One-time workstation setup

### WSL2 + Ubuntu (PowerShell as administrator)

```powershell
wsl --install -d Ubuntu-24.04      # skip if `wsl -l -v` already lists Ubuntu with VERSION 2
wsl --set-default-version 2
wsl --update
```

Open "Ubuntu" once from the Start menu to create the Linux user, then in Ubuntu:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git
git config --global core.autocrlf input
```

### Docker Desktop (Windows)

```powershell
winget install -e --id Docker.DockerDesktop
```

Docker Desktop → Settings:
* General: "Use the WSL 2 based engine" ✔
* Resources → WSL integration: enable integration with **Ubuntu** ✔

Check from Ubuntu: `docker version` and `docker compose version`.

### VS Code (Windows)

```powershell
code --install-extension ms-vscode-remote.remote-wsl
code --install-extension ms-vscode-remote.remote-containers
```

## 2. Repository location

Clone the repository **inside the WSL file system** (fast bind mounts, Linux permissions and
line endings), not under `C:\` / `/mnt/c`:

```bash
mkdir -p ~/code && cd ~/code
git clone <repo-url> base_infrastructure
cd base_infrastructure
cp .env.example .env
nano .env          # set TWS_USERID / TWS_PASSWORD (IBKR PAPER username), passwords if wanted
code .             # opens VS Code on Windows, connected to WSL
```

In VS Code: **F1 → Dev Containers: Reopen in Container**. The first build installs every
dependency (several minutes); later starts reuse the image.

## 3. Services

| Service | Image | Reached from `app` as | From Windows | Data |
|---|---|---|---|---|
| `sqlserver` | `mcr.microsoft.com/mssql/server:2022-latest` | `sqlserver:1433` | `localhost,14333` | volume `sqlserver-data` |
| `sqlserver-init` | same | – (one-shot: `CREATE DATABASE base_infra` if missing) | – | – |
| `ibkr-init` | same as `ibkr` | – (one-shot: makes the settings volume writable for the Gateway user) | – | – |
| `ibkr` | `ghcr.io/gnzsnz/ib-gateway:stable` | `ibkr:4004` (paper) | `localhost:4002` API, `localhost:5900` VNC | volume `ibkr-settings` |
| `app` | built from `.devcontainer/Dockerfile` | – | `localhost:5000` (Flask, forwarded) | repository bind mount |

Startup order (health checks, not only `depends_on`):
`sqlserver` healthy (`sqlcmd SELECT 1`) → `sqlserver-init` completed and `ibkr` started →
`ibkr` healthy (Gateway API port open = logged in) → `app`.

Without IBKR credentials the Gateway never becomes healthy; to work on the code anyway set
`IBKR_APP_START_CONDITION=service_started` in `.env`. The application itself retries the IBKR
connection (`IBKR_CONNECT_RETRIES`, `IBKR_CONNECT_RETRY_DELAY`), so a Gateway that is
restarting or still logging in is not fatal.

### Docker Compose commands (from the repository folder in Ubuntu, or a VS Code terminal on WSL)

```bash
docker compose up -d                     # start everything (builds app the first time)
docker compose up -d --build app         # rebuild the app image after changing requirements
docker compose ps                        # state + health of each service
docker compose stop ibkr                 # stop one service   (also: sqlserver, app)
docker compose start ibkr                # start it again
docker compose restart ibkr              # restart one service
docker compose down                      # stop and remove containers; volumes (data) are kept
docker compose logs -f ibkr              # follow logs of one service (sqlserver, app, sqlserver-init)
docker compose logs --tail 200 sqlserver
docker compose exec app bash             # shell in the app container
```

## 4. SQL Server

* The application builds its connection in `src/infrastructure/database/settings.py`
  (`DatabaseService("sql_server")`). In the container `DB_HOST=sqlserver` selects SQL
  authentication:
  ```
  DRIVER={ODBC Driver 18 for SQL Server};SERVER=sqlserver,1433;DATABASE=base_infra;
  UID=sa;PWD={DB_PASSWORD};Encrypt=yes;TrustServerCertificate=yes
  ```
  Driver stack: SQLAlchemy `mssql+pyodbc` → pyodbc → unixODBC → Microsoft ODBC Driver 18.
  Without these variables (Windows `.venv`) the original Windows configuration is used.
* Tables are created by the application (`BaseFactory` → `metadata.create_all`).
* From Windows: SSMS / Azure Data Studio → server `localhost,14333`, SQL login `sa`,
  password `MSSQL_SA_PASSWORD`, "Trust server certificate".
* From the app container: `sqlcmd -C -S sqlserver -U sa -P "$DB_PASSWORD" -d base_infra -Q "SELECT name FROM sys.tables"`
* The container database starts empty (it is not a copy of the Windows instance).

Reset the development database (deletes all SQL Server data):

```bash
docker compose stop app sqlserver
docker compose rm -f sqlserver sqlserver-init
docker volume rm base_infrastructure_sqlserver-data
docker compose up -d
```

## 5. IBKR / IB Gateway

* `ibkr` runs IB Gateway headless: IBC logs in with `TWS_USERID` / `TWS_PASSWORD` inside a
  virtual X display (Xvfb); `socat` publishes the Gateway API (container-local 4002 paper /
  4001 live) on 4004 / 4003 of the Docker network. No GUI or IBKR software runs in `app`.
* Paper trading is the default: `IBKR_ACCOUNT_MODE=paper`, Gateway `TRADING_MODE=paper`,
  app port 4004. Live needs `IBKR_ACCOUNT_MODE=live`, `IBKR_ALLOW_LIVE=yes`, `IBKR_PORT=4003`;
  without `IBKR_ALLOW_LIVE=yes` the application refuses to create the IBKR broker.
* The application keeps its configuration (`127.0.0.1:7497`, client id 1) in code; in the
  container `InteractiveBrokersBroker` replaces it with `IBKR_HOST`/`IBKR_PORT`
  (`ibkr:4004`) and the default client id 1 with `IBKR_CLIENT_ID`
  (`src/application/services/misbuffet/brokers/ibkr/ibkr_settings.py`).
* One IBKR username = one session. `IBKR_EXISTING_SESSION_ACTION=secondary` (default) makes the
  container back off if the same user is logged in elsewhere (e.g. TWS on Windows) instead of
  disconnecting it. Use a separate paper username for the container, or log out of TWS.
* Settings persist in the `ibkr-settings` volume (`TWS_SETTINGS_PATH`); the Gateway restarts
  itself daily at `IBKR_AUTO_RESTART_TIME`.
* 2FA / first login problems: set `IBKR_VNC_PASSWORD` in `.env`, `docker compose up -d ibkr`,
  and open a VNC viewer on `localhost:5900` to see the Gateway window. Logs:
  `docker compose logs -f ibkr`.

Start / restart only the Gateway:

```bash
docker compose up -d ibkr
docker compose restart ibkr
docker compose ps ibkr          # wait for "healthy"
```

## 6. Debugging (F5)

`.vscode/launch.json` runs inside the container with `/opt/venv/bin/python`:

* **Python Debugger: Main File** — `src/main.py`
* **Python: Flask App** — `src/interfaces/flask/app.py` (http://localhost:5000, Jinja debugging on)

Breakpoints, step over / into / out, variables, call stack and the "Raised / Uncaught
Exceptions" options of the Breakpoints panel work as usual (debugpy runs in the container).
`src/main.py` runs whatever project is enabled at the bottom of the file; with the IBKR
projects it connects to `ibkr:4004` and the `base_infra` database of `sqlserver`.

Run without the debugger:

```bash
python src/main.py
python src/interfaces/flask/app.py      # Flask on 0.0.0.0:5000, forwarded to Windows
```

## 7. Tests

```bash
python -m pytest tests -q                         # whole suite
python -m pytest tests/integration -v             # app → sqlserver, app → ibkr connectivity
```

`tests/integration/test_docker_services.py` checks SQLAlchemy → SQL Server (version, database,
a repository write/read through `RepositoryFactory`) and the IBKR API handshake with IB Gateway
(server time, accounts must be paper accounts `D…` in paper mode). It never sends an order and
uses `IBKR_TEST_CLIENT_ID` (999) so it does not collide with a running session. Outside the
container these tests are skipped. The Testing panel of VS Code uses pytest on `tests/`.

## 8. Files

| File | Role |
|---|---|
| `docker-compose.yml` | services, network, volumes, health checks, startup order |
| `.env.example` → `.env` | credentials and configuration (`.env` is git-ignored) |
| `.devcontainer/devcontainer.json` | VS Code attaches to `app`, interpreter, extensions |
| `.devcontainer/Dockerfile` | Debian 12 + Python 3.13 + ODBC Driver 18 + `requirements-dev.txt` |
| `.devcontainer/post-start.sh` | prints the environment and whether sqlserver / ibkr answer |
| `requirements.txt` / `requirements-dev.txt` | pinned dependencies (Windows and Linux) |
| `src/infrastructure/database/settings.py` | SQL Server connection from `DB_*` variables |
| `src/application/services/misbuffet/brokers/ibkr/ibkr_settings.py` | IBKR endpoint from `IBKR_*` variables |

The legacy all-in-one image (root `Dockerfile`, `docker/`) is not part of this environment.
