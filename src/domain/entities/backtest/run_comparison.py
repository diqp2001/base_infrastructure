"""
Comparability of backtest runs - pure domain logic (2026-11-18).

Viewable is not the same as economically comparable: runs of different models on different universes can be shown
side by side, but every assumption that differs is reported as a difference and, when it changes what the numbers
mean, as a warning. Nothing is refused: the reader decides.

    compare_runs(runs, models_by_run) -> RunComparison(differences, config_differences, warnings)

``runs``: BacktestRun entities. ``models_by_run``: {run id: [model description dicts]} (name, version, features,
hyperparameters), optional.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

from src.domain.entities.backtest.backtest_run import COMPLETED, BacktestRun

# (attribute, label, warning when they differ; None = a difference, not a warning)
COMPARED_FIELDS = (
    ("project_name", "project", None),
    ("requested_start", "window start", "Backtest windows differ."),
    ("requested_end", "window end", "Backtest windows differ."),
    ("universe_description", "universe", "Universes differ - performance is not directly comparable."),
    ("price_source", "price source", "Price sources differ."),
    ("include_dividends", "dividends", "Dividend treatment differs."),
    ("include_transaction_costs", "transaction costs", "Transaction cost assumptions differ."),
    ("starting_capital", "starting capital", "Starting capital differs."),
    ("gross_leverage", "gross leverage", "Gross leverage differs."),
    ("code_commit", "code commit", None),
)
POINT_IN_TIME_KEY = "point_in_time_membership"


@dataclass
class Difference:
    field: str
    label: str
    by_run: Dict[int, Any]

    def to_dict(self):
        return {"field": self.field, "label": self.label, "by_run": {str(k): v for k, v in self.by_run.items()}}


@dataclass
class RunComparison:
    run_ids: List[int]
    differences: List[Difference] = field(default_factory=list)
    config_differences: List[Difference] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def comparable(self) -> bool:
        return not self.warnings

    def to_dict(self):
        return {"run_ids": self.run_ids, "comparable": self.comparable, "warnings": self.warnings,
                "differences": [d.to_dict() for d in self.differences],
                "config_differences": [d.to_dict() for d in self.config_differences]}


def _norm(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    if isinstance(value, float):
        return round(value, 10)
    return value


def flatten(value: Any, prefix: str = "") -> Dict[str, Any]:
    """{'a': {'b': 1}, 'c': [1, 2]} -> {'a.b': 1, 'c': [1, 2]} (lists are leaves)."""
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for k, v in value.items():
            out.update(flatten(v, f"{prefix}.{k}" if prefix else str(k)))
        return out
    return {prefix: value}


def config_differences(runs: List[BacktestRun]) -> List[Difference]:
    flat = {r.id: flatten(r.config_snapshot or {}) for r in runs}
    keys = sorted({k for f in flat.values() for k in f})
    out = []
    for key in keys:
        values = {rid: f.get(key, "<absent>") for rid, f in flat.items()}
        if len({repr(v) for v in values.values()}) > 1:
            out.append(Difference(key, key, values))
    return out


def _model_signature(models: Iterable[Dict[str, Any]]) -> List[Any]:
    return sorted((m.get("name"), m.get("version"), m.get("role")) for m in models or [])


def compare_runs(runs: List[BacktestRun],
                 models_by_run: Optional[Dict[int, List[Dict[str, Any]]]] = None) -> RunComparison:
    if len(runs) < 2:
        raise ValueError("a comparison needs at least two runs")
    result = RunComparison(run_ids=[r.id for r in runs])
    warned = set()

    def warn(text):
        if text not in warned:
            warned.add(text)
            result.warnings.append(text)

    for attr, label, warning in COMPARED_FIELDS:
        values = {r.id: _norm(getattr(r, attr)) for r in runs}
        if len({repr(v) for v in values.values()}) > 1:
            result.differences.append(Difference(attr, label, values))
            if warning:
                warn(warning)
    pit = {r.id: (r.universe_snapshot or {}).get(POINT_IN_TIME_KEY) for r in runs}
    if len({repr(v) for v in pit.values()}) > 1:
        result.differences.append(Difference(POINT_IN_TIME_KEY, "point-in-time membership", pit))
        warn("Universe membership rules differ (point-in-time vs fixed).")
    if models_by_run is not None:
        signatures = {r.id: _model_signature(models_by_run.get(r.id)) for r in runs}
        if len({repr(v) for v in signatures.values()}) > 1:
            result.differences.append(Difference("models", "models", {
                rid: [f"{n} v{v}" + (f" ({role})" if role else "") for n, v, role in sig]
                for rid, sig in signatures.items()}))
    for r in runs:
        if r.status != COMPLETED:
            warn(f"Run {r.id} is {r.status} ({r.progress_label()}): its results cover only part of its window.")
        if r.code_dirty:
            warn(f"Run {r.id} ran on uncommitted code: its commit does not fully describe it.")
    result.config_differences = config_differences(runs)
    return result
