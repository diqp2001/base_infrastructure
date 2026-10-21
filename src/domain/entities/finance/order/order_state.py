"""
Order status transitions (BI-021): one rule for every order-status model (persistence enum, framework enum,
broker strings). Status updates can arrive late, twice or out of order (IBKR orderStatus callbacks); only an update
that moves the order FORWARD is applied:

    SUBMITTED -> PARTIALLY_FILLED (filled grows) -> FILLED | CANCELLED | REJECTED / INVALID / EXPIRED (terminal)

- a terminal status is final: nothing after it is applied;
- the cumulative filled quantity never decreases; within PARTIALLY_FILLED it must grow;
- a CANCELLED order may carry a partial fill (cancel of the remainder).
States are given by name, case-insensitive; the spellings of the different enums map to the same stage.
"""

from __future__ import annotations

_STAGE = {
    "NEW": 0, "PENDING": 0, "NONE": 0,
    "SUBMITTED": 1,
    "PARTIALLY_FILLED": 2, "PARTIAL_FILLED": 2,
    "FILLED": 3, "CANCELED": 3, "CANCELLED": 3, "REJECTED": 3, "INVALID": 3, "EXPIRED": 3,
}
TERMINAL = 3


def stage(status) -> int:
    name = str(getattr(status, "name", status)).upper()
    if name not in _STAGE:
        raise ValueError(f"unknown order status {status!r}")
    return _STAGE[name]


def is_terminal(status) -> bool:
    return stage(status) == TERMINAL


def advances(previous, previous_filled: float, new, new_filled: float) -> bool:
    """True when (new, new_filled) is a forward move from (previous, previous_filled); previous None = first."""
    if previous is None:
        return True
    old, nxt = stage(previous), stage(new)
    if old == TERMINAL or new_filled < previous_filled:
        return False
    if nxt > old:
        return True
    return nxt == old == stage("PARTIALLY_FILLED") and new_filled > previous_filled
