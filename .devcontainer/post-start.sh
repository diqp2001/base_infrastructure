#!/usr/bin/env bash
# Runs every time the dev container starts (devcontainer.json "postStartCommand").
# Prints the Python environment and whether the sqlserver / ibkr services answer on the
# Docker network. It never fails: the application handles a service that is still starting
# (IBKR_CONNECT_RETRIES) and the services can be restarted independently.
set -u

probe() {   # probe <label> <host> <port>
    if timeout 3 bash -c "exec 3<>/dev/tcp/$2/$3" 2>/dev/null; then
        echo "[post-start] $1  $2:$3  reachable"
    else
        echo "[post-start] $1  $2:$3  NOT reachable (docker compose logs $2)"
    fi
}

echo "[post-start] $(python --version) at $(command -v python)"
probe "SQL Server " "${DB_HOST:-sqlserver}" "${DB_PORT:-1433}"
probe "IB Gateway " "${IBKR_HOST:-ibkr}" "${IBKR_PORT:-4004}"
echo "[post-start] IBKR mode ${IBKR_ACCOUNT_MODE:-paper}, client id ${IBKR_CLIENT_ID:-1}; database ${DB_NAME:-base_infra}"
exit 0
