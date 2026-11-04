"""
Bar validation at import (P.08.08, GA-A4). A bar IBKR returns is stored only when it is consistent:

    prices > 0                         open / high / low / close, for price bars (TRADES, MIDPOINT, BID, ASK, ...)
    low <= open, close <= high         and low <= high, for every bar that has the four fields
    volume >= 0                        TRADES only (IBKR sends volume -1 on MIDPOINT / BID / ASK bars)

A rejected bar is never stored; the caller logs it as an import anomaly. Missing or non-numeric fields are left to
the extraction (a bar without 'high' simply yields no high value).
"""

from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Tuple

PRICE_FIELDS = ("open", "high", "low", "close")
# data types whose bars are prices (strictly positive); volatility / yield types are only checked for consistency
PRICE_TYPES = frozenset({"TRADES", "MIDPOINT", "BID", "ASK", "BID_ASK", "ADJUSTED_LAST"})
_EPS = 1e-9


def _number(value: Any) -> Optional[float]:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def bar_problems(bar: Dict[str, Any], what_to_show: Optional[str] = "TRADES") -> List[str]:
    """Why ``bar`` must not be stored; empty when it is valid."""
    kind = (what_to_show or "").upper()
    prices = {f: _number(bar.get(f)) for f in PRICE_FIELDS if bar.get(f) is not None}
    problems = []
    if any(v is None for v in prices.values()):
        problems.append("non-numeric price " + ", ".join(f for f, v in prices.items() if v is None))
    prices = {f: v for f, v in prices.items() if v is not None}
    if kind in PRICE_TYPES:
        bad = [f"{f} {v:g}" for f, v in prices.items() if v <= 0]
        if bad:
            problems.append("price <= 0: " + ", ".join(bad))
    if len(prices) == 4:
        low, high = prices["low"], prices["high"]
        if low > high + _EPS:
            problems.append(f"low {low:g} > high {high:g}")
        for f in ("open", "close"):
            if not (low - _EPS <= prices[f] <= high + _EPS):
                problems.append(f"{f} {prices[f]:g} outside low {low:g} .. high {high:g}")
    if kind == "TRADES" and bar.get("volume") is not None:
        volume = _number(bar.get("volume"))
        if volume is None or volume < 0:
            problems.append(f"volume {bar.get('volume')!r} < 0")
    return problems


def split_valid_bars(bars: Iterable[Dict[str, Any]], what_to_show: Optional[str] = "TRADES"
                     ) -> Tuple[List[Dict[str, Any]], List[Tuple[Dict[str, Any], List[str]]]]:
    """(bars to store, [(rejected bar, problems)])."""
    valid, rejected = [], []
    for bar in bars or []:
        problems = bar_problems(bar, what_to_show)
        if problems:
            rejected.append((bar, problems))
        else:
            valid.append(bar)
    return valid, rejected
