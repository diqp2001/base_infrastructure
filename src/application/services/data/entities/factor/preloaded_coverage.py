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
from typing import Dict, Iterable, List, Optional, Tuple

_lock = threading.Lock()
_ranges: Dict[Tuple[int, int], List[Tuple[datetime, datetime]]] = {}


def register(factor_id: int, entity_id: int, start: datetime, end: datetime) -> None:
    with _lock:
        _ranges.setdefault((int(factor_id), int(entity_id)), []).append((start, end))


def covers(factor_id: int, entity_id: int, when: datetime) -> bool:
    with _lock:
        return any(start <= when <= end for start, end in _ranges.get((int(factor_id), int(entity_id)), ()))


def extend(through: datetime, entity_ids: Optional[Iterable[int]] = None) -> int:
    """Live: the registered series are complete up to ``through`` as well (their newly closed bars were just
    imported). ``entity_ids``: only those entities' series (P.08.07: a ticker whose import failed keeps its coverage
    end, so its missing bar is still asked for instead of being served from an older stored bar); None = all.
    Returns the number of series extended."""
    only = None if entity_ids is None else {int(e) for e in entity_ids}
    extended = 0
    with _lock:
        for (factor_id, entity_id), ranges in _ranges.items():
            if only is not None and entity_id not in only:
                continue
            start = min(s for s, _ in ranges)
            if max(e for _, e in ranges) < through:
                ranges.append((start, through))
            extended += 1
        return extended


def clear() -> None:
    with _lock:
        _ranges.clear()


def registered() -> Dict[Tuple[int, int], List[Tuple[datetime, datetime]]]:
    with _lock:
        return {k: list(v) for k, v in _ranges.items()}
