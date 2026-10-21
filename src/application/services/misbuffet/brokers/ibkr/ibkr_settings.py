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
    IBKR_HISTORY_RETRIES / IBKR_HISTORY_RETRY_DELAY
                        extra attempts for a historical request that failed transiently (pacing,
                        farm disconnected, no answer in time) and the first backoff in seconds,
                        doubled each attempt (default 2 / 10); "no data" answers are never retried

With none of these variables set (Windows .venv) nothing changes.

Orders (BI-005): the only call sending an order is IBTWSClient.place_order, which calls
verify_connected_accounts first: the account TWS reports in ``managedAccounts`` must be of the
configured mode (paper accounts start with D: DU…, DF…), otherwise AccountModeMismatch and
nothing is sent. Connections built elsewhere with a hard-coded 7497 (project trainers,
api_service.ibkr_service, broker_factory defaults, monitoring) are data-only or reach TWS
through that same order path, so the port they were given never decides paper vs live.
tests/architecture/test_order_paths.py keeps it that way.
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


class AccountModeMismatch(PermissionError):
    """The account TWS / IB Gateway is logged into is not the kind IBKR_ACCOUNT_MODE allows: no order is sent."""


PAPER_ACCOUNT_PREFIX = "D"      # IBKR paper accounts: DU… (individual), DF… / DI… (advisor / broker masters)


def account_kind(account_id: str) -> str:
    return "paper" if account_id.strip().upper().startswith(PAPER_ACCOUNT_PREFIX) else "live"


def verify_connected_accounts(accounts, order_account: str = "", mode: Optional[str] = None) -> None:
    """Raise AccountModeMismatch unless the order would go to an account of the configured mode.

    ``accounts`` is what TWS reported in ``managedAccounts`` for this connection. Fail closed: no reported
    account, or an order account the connection does not manage, refuses the order. Without an order
    account TWS uses its default account, so every managed account must match the mode."""
    mode = mode or account_mode()
    managed = [a.strip() for a in (accounts or []) if a and a.strip()]
    if not managed:
        raise AccountModeMismatch("connected account unknown (TWS sent no managedAccounts): order refused")
    order_account = (order_account or "").strip()
    if order_account and order_account not in managed:
        raise AccountModeMismatch(f"order account {order_account} is not managed by this connection {managed}")
    wrong = [a for a in ([order_account] if order_account else managed) if account_kind(a) != mode]
    if wrong:
        raise AccountModeMismatch(f"IBKR_ACCOUNT_MODE={mode} but the connected account(s) {wrong} are "
                                  f"{account_kind(wrong[0])}: order refused")


class IBKRSettingsError(ValueError, RuntimeError):
    """Invalid IBKR_* settings. A ValueError (bad value) and a RuntimeError (the live guard has always raised
    RuntimeError), so callers catching either keep working."""


def validate_environment() -> None:
    """Check every IBKR_* variable at once; raise IBKRSettingsError listing all the problems (before connecting)."""
    errors = []
    for name in ("IBKR_PORT", "IBKR_CLIENT_ID", "IBKR_CONNECT_RETRIES", "IBKR_HISTORY_RETRIES"):
        try:
            value = _int_env(name)
        except ValueError as e:
            errors.append(str(e))
            continue
        if value is not None and value < 0:
            errors.append(f"{name} must be >= 0, got {value}")
    for name in ("IBKR_CONNECT_RETRY_DELAY", "IBKR_HISTORY_RETRY_DELAY"):
        delay = os.getenv(name)
        if delay:
            try:
                if float(delay) < 0:
                    errors.append(f"{name} must be >= 0, got {delay!r}")
            except ValueError:
                errors.append(f"{name} must be a number, got {delay!r}")
    try:
        account_mode()
    except (ValueError, RuntimeError) as e:
        errors.append(str(e))
    if errors:
        raise IBKRSettingsError("invalid IBKR settings: " + "; ".join(errors))


def resolve_endpoint(host: str, port: int, client_id: int) -> IBKREndpoint:
    """Endpoint after applying the IBKR_* environment overrides to the configured values."""
    validate_environment()
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


# Historical data requests (BI-029): transient failures are retried a bounded number of times with
# exponential backoff (IBKR_HISTORY_RETRIES, default 2; IBKR_HISTORY_RETRY_DELAY seconds, default 10).
# "No data" (162 without "pacing"), "no security definition" (200) etc. are answers, never retried.
TRANSIENT_HISTORY_ERRORS = {322, 366, 1100, 2103, 2105, 10182}


def is_transient_history_error(code: int, message: str = "") -> bool:
    return code in TRANSIENT_HISTORY_ERRORS or (code == 162 and "pacing" in (message or "").lower())


def history_retries() -> int:
    value = _int_env("IBKR_HISTORY_RETRIES")
    return 2 if value is None else max(0, value)


def history_retry_delay() -> float:
    value = os.getenv("IBKR_HISTORY_RETRY_DELAY")
    return float(value) if value else 10.0


def connect_retries() -> int:
    return max(0, _int_env("IBKR_CONNECT_RETRIES") or 0)


def connect_retry_delay() -> float:
    value = os.getenv("IBKR_CONNECT_RETRY_DELAY")
    return float(value) if value else 5.0
