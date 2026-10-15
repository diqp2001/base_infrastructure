"""
Catalog of every factor class that defines calculate(), discovered from src/domain/entities/factor.

Used by the wiring and resolution tests so that a new factor is covered without editing them.
"""

import importlib
import inspect
import pathlib
from functools import lru_cache

FACTOR_ROOT = pathlib.Path(__file__).resolve().parents[3] / "src" / "domain" / "entities" / "factor"
# keys calculate() may read that the resolution service adds itself (not declared dependencies)
SERVICE_KEYS = {"entity", "target_date"}
# string dependencies resolved from an attribute of a related entity (_resolve_entity_attr_dep)
ENTITY_ATTRIBUTE_DEPS = {"Position"}


@lru_cache(maxsize=None)
def factor_classes():
    """[(class name, class)] for every class that defines calculate(), sorted by name."""
    found = {}
    for path in sorted(FACTOR_ROOT.rglob("*.py")):
        if path.name.startswith("_") or "def calculate(" not in path.read_text(encoding="utf-8"):
            continue
        module_name = ".".join(path.relative_to(FACTOR_ROOT.parents[3]).with_suffix("").parts)
        module = importlib.import_module(module_name)
        for name, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ == module_name and "calculate" in cls.__dict__:
                found[name] = cls
    return sorted(found.items())


def instantiate(cls):
    """The factor with its default parameters, or None when it needs arguments."""
    try:
        return cls()
    except TypeError:
        return None


def declared_dependencies(factor):
    """calculate_dependencies of an instance ([] when the property is missing)."""
    deps = getattr(factor, "calculate_dependencies", None)
    if deps is None:
        return []
    return deps if isinstance(deps, list) else [deps]


def dependency_name(dep):
    return dep if isinstance(dep, str) else dep.dep_name


def unfed_parameters(cls, dependency_names):
    """Required calculate() parameters the resolution service cannot fill.

    _call_factor_calculate_method passes the whole dict to a `dependencies` parameter; otherwise it
    matches each parameter by name against the resolved dependencies (+ entity / target_date)."""
    params = [p for name, p in inspect.signature(cls.calculate).parameters.items() if name != "self"]
    if any(p.name == "dependencies" for p in params):
        return []
    fed = set(dependency_names) | SERVICE_KEYS
    return [p.name for p in params
            if p.default is inspect.Parameter.empty
            and p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            and p.name not in fed]
