"""
Background job status for the dashboard (smallest tracking mechanism, read-only for the UI).

* ``JobRecorder`` — used by the application processes (BaseBacktestRunner.run_backtest) to write
  ``<MONITOR_STATE_DIR>/jobs/<job_id>.json`` at start / end. Recording never raises and never
  changes the job's behaviour.
* ``JobReader`` — used by the dashboard: lists those files, plus the ``progress.json`` files that
  project managers already write under ``<MONITOR_RESULTS_DIR>/<project>/`` (e.g. the
  Spatio-Temporal Momentum projects), when present.
"""

import glob
import json
import os
import socket
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.application.services.monitoring.redaction import redact, redact_text

RUNNING, SUCCEEDED, FAILED = "running", "succeeded", "failed"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JobRecorder:

    def __init__(self, kind: str, name: str, state_dir: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        self.state_dir = state_dir or os.getenv("MONITOR_STATE_DIR") or ".monitor"
        self.job_id = f"{datetime.now(timezone.utc):%Y%m%dT%H%M%S}-{kind}-{uuid.uuid4().hex[:6]}"
        self._t0 = time.monotonic()
        self.record = {
            "job_id": self.job_id, "kind": kind, "name": name, "status": RUNNING,
            "started_at": _now(), "finished_at": None, "duration_seconds": None,
            "host": socket.gethostname(), "pid": os.getpid(), "error": None,
            "details": redact(details or {}),
        }

    @property
    def path(self) -> str:
        return os.path.join(self.state_dir, "jobs", f"{self.job_id}.json")

    def _write(self) -> None:
        try:
            os.makedirs(os.path.dirname(self.path), exist_ok=True)
            tmp = f"{self.path}.tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.record, f, default=str)
            os.replace(tmp, self.path)
        except Exception:
            pass   # monitoring must never interfere with the job

    def start(self) -> "JobRecorder":
        self._write()
        return self

    def finish(self, success: bool, error: Optional[str] = None, **details: Any) -> None:
        self.record.update(status=SUCCEEDED if success else FAILED, finished_at=_now(),
                           duration_seconds=round(time.monotonic() - self._t0, 2),
                           error=redact_text(str(error))[:2000] if error else None)
        if details:
            self.record["details"].update(redact(details))
        self._write()


class JobReader:

    def __init__(self, state_dir: str, results_dir: str, max_jobs: int = 200):
        self.jobs_dir = os.path.join(state_dir, "jobs")
        self.results_dir = results_dir
        self.max_jobs = max_jobs

    def jobs(self) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        files = sorted(glob.glob(os.path.join(self.jobs_dir, "*.json")), reverse=True)[: self.max_jobs]
        for path in files:
            try:
                with open(path, encoding="utf-8") as f:
                    item = json.load(f)
            except (OSError, ValueError):
                continue
            if isinstance(item, dict):
                item = redact(item)
                item["source"] = "job_tracker"
                item["alive"] = _pid_alive(item) if item.get("status") == RUNNING else None
                out.append(item)
        out.extend(self._project_progress())
        out.sort(key=lambda j: j.get("started_at") or j.get("updated_at") or "", reverse=True)
        return out

    def _project_progress(self) -> List[Dict[str, Any]]:
        out = []
        for path in sorted(glob.glob(os.path.join(self.results_dir, "*", "progress.json")))[:50]:
            try:
                with open(path, encoding="utf-8") as f:
                    snap = json.load(f)
            except (OSError, ValueError):
                continue
            if not isinstance(snap, dict):
                continue
            status = str(snap.get("status") or "unknown").lower()
            out.append(redact({
                "job_id": f"progress:{os.path.basename(os.path.dirname(path))}",
                "kind": "project_progress", "name": os.path.basename(os.path.dirname(path)),
                "status": {"completed": SUCCEEDED, "failed": FAILED, "running": RUNNING}.get(status, status),
                "started_at": snap.get("started_at"), "updated_at": snap.get("updated_at"),
                "finished_at": None, "duration_seconds": None,
                "error": snap.get("error"),
                "details": {k: snap.get(k) for k in ("phase", "percent", "bars_done", "bars_total", "mode")
                            if k in snap},
                "source": "progress.json",
            }))
        return out


def _pid_alive(item: Dict[str, Any]) -> Optional[bool]:
    """Only meaningful when the dashboard runs on the same host as the job (same container)."""
    if item.get("host") != socket.gethostname():
        return None
    try:
        os.kill(int(item.get("pid")), 0)
        return True
    except (OSError, TypeError, ValueError):
        return False
