"""
Log collection for the dashboard log viewer (read-only).

* ``install_monitoring_log_handler()`` — called by application processes (ProjectManager,
  backtest runner): appends WARNING+ / INFO records as JSON lines to
  ``<MONITOR_STATE_DIR>/logs/app-<pid>.jsonl`` (rotating, bounded), redacted at write time.
* ``RingBufferHandler`` — the dashboard process' own recent records (in memory).
* ``LogReader`` — merges both, newest first, with severity / component / time / text filters.
  It only reads files it created itself under the state directory; no path comes from a request.
"""

import glob
import json
import logging
import os
import socket
import threading
from collections import deque
from datetime import datetime, timedelta, timezone
from logging.handlers import RotatingFileHandler
from typing import Any, Deque, Dict, Iterable, List, Optional

from src.application.services.monitoring.redaction import redact_text

LEVELS = {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}
COMPONENTS = ("ibkr", "database", "market_data", "factors", "engine", "web", "monitoring", "application")
_COMPONENT_RULES = (
    ("monitoring.ibkr", "ibkr"), ("monitoring.database", "database"), ("monitoring", "monitoring"),
    ("ibtwsclient", "ibkr"), ("interactivebrokers", "ibkr"), ("ibkr", "ibkr"), ("ibapi", "ibkr"),
    ("contractresolver", "ibkr"),
    ("sqlalchemy", "database"), ("pyodbc", "database"), ("databaseservice", "database"),
    ("database", "database"), ("repository", "database"),
    ("marketdata", "market_data"), ("market_data", "market_data"), ("history", "market_data"),
    ("factor", "factors"),
    ("misbuffet", "engine"), ("engine", "engine"), ("backtest", "engine"), ("algorithm", "engine"),
    ("werkzeug", "web"), ("gunicorn", "web"), ("flask", "web"),
)
_IBKR_MESSAGE_HINTS = ("tws", "ib gateway", "ibkr", "error 502", "error 504", "error 1100", "error 162")
_DB_MESSAGE_HINTS = ("odbc", "sql server", "pyodbc", "operationalerror", "login failed")
_MARKET_DATA_HINTS = ("historical data", "market data", "no data", "bars")


def classify(logger_name: str, message: str = "") -> str:
    name = (logger_name or "").lower()
    for prefix, component in _COMPONENT_RULES:
        if prefix in name:
            return component
    msg = (message or "").lower()
    if any(h in msg for h in _IBKR_MESSAGE_HINTS):
        return "ibkr"
    if any(h in msg for h in _DB_MESSAGE_HINTS):
        return "database"
    if any(h in msg for h in _MARKET_DATA_HINTS):
        return "market_data"
    return "application"


def _record_to_dict(record: logging.LogRecord, process_name: str) -> Dict[str, Any]:
    try:
        message = record.getMessage()
    except Exception:  # malformed %-args must never break logging
        message = str(record.msg)
    if record.exc_info and record.exc_info[0] is not None:
        message = f"{message} [{record.exc_info[0].__name__}: {record.exc_info[1]}]"
    message = redact_text(message)[:2000]
    return {
        "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(timespec="milliseconds"),
        "level": record.levelname,
        "logger": record.name,
        "component": classify(record.name, message),
        "message": message,
        "process": process_name,
        "pid": record.process,
    }


class RingBufferHandler(logging.Handler):
    """Keeps the last ``capacity`` records of this process in memory."""

    def __init__(self, capacity: int = 2000, level: int = logging.INFO, process_name: str = "dashboard"):
        super().__init__(level)
        self.records: Deque[Dict[str, Any]] = deque(maxlen=capacity)
        self.process_name = process_name
        self._buffer_lock = threading.Lock()
        self.addFilter(lambda record: _not_noise(record))

    def emit(self, record: logging.LogRecord) -> None:
        try:
            item = _record_to_dict(record, self.process_name)
            with self._buffer_lock:
                self.records.append(item)
        except Exception:
            self.handleError(record)

    def snapshot(self) -> List[Dict[str, Any]]:
        with self._buffer_lock:
            return list(self.records)


# ibapi logs every request / answer at INFO ("REQUEST reqAccountSummary {...}", "ANSWER ..."): useful
# for protocol debugging, but it would flood the dashboard (and echo account messages). Only its
# warnings and errors are kept for monitoring.
NOISY_LOGGERS = ("ibapi",)


def _not_noise(record: logging.LogRecord) -> bool:
    return not (record.levelno < logging.WARNING and record.name.split(".")[0] in NOISY_LOGGERS)


class JsonLinesHandler(RotatingFileHandler):
    def __init__(self, path: str, process_name: str, max_bytes: int = 5_000_000, backups: int = 2):
        super().__init__(path, maxBytes=max_bytes, backupCount=backups, encoding="utf-8", delay=True)
        self.process_name = process_name
        self.addFilter(_not_noise)

    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(_record_to_dict(record, self.process_name), default=str)


_installed_lock = threading.Lock()
_installed: Dict[str, logging.Handler] = {}


def install_monitoring_log_handler(process_name: Optional[str] = None, level: int = logging.INFO,
                                   state_dir: Optional[str] = None) -> Optional[logging.Handler]:
    """Attach (once per process) a JSON-lines file handler to the root logger. Never raises."""
    state_dir = state_dir or os.getenv("MONITOR_STATE_DIR") or ".monitor"
    if (os.getenv("MONITOR_LOG_FILE_ENABLED") or "true").strip().lower() in ("0", "false", "no", "off"):
        return None
    try:
        with _installed_lock:
            key = os.path.abspath(state_dir)
            if key in _installed:
                return _installed[key]
            log_dir = os.path.join(state_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)
            name = process_name or os.path.basename(os.getenv("MONITOR_PROCESS_NAME", "") or "app")
            path = os.path.join(log_dir, f"{name}-{socket.gethostname()}-{os.getpid()}.jsonl")
            handler = JsonLinesHandler(path, process_name=name)
            handler.setLevel(level)
            root = logging.getLogger()
            root.addHandler(handler)
            if root.level > level or root.level == logging.NOTSET:
                root.setLevel(level)
            _installed[key] = handler
            return handler
    except Exception:
        return None


def _parse_ts(value: str) -> Optional[datetime]:
    try:
        ts = datetime.fromisoformat(value)
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


class LogReader:

    def __init__(self, state_dir: str, ring: Optional[RingBufferHandler] = None,
                 tail_bytes: int = 1_000_000, max_files: int = 20):
        self.log_dir = os.path.join(state_dir, "logs")
        self.ring = ring
        self.tail_bytes = tail_bytes
        self.max_files = max_files

    def _file_records(self) -> Iterable[Dict[str, Any]]:
        pattern = os.path.join(self.log_dir, "*.jsonl*")
        files = sorted(glob.glob(pattern), key=lambda p: os.path.getmtime(p), reverse=True)[: self.max_files]
        for path in files:
            try:
                size = os.path.getsize(path)
                with open(path, "rb") as f:
                    if size > self.tail_bytes:
                        f.seek(size - self.tail_bytes)
                        f.readline()                       # drop the partial first line
                    lines = f.read().decode("utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for line in lines:
                try:
                    item = json.loads(line)
                except ValueError:
                    continue
                if isinstance(item, dict) and "ts" in item:
                    yield item

    def sources(self) -> List[Dict[str, Any]]:
        files = sorted(glob.glob(os.path.join(self.log_dir, "*.jsonl")))
        out = []
        for path in files[: self.max_files]:
            try:
                out.append({"file": os.path.basename(path), "bytes": os.path.getsize(path),
                            "modified": datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
                            .isoformat(timespec="seconds")})
            except OSError:
                continue
        return out

    def recent(self, min_level: str = "INFO", component: Optional[str] = None,
               since_minutes: Optional[int] = None, query: Optional[str] = None,
               limit: int = 200) -> List[Dict[str, Any]]:
        threshold = LEVELS.get((min_level or "INFO").upper(), 20)
        since = datetime.now(timezone.utc) - timedelta(minutes=since_minutes) if since_minutes else None
        q = (query or "").lower()
        items = list(self._file_records())
        if self.ring is not None:
            items.extend(self.ring.snapshot())
        out = []
        seen = set()
        for item in items:
            if LEVELS.get(str(item.get("level", "")).upper(), 0) < threshold:
                continue
            if component and item.get("component") != component:
                continue
            ts = _parse_ts(item.get("ts"))
            if since and (ts is None or ts < since):
                continue
            message = redact_text(str(item.get("message", "")))      # re-redact on read
            if q and q not in message.lower() and q not in str(item.get("logger", "")).lower():
                continue
            key = (item.get("ts"), item.get("pid"), message[:120])
            if key in seen:
                continue
            seen.add(key)
            out.append({"ts": item.get("ts"), "level": item.get("level"), "component": item.get("component"),
                        "logger": item.get("logger"), "process": item.get("process"), "message": message})
        out.sort(key=lambda r: r.get("ts") or "", reverse=True)
        return out[:limit]
