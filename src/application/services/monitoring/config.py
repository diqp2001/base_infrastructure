"""
MonitoringConfig — dashboard configuration from environment variables, validated at startup.

Only non-secret values are kept here (hosts, ports, intervals, modes). Credentials stay in the
environment / secret files and are read by the infrastructure layer when connecting.
"""

import os
from dataclasses import asdict, dataclass, field
from typing import Dict, Optional, Tuple

ACCOUNT_MODES = ("paper", "live")


class MonitoringConfigError(ValueError):
    """Invalid monitoring configuration (raised at startup)."""


def _int(env: Dict[str, str], name: str, default: int, lo: int, hi: int) -> int:
    raw = env.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        raise MonitoringConfigError(f"{name} must be an integer, got {raw!r}") from None
    if not lo <= value <= hi:
        raise MonitoringConfigError(f"{name} must be between {lo} and {hi}, got {value}")
    return value


def _bool(env: Dict[str, str], name: str, default: bool) -> bool:
    raw = env.get(name)
    if raw is None or str(raw).strip() == "":
        return default
    value = str(raw).strip().lower()
    if value in ("1", "true", "yes", "on"):
        return True
    if value in ("0", "false", "no", "off"):
        return False
    raise MonitoringConfigError(f"{name} must be true/false, got {raw!r}")


@dataclass(frozen=True)
class RefreshIntervals:
    """Seconds between background collections (and suggested browser polling)."""
    health: int = 10        # application / connection health
    account: int = 30       # account summary
    positions: int = 30     # positions and open orders
    data: int = 30          # market-data freshness and factor status
    logs: int = 15          # log viewer


@dataclass(frozen=True)
class MonitoringConfig:
    environment: str = "development"
    version: str = "unknown"
    # database
    db_host: Optional[str] = None
    db_port: int = 1433
    db_name: str = "base_infra"
    db_readonly_configured: bool = False
    # IBKR
    ibkr_enabled: bool = True
    ibkr_host: str = "127.0.0.1"
    ibkr_port: int = 7497
    ibkr_client_id: int = 90
    ibkr_account_mode: str = "paper"
    ibkr_allow_live: bool = False
    # files written by the application processes and read by the dashboard
    state_dir: str = ".monitor"
    results_dir: str = "results"
    # behaviour
    intervals: RefreshIntervals = field(default_factory=RefreshIntervals)
    stale_factor: float = 3.0          # data is stale when older than stale_factor x interval
    log_buffer_size: int = 2000
    max_rows: int = 500

    @classmethod
    def from_env(cls, env: Optional[Dict[str, str]] = None) -> "MonitoringConfig":
        env = dict(os.environ if env is None else env)
        mode = (env.get("IBKR_ACCOUNT_MODE") or "paper").strip().lower()
        if mode not in ACCOUNT_MODES:
            raise MonitoringConfigError(f"IBKR_ACCOUNT_MODE must be one of {ACCOUNT_MODES}, got {mode!r}")
        default_port = 7497
        intervals = RefreshIntervals(
            health=_int(env, "MONITOR_HEALTH_INTERVAL", 10, 2, 3600),
            account=_int(env, "MONITOR_ACCOUNT_INTERVAL", 30, 5, 3600),
            positions=_int(env, "MONITOR_POSITIONS_INTERVAL", 30, 5, 3600),
            data=_int(env, "MONITOR_DATA_INTERVAL", 30, 5, 3600),
            logs=_int(env, "MONITOR_LOGS_INTERVAL", 15, 2, 3600),
        )
        return cls(
            environment=(env.get("APP_ENV") or "development").strip() or "development",
            version=(env.get("APP_VERSION") or "").strip() or _git_version(),
            db_host=(env.get("DB_HOST") or env.get("DB_SERVER") or None),
            db_port=_int(env, "DB_PORT", 1433, 1, 65535),
            db_name=(env.get("DB_NAME") or "base_infra"),
            db_readonly_configured=bool(env.get("DB_READONLY_USER")),
            ibkr_enabled=_bool(env, "MONITOR_IBKR_ENABLED", True),
            ibkr_host=(env.get("IBKR_HOST") or "127.0.0.1"),
            ibkr_port=_int(env, "IBKR_PORT", default_port, 1, 65535),
            ibkr_client_id=_int(env, "IBKR_MONITOR_CLIENT_ID", 90, 0, 2_147_483_647),
            ibkr_account_mode=mode,
            ibkr_allow_live=(env.get("IBKR_ALLOW_LIVE") or "").strip().lower() == "yes",
            state_dir=env.get("MONITOR_STATE_DIR") or ".monitor",
            results_dir=env.get("MONITOR_RESULTS_DIR") or "results",
            intervals=intervals,
            log_buffer_size=_int(env, "MONITOR_LOG_BUFFER", 2000, 100, 100_000),
            max_rows=_int(env, "MONITOR_MAX_ROWS", 500, 10, 10_000),
        )

    def safe_view(self) -> Dict:
        """Non-sensitive configuration for the settings page (no credentials, no usernames)."""
        data = asdict(self)
        data["intervals"] = asdict(self.intervals)
        return data


def _git_version(root: str = ".") -> str:
    """Short commit of the checked-out repository (read from .git, never by running git)."""
    try:
        head = open(os.path.join(root, ".git", "HEAD"), encoding="utf-8").read().strip()
        if head.startswith("ref: "):
            ref = head[5:]
            path = os.path.join(root, ".git", *ref.split("/"))
            if os.path.exists(path):
                return f"{ref.rsplit('/', 1)[-1]}@{open(path, encoding='utf-8').read().strip()[:8]}"
            packed = os.path.join(root, ".git", "packed-refs")
            if os.path.exists(packed):
                for line in open(packed, encoding="utf-8"):
                    if line.strip().endswith(ref):
                        return f"{ref.rsplit('/', 1)[-1]}@{line.split()[0][:8]}"
            return ref.rsplit("/", 1)[-1]
        return head[:8]
    except OSError:
        return "unknown"
