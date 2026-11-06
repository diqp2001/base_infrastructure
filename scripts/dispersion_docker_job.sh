#!/bin/bash
# Runs a dispersion screener module in the dev image on the Docker network of the paper gateway (READ-ONLY on IBKR:
# market data and contract lookups only). Used by the /dispersion page to start a maturities job.
#     dispersion_docker_job.sh LOG_FILE PYTHON_MODULE [ARGS...]
REPO="$(cd "$(dirname "$0")/.." && pwd)"
LOG="$1"; shift
mkdir -p "$(dirname "$LOG")"
docker run --rm --network "${DISPERSION_DOCKER_NETWORK:-base_infrastructure_net}" -v "$REPO":/w -w /w \
  -e PYTHONPATH=/w -e TZ=America/New_York \
  -e DISPERSION_IBKR_HOST="${DISPERSION_IBKR_HOST:-ibkr-paper}" -e DISPERSION_IBKR_PORT="${DISPERSION_IBKR_PORT:-4004}" \
  "${DISPERSION_DOCKER_IMAGE:-base_infrastructure-dev:py3.13}" python -u -m "$@" > "$LOG" 2>&1
