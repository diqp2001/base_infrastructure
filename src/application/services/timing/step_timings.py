"""
StepTimings — where the time of one engine step (bar) goes.

The engine creates one StepTimings per bar and makes it the CURRENT one (a context variable), so code at any depth
(the trading cycle, the model provider, ...) records into it with ``timed("read")`` without passing it around:

    with timed("features"):
        panel = build_feature_panel(...)

Sections add up when entered several times in the same bar. ``count(name, n)`` records counters (e.g. the IBKR
historical requests sent during the slice). Nothing is recorded when no StepTimings is current, so the helpers
are free outside a timed step.
"""

from __future__ import annotations

import contextvars
import time
from collections import OrderedDict
from contextlib import contextmanager
from typing import Dict, Iterator, Optional

_current: contextvars.ContextVar[Optional["StepTimings"]] = contextvars.ContextVar("step_timings", default=None)


class StepTimings:

    def __init__(self, label: str = ""):
        self.label = label
        self.seconds: "OrderedDict[str, float]" = OrderedDict()
        self.counts: "OrderedDict[str, int]" = OrderedDict()

    @contextmanager
    def section(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            self.seconds[name] = self.seconds.get(name, 0.0) + time.perf_counter() - start

    def count(self, name: str, n: int = 1) -> None:
        self.counts[name] = self.counts.get(name, 0) + int(n)

    def as_row(self) -> Dict[str, float]:
        row: Dict[str, float] = {f"{k}_s": round(v, 3) for k, v in self.seconds.items()}
        row.update(self.counts)
        return row

    def line(self, order=None) -> str:
        names = list(order or self.seconds)
        parts = [f"{n} {self.seconds[n]:.1f}s" for n in names if n in self.seconds]
        parts += [f"{n} {c}" for n, c in self.counts.items()]
        return f"[timing] {self.label}  " + " | ".join(parts)


def current() -> Optional[StepTimings]:
    return _current.get()


@contextmanager
def activate(timings: StepTimings) -> Iterator[StepTimings]:
    """Make ``timings`` the current StepTimings for the duration of the block."""
    token = _current.set(timings)
    try:
        yield timings
    finally:
        _current.reset(token)


@contextmanager
def timed(name: str) -> Iterator[None]:
    """Add the block's duration to section ``name`` of the current StepTimings (no-op when none is current)."""
    timings = _current.get()
    if timings is None:
        yield
        return
    with timings.section(name):
        yield


def count(name: str, n: int = 1) -> None:
    timings = _current.get()
    if timings is not None:
        timings.count(name, n)


# ── Per-bar records (CSV) and run summary ───────────────────────────────────────────────────────────────────────────

TOP_LEVEL = ("slice", "cycle", "orders", "valuation")                  # they add up to the step's time
DETAIL = ("update", "read", "features", "train", "score", "persist")  # inside the cycle
CSV_COLUMNS = (["bar", "total_s"] + [f"{n}_s" for n in TOP_LEVEL] + [f"{n}_s" for n in DETAIL]
               + ["ibkr_s", "ibkr_requests"])


def record(timings: StepTimings, csv_path: str) -> str:
    """Append the bar to ``csv_path`` (header written once) and return the one-line summary."""
    import csv
    import os
    total = sum(timings.seconds.get(n, 0.0) for n in TOP_LEVEL)
    row = {"bar": timings.label, "total_s": round(total, 3)}
    row.update({f"{n}_s": round(timings.seconds.get(n, 0.0), 3) for n in TOP_LEVEL + DETAIL + ("ibkr",)})
    row["ibkr_requests"] = timings.counts.get("ibkr_requests", 0)
    try:
        os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
        new = not os.path.exists(csv_path)
        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
            if new:
                writer.writeheader()
            writer.writerow(row)
    except OSError:
        pass                                                           # timing must never break a run
    top = " ".join(f"{n} {timings.seconds.get(n, 0.0):.1f}s" for n in TOP_LEVEL)
    detail = " ".join(f"{n} {timings.seconds[n]:.1f}" for n in DETAIL if n in timings.seconds)
    ibkr = f"ibkr {timings.counts.get('ibkr_requests', 0)} req {timings.seconds.get('ibkr', 0.0):.1f}s"
    return f"[timing] {timings.label}  total {total:.1f}s | {top} | cycle: {detail or '-'} | {ibkr}"


def summarise(csv_path: str) -> Optional[str]:
    """Mean seconds per bar of each section and its share of the total, from the per-bar CSV."""
    import csv
    import os
    if not os.path.exists(csv_path):
        return None
    with open(csv_path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return None
    n = len(rows)
    mean = {c: sum(float(r.get(c) or 0) for r in rows) / n for c in CSV_COLUMNS[1:]}
    total = mean["total_s"] or 1e-9
    parts = [f"{c[:-2]} {mean[c]:.1f}s ({100 * mean[c] / total:.0f}%)" for c in [f"{t}_s" for t in TOP_LEVEL]]
    detail = [f"{c[:-2]} {mean[c]:.1f}s" for c in [f"{d}_s" for d in DETAIL] if mean[c] > 0]
    return (f"[timing] {n} bars, mean {mean['total_s']:.1f}s per bar: " + ", ".join(parts)
            + f" | cycle: {', '.join(detail) or '-'} | ibkr {mean['ibkr_requests']:.1f} requests "
              f"{mean['ibkr_s']:.1f}s per bar")
