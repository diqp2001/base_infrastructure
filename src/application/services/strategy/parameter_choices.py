"""
Every strategy parameter as a choice, never typed text: the designer shows each value of a project's sections as a
dropdown (one value) or a checkbox list (a list of values), and reads the posted choices back.

field_tree(section, values, locked)   the fields of one section (nested dicts become groups)
apply_choices(section, values, form)  the section with the posted choices written in (only offered values accepted)

Choices: booleans true / false; numbers a grid around the current value; known text parameters their list
(KNOWN_TEXT); known lists their catalog (fundamentals, price sources, return horizons, MACD pairs); anything else keeps
its value (shown, not editable). The current value is always one of the choices.
"""

from __future__ import annotations

import copy
import json
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

IBKR_BAR_SIZES = ("1 min", "2 mins", "3 mins", "5 mins", "10 mins", "15 mins", "20 mins", "30 mins", "1 hour",
                  "2 hours", "3 hours", "4 hours", "8 hours", "1 day", "1 week", "1 month")
BAR_FREQUENCIES = ("1m", "2m", "3m", "5m", "10m", "15m", "20m", "30m", "1h", "2h", "3h", "4h", "8h", "1d", "1w", "1mo")

KNOWN_TEXT: Dict[str, Tuple[str, ...]] = {
    "weighting": ("equal_weight", "market_cap_weight", "volatility_weight", "model_score_weight"),
    "fundamental_scaling": ("sector_neutral", "cross_sectional"),
    "research_price_series": ("ADJUSTED_LAST", "TRADES"),
    "traded_variant": ("A", "B"),
    "device": ("cpu", "cuda"),
    "model_type": ("tft", "conv", "lstm", "mlp", "slp", "lightgbm"),
    "currency_code": ("USD", "EUR", "GBP", "CAD", "CHF", "JPY"),
    "initial_cash_currency_code": ("USD", "EUR", "GBP", "CAD", "CHF", "JPY"),
    "duration_str": ("1 M", "3 M", "6 M", "1 Y", "2 Y", "3 Y", "5 Y", "10 Y", "20 Y"),
    "bar_size_setting": IBKR_BAR_SIZES,
    "scaling": ("standard", "minmax", "robust", "none"),
    "session_start": ("09:30", "09:35", "09:40", "09:45", "10:00"),
    "session_end": ("15:30", "15:45", "15:50", "15:55", "16:00"),
}
INT_GRID = (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 18, 20, 21, 24, 25, 26, 30, 32, 36, 40, 42, 48,
            50, 52, 60, 63, 64, 72, 84, 90, 96, 100, 104, 120, 126, 128, 150, 156, 180, 200, 240, 250, 252, 256, 300,
            365, 500, 504, 512, 730, 756, 1000, 1008, 1260, 1825, 2520, 5000, 10000)
FLOAT_COMMON = (0.0, 0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01, 0.02, 0.03, 0.05, 0.075, 0.1, 0.15, 0.2, 0.25, 0.3,
                0.4, 0.5, 0.6, 0.75, 0.8, 0.9, 0.95, 0.99, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0, 7.5, 10.0, 15.0, 20.0,
                25.0, 50.0, 100.0)
HORIZONS = tuple(range(1, 25)) + (26, 30, 36, 48, 52, 60, 63, 104, 126, 156, 252)
MACD_PAIRS = ((2, 4), (3, 6), (4, 8), (4, 12), (6, 12), (8, 16), (8, 24), (12, 24), (12, 26), (16, 32), (16, 48),
              (24, 52), (32, 64), (32, 96), (64, 192))
PRICE_SOURCES = ("ibkr", "eulerpool", "fmp")


def _fundamentals() -> Tuple[str, ...]:
    try:
        from src.application.services.data.entities.factor.cross_sectional_momentum.csm_fundamentals import (
            available_candidates,
        )
        return tuple(available_candidates())
    except Exception:                       # the catalog unavailable: the current list stays the only choice
        return ()


KNOWN_LISTS: Dict[str, Callable[[], Sequence[Any]]] = {
    "fundamentals": _fundamentals,
    "file_price_sources": lambda: PRICE_SOURCES,
    "return_horizons": lambda: HORIZONS,
    "macd_combinations": lambda: [list(p) for p in MACD_PAIRS],
}


# -- choices ----------------------------------------------------------------------------------------------------------
def int_choices(current: Optional[int]) -> List[int]:
    if current is None:
        return [v for v in INT_GRID if v <= 1000]
    lo, hi = (0, max(20, current * 10)) if current <= 10 else (max(1, current // 10), current * 10)
    return sorted({v for v in INT_GRID if lo <= v <= hi} | {current})


def float_choices(current: float) -> List[float]:
    def clean(x):
        return float(f"{x:.6g}")
    candidates = set(FLOAT_COMMON) | {clean(current * m) for m in (0.1, 0.25, 0.5, 0.75, 1.25, 1.5, 2, 3, 5, 10)}
    if current > 0:
        candidates = {c for c in candidates if c == 0 or current / 50 <= c <= current * 50}
    elif current < 0:
        candidates = {-c for c in candidates} | {0.0}
    return sorted(candidates | {clean(current)})


def text_choices(key: str, current: Optional[str]) -> List[str]:
    options = list(KNOWN_TEXT.get(key, ()))
    if current is not None and current not in options:
        options.insert(0, current)
    return options


def _label(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        return " / ".join(str(v) for v in value)
    return str(value)


def _option(value: Any) -> Tuple[str, str]:
    return json.dumps(value), _label(value)


# -- fields -------------------------------------------------------------------------------------------------------------
def _scalar_field(key: str, value: Any) -> Optional[Dict[str, Any]]:
    if isinstance(value, bool):
        options = [True, False]
    elif isinstance(value, int):
        options = int_choices(value)
    elif isinstance(value, float):
        options = float_choices(value)
    elif isinstance(value, str):
        if value.startswith("<class"):
            return None
        options = text_choices(key, value)
    else:
        return None
    return {"kind": "select", "options": [_option(v) for v in options], "selected": [json.dumps(value)]}


def _list_field(key: str, value: List[Any]) -> Optional[Dict[str, Any]]:
    known = KNOWN_LISTS.get(key)
    catalog: List[Any] = list(known()) if known else []
    if not catalog and value and all(isinstance(v, int) and not isinstance(v, bool) for v in value):
        catalog = list(HORIZONS)
    if not catalog and not value:
        return None
    current = [list(v) if isinstance(v, tuple) else v for v in value]
    options = list(catalog)
    for v in current:                       # the current values are always offered
        if v not in options:
            options.append(v)
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in options):
        options = sorted(options)
    return {"kind": "multi", "options": [_option(v) for v in options], "selected": [json.dumps(v) for v in current]}


def field_tree(section: str, values: Dict[str, Any], locked: Optional[Dict[str, str]] = None,
               path: Tuple[str, ...] = ()) -> List[Dict[str, Any]]:
    """[{name, key, label, kind: select | multi | group | fixed, options, selected, children, note}] of a section.
    ``locked``: {key: why} keys set elsewhere in the designer (shown, not editable)."""
    locked = locked or {}
    out = []
    for key, value in values.items():
        p = path + (key,)
        name = json.dumps([section, *p])
        base = {"name": name, "key": key, "label": key.split(".")[-1].replace("_", " ")}
        if key in locked:
            out.append({**base, "kind": "fixed", "value": _label(value) if not isinstance(value, dict) else "",
                        "note": locked[key]})
            continue
        if isinstance(value, dict):
            out.append({**base, "kind": "group", "children": field_tree(section, value, locked, p)})
            continue
        field = (_list_field(key, list(value)) if isinstance(value, (list, tuple))
                 else _scalar_field(key, value))
        out.append({**base, **field} if field else {**base, "kind": "fixed", "value": _label(value),
                                                     "note": "kept as the project defines it"})
    return out


def _walk(fields: Iterable[Dict[str, Any]]):
    for f in fields:
        if f["kind"] == "group":
            yield from _walk(f["children"])
        else:
            yield f


def apply_choices(section: str, values: Dict[str, Any], form, locked: Optional[Dict[str, str]] = None
                  ) -> Dict[str, Any]:
    """The section with the posted choices written in. ``form``: .get(name) / .getlist(name) (a Flask form); a
    value that is not one of the field's choices raises ValueError (nothing typed is ever accepted)."""
    out = copy.deepcopy(values)
    for f in _walk(field_tree(section, values, locked)):
        if f["kind"] not in ("select", "multi"):
            continue
        allowed = {v for v, _ in f["options"]}
        if f["kind"] == "select":
            raw = form.get(f["name"])
            if raw is None:
                continue
            if raw not in allowed:
                raise ValueError(f"{f['label']}: {raw!r} is not one of its choices")
            new = json.loads(raw)
        else:
            if form.get("present:" + f["name"]) is None:      # the checkbox list was not on the page
                continue
            raws = form.getlist(f["name"])
            bad = [r for r in raws if r not in allowed]
            if bad:
                raise ValueError(f"{f['label']}: {bad} are not among its choices")
            order = [v for v, _ in f["options"]]
            new = [json.loads(r) for r in sorted(set(raws), key=order.index)]
        node = out
        keys = json.loads(f["name"])[1:]
        for k in keys[:-1]:
            node = node[k]
        node[keys[-1]] = new
    return out
