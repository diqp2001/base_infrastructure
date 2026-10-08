"""
Database monitoring through a read-only connection.

Connection preference:
  1. DB_READONLY_USER / DB_READONLY_PASSWORD (a db_datareader-only SQL Server login): read-only is
     enforced by SQL Server itself;
  2. otherwise the application connection (DB_* variables) with the application-level
     read-only guard only — reported on the dashboard as "database-level read-only: no".
"""

import socket
import time
from typing import Any, Dict, Optional

from src.infrastructure.repositories.local_repo.monitoring.monitoring_read_repository import (
    MonitoringReadRepository,
    create_read_only_engine,
    has_read_only_guard,
)


class DatabaseMonitor:

    def __init__(self, url=None, engine=None, db_level_read_only: Optional[bool] = None):
        self._url = url
        self._engine = engine
        self._repo: Optional[MonitoringReadRepository] = None
        self.db_level_read_only = db_level_read_only

    @classmethod
    def from_environment(cls) -> Optional["DatabaseMonitor"]:
        from src.infrastructure.database.settings import get_database_url, get_readonly_database_url

        url = get_readonly_database_url()
        if url is not None:
            return cls(url=url, db_level_read_only=True)
        import os
        if os.getenv("DB_HOST") or os.getenv("DB_SERVER"):
            return cls(url=get_database_url("sql_server"), db_level_read_only=False)
        return None

    @property
    def repo(self) -> MonitoringReadRepository:
        if self._repo is None:
            if self._engine is None:
                self._engine = create_read_only_engine(self._url)
            self._repo = MonitoringReadRepository(self._engine)
        return self._repo

    def health(self) -> Dict[str, Any]:
        info = self.repo.ping()
        info["db_level_read_only"] = (self.db_level_read_only if info.get("login_can_write") is None
                                      else (bool(self.db_level_read_only) and not info["login_can_write"]))
        info["app_level_read_only_guard"] = has_read_only_guard(self.repo.engine)
        return info


def tcp_probe(host: Optional[str], port: Optional[int], timeout: float = 2.0) -> Dict[str, Any]:
    """Network-level reachability (not application readiness)."""
    if not host or not port:
        return {"host": host, "port": port, "reachable": None, "latency_ms": None, "error": "not configured"}
    t0 = time.perf_counter()
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            pass
        return {"host": host, "port": int(port), "reachable": True,
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 1), "error": None}
    except OSError as e:
        return {"host": host, "port": int(port), "reachable": False, "latency_ms": None,
                "error": type(e).__name__}
