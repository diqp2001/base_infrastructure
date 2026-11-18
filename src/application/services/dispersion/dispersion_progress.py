"""
Progress of the latest model-filtered dispersion run, for the status page (/dispersion-stm/): <results_dir>/status.json.

{state: running | done | failed, step: prices | backtest, started_at, updated_at, message, run_folder,
 months_done, months_total, settled, cumulative_pnl_original, cumulative_pnl_filtered, last_month, log_tail}
Written atomically (temp file + replace) so a reader never sees half a file.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict, Optional

LOG_TAIL = 40


def status_path(results_dir: str) -> str:
    return os.path.join(results_dir, "status.json")


def read_status(results_dir: str) -> Optional[Dict[str, Any]]:
    try:
        with open(status_path(results_dir), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


class RunStatus:

    def __init__(self, results_dir: str, step: str, on_month=None):
        self.results_dir = results_dir
        self.on_month = on_month          # called with the cycle after each settled month (partial report)
        self.data: Dict[str, Any] = {"state": "running", "step": step,
                                     "started_at": datetime.now().isoformat(timespec="seconds"), "log_tail": []}
        self.write()

    def update(self, **fields) -> None:
        self.data.update(fields)
        self.write()

    def log(self, line: str) -> None:
        tail = self.data.setdefault("log_tail", [])
        tail.append(f"{datetime.now().strftime('%H:%M:%S')} {line}")
        del tail[:-LOG_TAIL]
        self.write()

    def write(self) -> None:
        self.data["updated_at"] = datetime.now().isoformat(timespec="seconds")
        os.makedirs(self.results_dir, exist_ok=True)
        path = status_path(self.results_dir)
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=1, default=str)
        os.replace(tmp, path)

    def on_step(self, cycle, result, portfolio_value=None) -> None:
        """After an engine step: months opened / settled, cumulative P&L of A and B, the portfolio value."""
        settled = [m for m in cycle.months if m.complete]
        fields = {"months_done": sum(1 for m in cycle.months if m.trade is not None or m.problem),
                  "settled": len(settled),
                  "cumulative_pnl_original": sum(m.original.pnl for m in settled),
                  "cumulative_pnl_filtered": sum(m.filtered.pnl for m in settled),
                  "session": str(result.session) if result.session else None,
                  "portfolio_value": float(portfolio_value) if portfolio_value is not None else None}
        if result.opened is not None or result.settled is not None:
            fields["last_month"] = str((result.opened or result.settled).opened)
        if self.on_month is not None and result.settled is not None:
            self.on_month(cycle)
        self.update(**fields)
