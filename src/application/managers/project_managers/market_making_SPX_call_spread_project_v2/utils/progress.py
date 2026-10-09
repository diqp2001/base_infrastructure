"""
Run progress of the SPX call spread v2 project, persisted to ``progress.json``.

Same idea as STMProgressTracker: the project manager and the algorithm update
it, and with ``persist_path`` every update is written atomically to JSON, so a
run started anywhere (main.py, VS Code) can be followed by reading the file.
"""

import json
import os
import threading
from datetime import datetime
from typing import Any, Dict, List, Optional


class MMProgressTracker:

    def __init__(self, persist_path: Optional[str] = None, max_log_lines: int = 300):
        self.persist_path = persist_path
        self.max_log_lines = max_log_lines
        self._lock = threading.Lock()
        self._reset(None, "")

    def _reset(self, bars_total: Optional[int], mode: str) -> None:
        self.mode = mode
        self.status = "idle"
        self.phase_name = ""
        self.bars_total = bars_total
        self.bars_done = 0
        self.trades = 0
        self.hedges = 0
        self.errors = 0
        self.portfolio_value: Optional[float] = None
        self.last_step: Optional[Dict[str, Any]] = None
        self.log_lines: List[str] = []
        self.error: Optional[str] = None
        self.summary: Optional[Dict[str, Any]] = None
        self.started_at: Optional[str] = None

    # ------------------------------------------------------------------ updates
    def start(self, mode: str, bars_total: Optional[int] = None) -> None:
        self._reset(bars_total, mode)
        self.status = "running"
        self.started_at = datetime.now().isoformat(timespec="seconds")
        self._persist()

    def phase(self, name: str) -> None:
        self.phase_name = name
        self.log(name)

    def log(self, message: str) -> None:
        with self._lock:
            self.log_lines.append(f"{datetime.now():%H:%M:%S} {message}")
            del self.log_lines[:-self.max_log_lines]
        self._persist()

    def on_step(self, result, portfolio_value: Optional[float] = None) -> None:
        self.bars_done += 1
        self.trades += int(result.option_order is not None)
        self.hedges += int(result.hedge_order is not None)
        self.errors += int(result.error is not None)
        self.portfolio_value = portfolio_value
        self.last_step = result.summary()
        self._persist()

    def complete(self, summary: Optional[Dict[str, Any]] = None) -> None:
        self.status = "completed"
        self.summary = summary
        self._persist()

    def fail(self, error: str) -> None:
        self.status = "failed"
        self.error = error
        self._persist()

    # ------------------------------------------------------------------ persistence
    def snapshot(self) -> Dict[str, Any]:
        percent = None
        if self.bars_total:
            percent = round(100.0 * min(self.bars_done, self.bars_total) / self.bars_total, 1)
        return {
            'status': self.status, 'mode': self.mode, 'phase': self.phase_name,
            'bars_done': self.bars_done, 'bars_total': self.bars_total, 'percent': percent,
            'option_entries': self.trades, 'hedges': self.hedges, 'step_errors': self.errors,
            'portfolio_value': self.portfolio_value, 'last_step': self.last_step,
            'error': self.error, 'summary': self.summary, 'started_at': self.started_at,
            'updated_at': datetime.now().isoformat(timespec="seconds"),
            'log': list(self.log_lines[-60:]),
        }

    def _persist(self) -> None:
        if not self.persist_path:
            return
        with self._lock:
            snap = self.snapshot()
            try:
                os.makedirs(os.path.dirname(self.persist_path) or ".", exist_ok=True)
                tmp = f"{self.persist_path}.{os.getpid()}.tmp"
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(snap, f, default=str)
                os.replace(tmp, self.persist_path)
            except OSError:
                pass

    @staticmethod
    def read_snapshot(path: str) -> Optional[Dict[str, Any]]:
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (OSError, ValueError):
            return None
