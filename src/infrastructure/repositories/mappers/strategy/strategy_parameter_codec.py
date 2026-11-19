"""
A Strategy's parameters <-> rows of (section, name, value) (tables strategy_parameters / strategy_parameter_values).

* every LEAF of the strategy's sections is one row: ``name`` is its path inside the section, JSON-pointer style
  (keys joined by '/', '~' written '~0', '/' written '~1', an empty key '~e'): section 'model',
  name 'stm.model/params/hidden_dim'. Lists are leaves (stored as JSON). An empty dict is a leaf too ('{}'), an
  empty section is the row (section, '') - so the sections rebuild exactly (the content hash depends on them);
* the typed definition (bar_frequency, bar_size, model_type, training_window, retrain_every_days,
  prediction_horizon) is section 'definition', one row per field that has a value;
* a value is stored as text with its type (null, bool, int, float, str, json) and, for int / float, a numeric copy.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Tuple

DEFINITION_SECTION = "definition"
NULL, BOOL, INT, FLOAT, STR, JSON = "null", "bool", "int", "float", "str", "json"


def escape(key: str) -> str:
    key = str(key)
    if key == "":
        return "~e"
    return key.replace("~", "~0").replace("/", "~1")


def unescape(token: str) -> str:
    if token == "~e":
        return ""
    return token.replace("~1", "/").replace("~0", "~")


def flatten(sections: Dict[str, Dict[str, Any]], definition: Optional[Dict[str, Any]] = None
            ) -> List[Tuple[str, str, Any]]:
    """[(section, name, leaf value)] of the sections, then the typed definition (fields without a value skipped)."""
    rows: List[Tuple[str, str, Any]] = []

    def walk(section: str, value: Dict[str, Any], path: List[str]) -> None:
        for key, item in value.items():
            here = path + [escape(key)]
            if isinstance(item, dict) and item:
                walk(section, item, here)
            else:
                rows.append((section, "/".join(here), item))

    for section, values in (sections or {}).items():
        if section == DEFINITION_SECTION:
            raise ValueError(f"'{DEFINITION_SECTION}' is reserved for the typed definition")
        if isinstance(values, dict) and values:
            walk(section, values, [])
        else:
            rows.append((section, "", values if values is not None else {}))
    for field, value in (definition or {}).items():
        if value is not None:
            rows.append((DEFINITION_SECTION, field, value))
    return rows


def unflatten(rows: Iterable[Tuple[str, str, Any]]) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """(sections, definition) from rows of (section, name, value)."""
    sections: Dict[str, Dict[str, Any]] = {}
    definition: Dict[str, Any] = {}
    for section, name, value in rows:
        if section == DEFINITION_SECTION:
            definition[name] = value
            continue
        target = sections.setdefault(section, {})
        if name == "":
            continue                                        # the empty section itself
        tokens = [unescape(t) for t in name.split("/")]
        for token in tokens[:-1]:
            target = target.setdefault(token, {})
        target[tokens[-1]] = value
    return sections, definition


def encode(value: Any) -> Tuple[str, Optional[str], Optional[float]]:
    """(value_type, text, numeric copy)."""
    if value is None:
        return NULL, None, None
    if isinstance(value, bool):
        return BOOL, "true" if value else "false", None
    if isinstance(value, int):
        return INT, str(value), float(value)
    if isinstance(value, float):
        return FLOAT, repr(value), value if value == value and abs(value) != float("inf") else None
    if isinstance(value, str):
        return STR, value, None
    if isinstance(value, (list, tuple, dict)):
        return JSON, json.dumps(value, sort_keys=True, default=str), None
    return STR, str(value), None


def decode(value_type: str, text: Optional[str]) -> Any:
    if value_type == NULL or text is None:
        return None
    if value_type == BOOL:
        return text == "true"
    if value_type == INT:
        return int(text)
    if value_type == FLOAT:
        return float(text)
    if value_type == JSON:
        return json.loads(text)
    return text
