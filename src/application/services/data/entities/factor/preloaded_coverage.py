"""
Ranges of raw bar series that were loaded IN FULL from the data provider before a backtest (BacktestDataPreloadService).

Inside a registered range every bar the provider has is already stored, so a bar that is still missing there does
not exist (no trade in that window, a halt, ...): asking IBKR for it again at every engine step only costs time.
FactorValueResolutionService consults ``covers`` and then serves the latest CLOSED stored bar instead (still no
look-ahead). Process-wide, keyed by database ids (factor id, entity id); ``clear`` forgets everything.
"""

from __future__ import annotations

import threading
from datetime import datetime
from typing import Dict, List, Tuple

_lock = threading.Lock()
_ranges: Dict[Tuple[int, int], List[Tuple[datetime, datetime]]] = {}


def register(factor_id: int, entity_id: int, start: datetime, end: datetime) -> None:
    with _lock:
        _ranges.setdefault((int(factor_id), int(entity_id)), []).append((start, end))


def covers(factor_id: int, entity_id: int, when: datetime) -> bool:
    with _lock:
        return any(start <= when <= end for start, end in _ranges.get((int(factor_id), int(entity_id)), ()))


def extend(through: datetime) -> int:
    """Live: every registered series is complete up to ``through`` as well (its newly closed bars were just imported).
    Returns the number of series extended."""
    with _lock:
        for ranges in _ranges.values():
            start = min(s for s, _ in ranges)
            if max(e for _, e in ranges) < through:
                ranges.append((start, through))
        return len(_ranges)


def clear() -> None:
    with _lock:
        _ranges.clear()


def registered() -> Dict[Tuple[int, int], List[Tuple[datetime, datetime]]]:
    with _lock:
        return {k: list(v) for k, v in _ranges.items()}
