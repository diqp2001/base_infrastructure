"""
STMProgressTracker — thread-safe progress of a Spatio-Temporal Momentum run,
fed by the trading cycle (bars, retrains) and the training loop (epoch logs).

With ``persist_path`` the tracker also writes its snapshot to a JSON file
(atomically, throttled), so a dashboard in ANOTHER process — the Flask app —
can follow a run started from main.py / VS Code.
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, Optional


class STMProgressTracker:

    def __init__(self, max_log_lines: int = 300, persist_path: Optional[str] = None,
                 min_write_interval: float = 1.0):
        self._lock = threading.Lock()
        self._log = deque(maxlen=max_log_lines)
        self.persist_path = persist_path
        self.min_write_interval = min_write_interval
        self._last_write = 0.0
        self.reset(persist=False)   # never overwrite a previous run's file until a run starts

    def reset(self, bars_total: Optional[int] = None, mode: str = "", persist: bool = True) -> None:
        with self._lock:
            self._state: Dict[str, Any] = {
                "status": "idle",          # idle | running | completed | failed
                "mode": mode,
                "phase": "",
                "started_at": None,
                "finished_at": None,
                "bars_done": 0,
                "bars_total": bars_total,
                "current_time": None,
                "current_session": None,
                "retrainings": [],
                "trained_sessions": 0,
                "last_epoch": None,
                "portfolio_value": None,
                "error": None,
            }
            self._log.clear()
            self.report = None
        if persist:
            self._persist(force=True)

    # ------------------------------------------------------------------ writers

    def start(self, mode: str, bars_total: Optional[int] = None) -> None:
        self.reset(bars_total=bars_total, mode=mode, persist=False)
        with self._lock:
            self._state.update(status="running", phase="starting", started_at=datetime.now().isoformat())
        self._persist(force=True)

    def phase(self, name: str) -> None:
        with self._lock:
            self._state["phase"] = name
        self.log(f"[phase] {name}")

    def log(self, message: str) -> None:
        line = f"{datetime.now().strftime('%H:%M:%S')}  {message}"
        with self._lock:
            self._log.append(line)
            if message.startswith("epoch "):
                self._state["last_epoch"] = message
        self._persist()

    def on_step(self, result, portfolio_value: Optional[float] = None) -> None:
        with self._lock:
            s = self._state
            s["bars_done"] += 1
            s["current_time"] = str(getattr(result, "time", "") or "")
            session = getattr(result, "session", None)
            s["current_session"] = str(session.date()) if session is not None else None
            if getattr(result, "scores", None):
                s["trained_sessions"] += 1
            if getattr(result, "retrained", False):
                s["retrainings"].append({"session": s["current_session"],
                                         "artifact_id": getattr(result, "artifact_id", None)})
            if portfolio_value is not None:
                s["portfolio_value"] = float(portfolio_value)
        self._persist()

    def complete(self, report=None) -> None:
        with self._lock:
            self.report = report
            self._state.update(status="completed", phase="done", finished_at=datetime.now().isoformat())
        self.log("[run] completed")
        self._persist(force=True)

    def fail(self, error: str) -> None:
        with self._lock:
            self._state.update(status="failed", error=error, finished_at=datetime.now().isoformat())
        self.log(f"[run] failed: {error}")
        self._persist(force=True)

    # ------------------------------------------------------------------ readers

    @property
    def status(self) -> str:
        with self._lock:
            return self._state["status"]

    # ------------------------------------------------------------------ persistence

    def _persist(self, force: bool = False) -> None:
        if not self.persist_path:
            return
        now = time.time()
        if not force and now - self._last_write < self.min_write_interval:
            return
        self._last_write = now
        snap = self.snapshot(log_lines=200)
        snap["updated_at"] = datetime.now().isoformat()
        snap["pid"] = os.getpid()
        try:
            os.makedirs(os.path.dirname(self.persist_path) or ".", exist_ok=True)
            tmp = f"{self.persist_path}.{os.getpid()}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(snap, f, default=str)
            os.replace(tmp, self.persist_path)
        except OSError:
            pass                                   # progress display must never break a run

    @staticmethod
    def read_snapshot(path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None

    def snapshot(self, log_lines: int = 60) -> Dict[str, Any]:
        with self._lock:
            state = dict(self._state)
            state["retrainings"] = list(self._state["retrainings"])
            state["log"] = list(self._log)[-log_lines:]
            state["has_report"] = self.report is not None
            total = state.get("bars_total")
            state["percent"] = (min(100.0, 100.0 * state["bars_done"] / total) if total else None)
            return state
