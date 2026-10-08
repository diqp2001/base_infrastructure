"""
IBKR connection endpoint from the environment.

The code base passes 127.0.0.1:7497 / client id 1 to the broker in many places (TWS on the
same Windows machine). In the Docker development environment the API is served by the
``ibkr`` service (IB Gateway), so the deployment overrides the endpoint with environment
variables, applied once in InteractiveBrokersBroker:

    IBKR_HOST           host of TWS / IB Gateway          (e.g. ibkr)
    IBKR_PORT           API port                          (IB Gateway container: 4004 paper)
    IBKR_CLIENT_ID      replaces the default client id 1; explicit other ids are kept
    IBKR_ACCOUNT_MODE   paper (default) | live
    IBKR_ALLOW_LIVE     must be "yes" for IBKR_ACCOUNT_MODE=live (guard against live by mistake)
    IBKR_CONNECT_RETRIES / IBKR_CONNECT_RETRY_DELAY
                        extra connection attempts and seconds between them (default 0 / 5)

With none of these variables set (Windows .venv) nothing changes.
"""

import os
from dataclasses import dataclass
from typing import Optional

DEFAULT_CLIENT_ID = 1
ACCOUNT_MODES = ("paper", "live")


@dataclass(frozen=True)
class IBKREndpoint:
    host: str
    port: int
    client_id: int
    account_mode: str
    overridden: bool

    @property
    def paper(self) -> bool:
        return self.account_mode == "paper"


def _int_env(name: str) -> Optional[int]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"{name} must be an integer, got {value!r}") from None


def account_mode() -> str:
    mode = (os.getenv("IBKR_ACCOUNT_MODE") or "paper").strip().lower()
    if mode not in ACCOUNT_MODES:
        raise ValueError(f"IBKR_ACCOUNT_MODE must be one of {ACCOUNT_MODES}, got {mode!r}")
    if mode == "live" and (os.getenv("IBKR_ALLOW_LIVE") or "").strip().lower() != "yes":
        raise RuntimeError("IBKR_ACCOUNT_MODE=live requires IBKR_ALLOW_LIVE=yes "
                           "(the development environment is paper trading by default)")
    return mode


def resolve_endpoint(host: str, port: int, client_id: int) -> IBKREndpoint:
    """Endpoint after applying the IBKR_* environment overrides to the configured values."""
    env_host = (os.getenv("IBKR_HOST") or "").strip() or None
    env_port = _int_env("IBKR_PORT")
    env_client = _int_env("IBKR_CLIENT_ID")
    mode = account_mode()
    new_client = env_client if (env_client is not None and client_id == DEFAULT_CLIENT_ID) else client_id
    endpoint = IBKREndpoint(
        host=env_host or host,
        port=env_port if env_port is not None else port,
        client_id=new_client,
        account_mode=mode,
        overridden=bool(env_host or env_port is not None or new_client != client_id),
    )
    return endpoint


def connect_retries() -> int:
    return max(0, _int_env("IBKR_CONNECT_RETRIES") or 0)


def connect_retry_delay() -> float:
    value = os.getenv("IBKR_CONNECT_RETRY_DELAY")
    return float(value) if value else 5.0
