"""
src/application/services/data/entities/factor/exceptions.py

Application-layer exceptions for the factor resolution pipeline.

These are *raised* (not just logged-and-returned-None) so that callers can
distinguish structural errors — such as a cyclic dependency graph — from
ordinary transient failures.
"""

from __future__ import annotations

from typing import List, Optional


class FactorResolutionError(Exception):
    """Base class for all factor-resolution-pipeline errors."""


class FactorDependencyCycleError(FactorResolutionError):
    """
    Raised when the factor dependency graph contains a directed cycle.

    Carries the full cycle path so callers can identify exactly which factors
    form the cycle without inspecting internal state.

    Attributes
    ----------
    cycle_names : list of str
        Factor names forming the cycle, e.g. ``["A", "B", "C", "A"]``.
        The first and last element are the same factor (entry point of cycle).
    cycle_ids : list of int
        Factor IDs in the same order as ``cycle_names``.
    cycle_path : str
        Human-readable arrow notation, e.g. ``"A → B → C → A"``.

    Examples
    --------
    Self-cycle:
        cycle_names=["A", "A"],  cycle_path="A → A"

    Two-factor cycle:
        cycle_names=["A", "B", "A"],  cycle_path="A → B → A"

    Three-factor cycle:
        cycle_names=["A", "B", "C", "A"],  cycle_path="A → B → C → A"

    Cycle embedded in larger graph (B → D → E → B):
        cycle_names=["B", "D", "E", "B"]
    """

    def __init__(
        self,
        cycle_names: List[str],
        cycle_ids: Optional[List[int]] = None,
        message: Optional[str] = None,
    ) -> None:
        self.cycle_names = list(cycle_names)
        self.cycle_ids = list(cycle_ids) if cycle_ids else []
        self.cycle_path = " → ".join(str(n) for n in cycle_names)
        full_msg = message or f"Factor dependency cycle detected: {self.cycle_path}"
        super().__init__(full_msg)
