"""
MonitoringService — background collection + read-only views for the dashboard.

One instance per dashboard process (``get_monitoring_service()``):

* a database thread: health / latency every ``intervals.health`` seconds, factor and
  market-data freshness every ``intervals.data`` seconds (bounded, grouped queries);
* the IBKR monitor thread (one API connection, its own client id);
* logs and job files are read on request (bounded tails of files written by the app).

Every public method only reads. No method here can place orders, write to the database,
start jobs or change configuration.
"""

import logging
import os
import platform
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.application.services.monitoring.config import MonitoringConfig
from src.application.services.monitoring.db_monitor import DatabaseMonitor, tcp_probe
from src.application.services.monitoring.job_tracker import FAILED, RUNNING, JobReader
from src.application.services.monitoring.log_store import COMPONENTS, LEVELS, LogReader, RingBufferHandler
from src.application.services.monitoring.redaction import redact, redact_text
from src.application.services.monitoring.status import (
    DEGRADED, DISCONNECTED, ERROR, HEALTHY, STALE, UNKNOWN, Section, iso, make_view, utcnow, worst,
)

logger = logging.getLogger("monitoring.service")
MAX_BAR_STALENESS_SECONDS = 4 * 86400      # same default as Factor.MAX_BAR_STALENESS_SECONDS


def _frequency_seconds(frequency: Optional[str]) -> Optional[int]:
    try:
        from src.domain.entities.factor.factor import Factor
        return Factor.frequency_seconds(frequency)
    except Exception:
        return None


def _as_utc(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if hasattr(value, "year"):          # date
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


class MonitoringService:

    def __init__(self, config: MonitoringConfig, db: Optional[DatabaseMonitor] = None, ibkr=None,
                 ring: Optional[RingBufferHandler] = None):
        self.config = config
        self.db = db
        self.ibkr = ibkr
        self.ring = ring
        self.logs = LogReader(config.state_dir, ring=ring)
        self.jobs = JobReader(config.state_dir, config.results_dir)
        iv, k = config.intervals, config.stale_factor
        self.s_database = Section("database", stale_after_seconds=iv.health * k + 5)
        self.s_network = Section("network", stale_after_seconds=iv.health * k + 5)
        self.s_factors = Section("factors", stale_after_seconds=iv.data * k + 5)
        self.s_market = Section("market_data", stale_after_seconds=iv.data * k + 5)
        self.s_quality = Section("data_quality", stale_after_seconds=iv.data * k + 5)
        self.started_at = utcnow()
        self._db_thread: Optional[threading.Thread] = None
        self._last_db_tick: Optional[datetime] = None
        self._started = False
        self._start_lock = threading.Lock()
        self._stop = threading.Event()

    # ------------------------------------------------------------------ lifecycle
    def start(self) -> None:
        with self._start_lock:
            if self._started:
                return
            self._started = True
            self._db_thread = threading.Thread(target=self._db_loop, name="monitor-db", daemon=True)
            self._db_thread.start()
            if self.ibkr is not None and self.config.ibkr_enabled:
                self.ibkr.start()
            logger.info("monitoring service started (environment=%s)", self.config.environment)

    def stop(self) -> None:
        self._stop.set()
        if self.ibkr is not None:
            self.ibkr.stop()

    def _db_loop(self) -> None:
        last_data = 0.0
        while not self._stop.is_set():
            self.collect_health()
            if time.monotonic() - last_data >= self.config.intervals.data:
                last_data = time.monotonic()
                self.collect_data()
            self._last_db_tick = utcnow()
            self._stop.wait(self.config.intervals.health)

    # ------------------------------------------------------------------ collection
    def collect_health(self) -> None:
        cfg = self.config
        probes = {"sqlserver": tcp_probe(cfg.db_host, cfg.db_port) if cfg.db_host else
                  {"host": None, "port": None, "reachable": None, "latency_ms": None, "error": "not configured"},
                  "ibkr": tcp_probe(cfg.ibkr_host, cfg.ibkr_port) if cfg.ibkr_enabled else
                  {"host": cfg.ibkr_host, "port": cfg.ibkr_port, "reachable": None, "latency_ms": None,
                   "error": "IBKR monitoring disabled"}}
        net_status = HEALTHY if all(p["reachable"] for p in probes.values() if p["reachable"] is not None) \
            else DISCONNECTED
        self.s_network.update(net_status, probes)
        if self.db is None:
            self.s_database.update(UNKNOWN, error="database monitoring not configured (DB_HOST unset)")
            return
        try:
            info = self.db.health()
            status = HEALTHY if info.get("latency_ms", 0) < 2000 else DEGRADED
            self.s_database.update(status, info)
        except Exception as e:
            self.s_database.update(DISCONNECTED if "timeout" in str(e).lower() or "connect" in str(e).lower()
                                   else ERROR, error=redact_text(f"{type(e).__name__}: {e}")[:500])
            logger.warning("database monitor: %s", redact_text(str(e))[:300])

    def collect_data(self) -> None:
        if self.db is None:
            for s in (self.s_factors, self.s_market, self.s_quality):
                s.update(UNKNOWN, error="database monitoring not configured")
            return
        limit = self.config.max_rows
        try:
            counts = self.db.repo.table_counts()
            factors = self.db.repo.factor_summary(limit=limit)
            sources = self.db.repo.data_sources()
            self.s_factors.update(HEALTHY, {"counts": counts, "factors": factors, "sources": sources})
        except Exception as e:
            self.s_factors.update(ERROR, error=redact_text(f"{type(e).__name__}: {e}")[:500])
        try:
            rows = self.db.repo.market_data_freshness(limit=limit)
            self.s_market.update(HEALTHY, {"rows": rows})
        except Exception as e:
            self.s_market.update(ERROR, error=redact_text(f"{type(e).__name__}: {e}")[:500])
        try:
            quality = self.db.repo.data_quality(limit=limit)
            if quality is None:
                self.s_quality.update(UNKNOWN, error="no observation provenance recorded in this database")
            else:
                bad = sum(c["count"] for c in quality["counts"] if c["status"] != "valid")
                self.s_quality.update(DEGRADED if bad else HEALTHY, {**quality, "not_valid": bad})
        except Exception as e:
            self.s_quality.update(ERROR, error=redact_text(f"{type(e).__name__}: {e}")[:500])

    # ------------------------------------------------------------------ views
    def application(self) -> Dict[str, Any]:
        now = utcnow()
        db_alive = bool(self._db_thread and self._db_thread.is_alive())
        ibkr_alive = bool(self.ibkr and self.ibkr.thread_alive)
        status = HEALTHY if (db_alive or not self._started) else DEGRADED
        if not self._started:
            status = UNKNOWN
        data = {
            "environment": self.config.environment, "version": self.config.version,
            "python": platform.python_version(), "platform": platform.platform(terse=True),
            "pid": os.getpid(), "started_at": iso(self.started_at),
            "uptime_seconds": round((now - self.started_at).total_seconds()),
            "collectors": {"database": db_alive,
                           "ibkr": ibkr_alive if self.config.ibkr_enabled else None},
            "last_collection": iso(self._last_db_tick),
        }
        return make_view("application", status, data, now, stale_after=60)

    def database(self) -> Dict[str, Any]:
        return self.s_database.view()

    def network(self) -> Dict[str, Any]:
        return self.s_network.view()

    def ibkr_connection(self) -> Dict[str, Any]:
        if self.ibkr is None or not self.config.ibkr_enabled:
            return make_view("ibkr", UNKNOWN, {"enabled": False, "configured_mode": self.config.ibkr_account_mode},
                             None, stale_after=60, error="IBKR monitoring disabled")
        data = self.ibkr.connection_view()
        error = None
        if data["connection_failures"] and not data["connected"]:
            error = data["connection_failures"][0]["message"]
        updated = _as_utc(data["last_heartbeat"]) if data["connected"] else _as_utc(data["last_connect_attempt"])
        return make_view("ibkr", data["status"], data, updated,
                         stale_after=self.config.intervals.health * self.config.stale_factor + 15, error=error)

    def _ibkr_data_view(self, name: str, data: Dict[str, Any], interval: int) -> Dict[str, Any]:
        if self.ibkr is None or not self.config.ibkr_enabled:
            return make_view(name, UNKNOWN, None, None, 60, error="IBKR monitoring disabled")
        updated = _as_utc(data.get("updated_at"))
        connected = self.ibkr.connected
        if updated is None:
            status, error = (DEGRADED, "waiting for the first update from IB Gateway") if connected else \
                (DISCONNECTED, "IB Gateway not connected")
        else:
            status, error = (HEALTHY, None) if connected else (DISCONNECTED, "IB Gateway not connected - last "
                                                                           "known values shown")
        return make_view(name, status, data, updated, stale_after=interval * self.config.stale_factor + 15,
                         error=error)

    def account_summary(self) -> Dict[str, Any]:
        data = self.ibkr.account_view() if self.ibkr is not None else {}
        return self._ibkr_data_view("account_summary", data, self.config.intervals.account)

    def positions(self) -> Dict[str, Any]:
        data = self.ibkr.positions_view() if self.ibkr is not None else {}
        return self._ibkr_data_view("positions", data, self.config.intervals.positions)

    def orders(self) -> Dict[str, Any]:
        data = self.ibkr.orders_view() if self.ibkr is not None else {}
        return self._ibkr_data_view("open_orders", data, self.config.intervals.positions)

    def data_quality(self) -> Dict[str, Any]:
        """Observation quality (BI-034): counts per status / data type and the latest non-VALID observations
        with their reasons — failures visible without querying tables. Read-only, never alters calculations."""
        return self.s_quality.view()

    def market_data(self, limit: int = 200, stale_only: bool = False, query: Optional[str] = None) -> Dict[str, Any]:
        view = self.s_market.view()
        now = utcnow()
        rows_out: List[Dict[str, Any]] = []
        stale_count = 0
        for r in (view["data"] or {}).get("rows", []):
            last = _as_utc(r.get("last_date"))
            expected = _frequency_seconds(r.get("frequency"))
            threshold = max(expected * self.config.stale_factor, MAX_BAR_STALENESS_SECONDS) if expected \
                else MAX_BAR_STALENESS_SECONDS
            age = (now - last).total_seconds() if last else None
            state = "unknown" if age is None else ("stale" if age > threshold else "fresh")
            stale_count += state == "stale"
            row = {"factor": r.get("factor"), "source": r.get("source"), "frequency": r.get("frequency"),
                   "expected_seconds": expected, "entity_type": r.get("entity_type"),
                   "entity_id": r.get("entity_id"), "symbol": r.get("symbol"),
                   "value_count": r.get("value_count"), "last_timestamp": iso(last),
                   "age_seconds": None if age is None else round(age), "stale_after_seconds": threshold,
                   "state": state}
            if stale_only and state != "stale":
                continue
            if query and query.lower() not in " ".join(str(row.get(k) or "") for k in
                                                       ("factor", "symbol", "source", "entity_type")).lower():
                continue
            rows_out.append(row)
        total = len((view["data"] or {}).get("rows", []))
        if view["data"] is not None and view["status"] == HEALTHY:
            view["status"] = UNKNOWN if total == 0 else (HEALTHY if stale_count == 0 else
                                                         (STALE if stale_count == total else DEGRADED))
        errors = self.logs.recent(min_level="WARNING", component="market_data", limit=20)
        view["data"] = {
            "rows": rows_out[:limit], "total_series": total, "stale_series": stale_count,
            "sources": (self.s_factors.view()["data"] or {}).get("sources", []),
            "last_historical_retrieval": None,
            "last_historical_retrieval_note": "Unavailable: factor values store the observation time only, "
                                              "not when they were downloaded.",
            "last_live_update": None,
            "last_live_update_note": "Unavailable: the application does not record live market-data updates.",
            "recent_errors": errors,
        }
        return view

    def factors(self, limit: int = 200, query: Optional[str] = None) -> Dict[str, Any]:
        view = self.s_factors.view()
        now = utcnow()
        data = view["data"] or {}
        rows = []
        for f in data.get("factors", []):
            last = _as_utc(f.get("last_date"))
            row = dict(f)
            row["first_date"] = iso(_as_utc(f.get("first_date")))
            row["last_date"] = iso(last)
            row["age_seconds"] = None if last is None else round((now - last).total_seconds())
            row["calculated"] = f.get("source") == "calculated"
            if query and query.lower() not in " ".join(str(f.get(k) or "") for k in
                                                       ("name", "group", "subgroup", "source", "factor_type")).lower():
                continue
            rows.append(row)
        jobs = self.jobs.jobs()
        running = [j for j in jobs if j.get("status") == RUNNING]
        failed = [j for j in jobs if j.get("status") == FAILED]
        succeeded = [j for j in jobs if j.get("status") == "succeeded"]
        if view["data"] is not None and view["status"] == HEALTHY:
            if failed and (not succeeded or (failed[0].get("finished_at") or "") > (succeeded[0].get("finished_at") or "")):
                view["status"] = DEGRADED
            elif data.get("counts", {}).get("factor_values", 0) == 0:
                view["status"] = UNKNOWN
        view["data"] = {
            "counts": data.get("counts"),
            "factors": rows[:limit],
            "calculated_factors": sum(1 for r in rows if r["calculated"]),
            "running_jobs": running,
            "last_success": succeeded[0] if succeeded else None,
            "last_failure": failed[0] if failed else None,
            "recent_errors": self.logs.recent(min_level="WARNING", component="factors", limit=20),
        }
        return view

    def jobs_status(self, limit: int = 100) -> Dict[str, Any]:
        jobs = self.jobs.jobs()[:limit]
        status = UNKNOWN if not jobs else (DEGRADED if any(j.get("status") == FAILED for j in jobs[:5]) else HEALTHY)
        return make_view("jobs", status, {"jobs": jobs, "count": len(jobs)}, utcnow(), stale_after=60)

    def recent_logs(self, level: str = "INFO", component: Optional[str] = None,
                    since_minutes: Optional[int] = None, query: Optional[str] = None, limit: int = 200) -> Dict[str, Any]:
        records = self.logs.recent(min_level=level, component=component, since_minutes=since_minutes,
                                   query=query, limit=limit)
        return make_view("logs", HEALTHY, {"records": records, "count": len(records), "components": COMPONENTS,
                                           "levels": list(LEVELS), "sources": self.logs.sources()},
                         utcnow(), stale_after=60)

    def safe_config(self) -> Dict[str, Any]:
        data = self.config.safe_view()
        data["db_level_read_only"] = bool(self.db and self.db.db_level_read_only)
        data["dashboard"] = {"read_only": True, "authentication": "none (network-restricted)",
                             "mutating_http_methods": "rejected (405)"}
        return make_view("settings", HEALTHY, redact(data), utcnow(), stale_after=3600)

    def overview(self) -> Dict[str, Any]:
        app, db, ib = self.application(), self.database(), self.ibkr_connection()
        acct = self.account_summary()
        md, fac = self.market_data(limit=0), self.factors(limit=0)
        errors = self.logs.recent(min_level="ERROR", limit=8)
        core = [app["status"], db["status"]] + ([ib["status"]] if self.config.ibkr_enabled else [])
        overall = worst(*core)
        if overall == HEALTHY and (md["status"] in (STALE, DEGRADED) or fac["status"] in (DEGRADED,)):
            overall = DEGRADED
        if overall == STALE:
            overall = DEGRADED

        def card(view, summary):
            return {"status": view["status"], "updated_at": view["updated_at"], "age_seconds": view["age_seconds"],
                    "stale": view["stale"], "error": view["error"], "summary": summary}

        ib_data = ib["data"] or {}
        acct_values = (acct["data"] or {}).get("values", {}) if acct["data"] else {}
        nl = acct_values.get("net_liquidation", {}) if acct_values else {}
        return make_view("overview", overall, {
            "application": card(app, {"uptime_seconds": app["data"]["uptime_seconds"], "version": app["data"]["version"]}),
            "ibkr": card(ib, {"connected": ib_data.get("connected"), "mode": ib_data.get("detected_mode")
                              or ib_data.get("configured_mode"), "host": ib_data.get("host"), "port": ib_data.get("port")}),
            "database": card(db, {"latency_ms": (db["data"] or {}).get("latency_ms"),
                                  "database": (db["data"] or {}).get("database"),
                                  "read_only_login": (db["data"] or {}).get("db_level_read_only")}),
            "account": card(acct, {"net_liquidation": nl.get("value"), "currency": nl.get("currency"),
                                   "available": bool(nl.get("available"))}),
            "market_data": card(md, {"series": md["data"]["total_series"], "stale": md["data"]["stale_series"]}),
            "factors": card(fac, {"factor_values": ((fac["data"] or {}).get("counts") or {}).get("factor_values"),
                                  "running_jobs": len(fac["data"]["running_jobs"]),
                                  "last_failure": (fac["data"]["last_failure"] or {}).get("finished_at")}),
            "errors": {"status": ERROR if errors else HEALTHY, "records": errors},
        }, utcnow(), stale_after=60)

    def connections(self) -> Dict[str, Any]:
        return make_view("connections", worst(self.database()["status"], self.ibkr_connection()["status"]
                                              if self.config.ibkr_enabled else HEALTHY), {
            "application": self.application(), "database": self.database(), "network": self.network(),
            "ibkr": self.ibkr_connection(),
            "flask": {"status": HEALTHY, "detail": "this response was served by the dashboard process"},
            "containers": {"status": UNKNOWN, "detail": "Unavailable: the Docker API is intentionally not exposed "
                                                        "to the dashboard; see network reachability and "
                                                        "application-level checks instead."},
        }, utcnow(), stale_after=60)


_service: Optional[MonitoringService] = None
_service_lock = threading.Lock()


def build_monitoring_service(config: Optional[MonitoringConfig] = None) -> MonitoringService:
    from src.application.services.monitoring.ibkr_monitor import IBKRMonitor

    config = config or MonitoringConfig.from_env()
    ring = RingBufferHandler(capacity=config.log_buffer_size, process_name="dashboard")
    logging.getLogger().addHandler(ring)
    if logging.getLogger().level in (logging.NOTSET, logging.WARNING):
        logging.getLogger().setLevel(logging.INFO)
    try:
        db = DatabaseMonitor.from_environment()
    except Exception as e:
        logger.error("database monitor unavailable: %s", redact_text(str(e)))
        db = None
    ibkr = IBKRMonitor(config.ibkr_host, config.ibkr_port, config.ibkr_client_id, config.ibkr_account_mode,
                       account_interval=config.intervals.account, positions_interval=config.intervals.positions,
                       heartbeat_interval=config.intervals.health) if config.ibkr_enabled else None
    return MonitoringService(config, db=db, ibkr=ibkr, ring=ring)


def get_monitoring_service() -> MonitoringService:
    global _service
    with _service_lock:
        if _service is None:
            _service = build_monitoring_service()
        return _service


def set_monitoring_service(service: Optional[MonitoringService]) -> None:
    """Tests / embedding: inject a service instance."""
    global _service
    with _service_lock:
        _service = service
