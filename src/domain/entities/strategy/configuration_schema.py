"""
Configuration schema of a strategy project: the fields each section accepts, their types, bounds and choices.

A project declares one ``SectionSchema`` per configuration section it supports (``universe``, ``factors``, ``model``,
``training``, ``portfolio``, ``trading``, ``risk``, ``evaluation``, ``data_policy``). ``validate_sections`` checks a
configuration against it: unknown sections or fields are rejected (a parameter that has no effect is never accepted
silently), types and bounds are enforced, missing fields take their defaults. Pure: no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

SECTIONS: Tuple[str, ...] = ("universe", "factors", "model", "training", "portfolio", "trading", "risk",
                             "evaluation", "data_policy")

ERROR, WARNING = "error", "warning"


@dataclass(frozen=True)
class ValidationIssue:
    section: str
    field: Optional[str]
    message: str
    severity: str = ERROR

    def __str__(self) -> str:
        where = f"{self.section}.{self.field}" if self.field else self.section
        return f"[{self.severity}] {where}: {self.message}"


@dataclass(frozen=True)
class FieldSpec:
    """One configurable field. ``kind``: int | float | bool | str | choice | date | datetime | str_list |
    choice_list | int_list | int_pair_list."""
    name: str
    kind: str
    default: Any = None
    label: str = ""
    help: str = ""
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    choices: Tuple[Any, ...] = ()
    required: bool = False
    nullable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "kind": self.kind, "default": self.default, "label": self.label or self.name,
                "help": self.help, "minimum": self.minimum, "maximum": self.maximum, "choices": list(self.choices),
                "required": self.required, "nullable": self.nullable}


@dataclass(frozen=True)
class SectionSchema:
    name: str
    fields: Tuple[FieldSpec, ...]
    label: str = ""
    help: str = ""

    def field(self, name: str) -> Optional[FieldSpec]:
        return next((f for f in self.fields if f.name == name), None)

    def defaults(self) -> Dict[str, Any]:
        return {f.name: f.default for f in self.fields}

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "label": self.label or self.name, "help": self.help,
                "fields": [f.to_dict() for f in self.fields]}


@dataclass(frozen=True)
class ConfigurationSchema:
    project_key: str
    sections: Tuple[SectionSchema, ...] = field(default_factory=tuple)

    def section(self, name: str) -> Optional[SectionSchema]:
        return next((s for s in self.sections if s.name == name), None)

    def defaults(self) -> Dict[str, Dict[str, Any]]:
        return {s.name: s.defaults() for s in self.sections}

    def to_dict(self) -> Dict[str, Any]:
        return {"project_key": self.project_key, "sections": [s.to_dict() for s in self.sections]}


def _is_int(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _number(v) -> bool:
    return (isinstance(v, (int, float)) and not isinstance(v, bool))


def _parse_date(v):
    if isinstance(v, datetime):
        return v
    if isinstance(v, date):
        return datetime(v.year, v.month, v.day)
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v.strip())
        except ValueError:
            return None
    return None


def coerce(spec: FieldSpec, value: Any) -> Tuple[Any, Optional[str]]:
    """(value normalised to the spec's kind, error message or None). Form values arrive as strings."""
    if value is None or (isinstance(value, str) and value.strip() == "" and spec.kind not in ("str",)):
        if spec.nullable or not spec.required:
            return (None if spec.nullable else spec.default), None
        return None, "is required"
    k = spec.kind
    try:
        if k == "int":
            if isinstance(value, str):
                value = int(value.strip())
            if not _is_int(value):
                return value, "must be an integer"
        elif k == "float":
            if isinstance(value, str):
                value = float(value.strip())
            if not _number(value):
                return value, "must be a number"
            value = float(value)
        elif k == "bool":
            if isinstance(value, str):
                if value.strip().lower() not in ("true", "false", "1", "0", "on", "off", "yes", "no"):
                    return value, "must be true or false"
                value = value.strip().lower() in ("true", "1", "on", "yes")
            if not isinstance(value, bool):
                return value, "must be true or false"
        elif k == "str":
            if not isinstance(value, str):
                return value, "must be text"
        elif k == "choice":
            if value not in spec.choices:
                return value, f"must be one of {list(spec.choices)}"
        elif k in ("date", "datetime"):
            parsed = _parse_date(value)
            if parsed is None:
                return value, "must be a date (YYYY-MM-DD) or date-time (YYYY-MM-DD HH:MM:SS)"
            value = parsed.strftime("%Y-%m-%d") if k == "date" else parsed.strftime("%Y-%m-%d %H:%M:%S")
        elif k in ("str_list", "choice_list"):
            if isinstance(value, str):
                value = [x.strip() for x in value.replace("\n", ",").split(",") if x.strip()]
            if not isinstance(value, (list, tuple)) or not all(isinstance(x, str) for x in value):
                return value, "must be a list of text values"
            value = list(dict.fromkeys(value))
            if k == "choice_list":
                bad = [x for x in value if x not in spec.choices]
                if bad:
                    return value, f"unknown values {bad}"
        elif k == "int_list":
            if isinstance(value, str):
                value = [int(x) for x in value.replace(" ", "").split(",") if x]
            if not isinstance(value, (list, tuple)) or not all(_is_int(x) for x in value):
                return value, "must be a list of integers"
            value = list(value)
        elif k == "int_pair_list":
            if isinstance(value, str):
                pairs = [p for p in value.replace(" ", "").split(";") if p]
                value = [[int(x) for x in p.split(",")] for p in pairs]
            if (not isinstance(value, (list, tuple))
                    or not all(isinstance(p, (list, tuple)) and len(p) == 2 and all(_is_int(x) for x in p)
                               for p in value)):
                return value, "must be pairs of integers (e.g. 2,6; 4,12)"
            value = [list(p) for p in value]
        else:
            return value, f"unknown field kind '{k}'"
    except (TypeError, ValueError):
        return value, f"is not a valid {k}"
    for v in (value if isinstance(value, list) and k in ("int_list",) else [value]):
        if spec.minimum is not None and _number(v) and v < spec.minimum:
            return value, f"must be >= {spec.minimum:g}"
        if spec.maximum is not None and _number(v) and v > spec.maximum:
            return value, f"must be <= {spec.maximum:g}"
    return value, None


def validate_sections(schema: ConfigurationSchema, sections: Dict[str, Dict[str, Any]]
                      ) -> Tuple[Dict[str, Dict[str, Any]], List[ValidationIssue]]:
    """(normalised sections with defaults filled in, issues). Unknown sections / fields are errors."""
    issues: List[ValidationIssue] = []
    out: Dict[str, Dict[str, Any]] = {}
    for name in sections or {}:
        if name not in SECTIONS:
            issues.append(ValidationIssue(name, None, "unknown section"))
        elif schema.section(name) is None:
            issues.append(ValidationIssue(name, None, f"not supported by project '{schema.project_key}'"))
    for section in schema.sections:
        given = dict((sections or {}).get(section.name) or {})
        values: Dict[str, Any] = {}
        for key in given:
            if section.field(key) is None:
                issues.append(ValidationIssue(section.name, key,
                                              f"not supported by project '{schema.project_key}'"))
        for spec in section.fields:
            if spec.name in given:
                value, error = coerce(spec, given[spec.name])
                if error:
                    issues.append(ValidationIssue(section.name, spec.name, error))
            elif spec.required:
                value = None
                issues.append(ValidationIssue(section.name, spec.name, "is required"))
            else:
                value = spec.default
            values[spec.name] = value
        out[section.name] = values
    return out, issues


def errors(issues: Sequence[ValidationIssue]) -> List[ValidationIssue]:
    return [i for i in issues if i.severity == ERROR]
