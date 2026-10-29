"""
Trading controls (P.05): who may send new orders. Pure; no I/O.

A control applies to a scope — GLOBAL (target '*': the kill switch), ACCOUNT (an account id) or STRATEGY (a strategy /
portfolio name) — and has a mode:
    enabled      orders allowed (subject to every risk limit)
    reduce_only  only orders that reduce an existing position without flipping it (used to liquidate under control)
    disabled     no order at all
Controls are append-only: the latest row per (scope, target) is in force, earlier rows are the audit trail. For an
order, the MOST restrictive mode among the matching scopes applies; a scope without any row is enabled.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Iterable, List, Optional, Tuple


class ControlScope(str, Enum):
    GLOBAL = "global"
    ACCOUNT = "account"
    STRATEGY = "strategy"


class ControlMode(str, Enum):
    ENABLED = "enabled"
    REDUCE_ONLY = "reduce_only"
    DISABLED = "disabled"


_RANK = {ControlMode.ENABLED: 0, ControlMode.REDUCE_ONLY: 1, ControlMode.DISABLED: 2}
GLOBAL_TARGET = "*"


@dataclass
class TradingControl:
    scope: ControlScope
    target: str
    mode: ControlMode
    reason: str
    changed_by: str
    changed_at: datetime
    id: Optional[int] = None

    def __post_init__(self):
        if not str(self.reason or "").strip():
            raise ValueError("a trading control change needs a reason")
        if not str(self.changed_by or "").strip():
            raise ValueError("a trading control change needs who made it")
        if self.scope is ControlScope.GLOBAL:
            self.target = GLOBAL_TARGET
        elif not str(self.target or "").strip():
            raise ValueError(f"a {self.scope.value} control needs a target")


def effective_mode(controls: Iterable[TradingControl], account: Optional[str],
                   strategy: Optional[str]) -> Tuple[ControlMode, List[str]]:
    """Most restrictive mode among the latest controls matching (global, account, strategy), with the reasons of
    every non-enabled one."""
    latest = {}
    for c in controls:
        k = (c.scope, c.target)
        if k not in latest or (c.changed_at, c.id or 0) >= (latest[k].changed_at, latest[k].id or 0):
            latest[k] = c
    applicable = [latest.get((ControlScope.GLOBAL, GLOBAL_TARGET))]
    if account:
        applicable.append(latest.get((ControlScope.ACCOUNT, account)))
    if strategy:
        applicable.append(latest.get((ControlScope.STRATEGY, strategy)))
    mode, reasons = ControlMode.ENABLED, []
    for c in applicable:
        if c is None or c.mode is ControlMode.ENABLED:
            continue
        reasons.append(f"{c.scope.value} {c.target}: {c.mode.value} ({c.reason}; {c.changed_by}, {c.changed_at})")
        if _RANK[c.mode] > _RANK[mode]:
            mode = c.mode
    return mode, reasons


def reduces_position(position_before: float, quantity: float) -> bool:
    """True when the order moves the position toward zero without crossing it."""
    after = position_before + quantity
    if position_before == 0 or quantity == 0:
        return False
    return abs(after) < abs(position_before) and (after == 0 or (after > 0) == (position_before > 0))
