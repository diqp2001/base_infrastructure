"""
Generic checks applied to every repository module under src/infrastructure/repositories.

Used by test_all_repositories.py (and runnable as a report: python -m tests.repositories.repository_checks).
In-memory SQLite and MagicMock IBKR clients only: nothing connects anywhere.
"""

import contextlib
import importlib
import inspect
import io
import os
from typing import Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO_DIR = os.path.join(ROOT, "src", "infrastructure", "repositories")
PACKAGE = "src.infrastructure.repositories"


def repository_modules() -> List[str]:
    """Every module of the repository layer except the mappers (tested through the repositories)."""
    names = []
    for dirpath, dirnames, files in os.walk(REPO_DIR):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "mappers")]
        for f in files:
            if f.endswith(".py") and f != "__init__.py":
                rel = os.path.relpath(os.path.join(dirpath, f), ROOT)[:-3]
                names.append(rel.replace(os.sep, "."))
    return sorted(names)


def quiet(fn, *args, **kwargs):
    """Call fn with stdout swallowed (repositories print their errors)."""
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


def repository_classes(module) -> List[type]:
    return [c for _, c in inspect.getmembers(module, inspect.isclass)
            if c.__module__ == module.__name__ and c.__name__.endswith(("Repository", "Repositories"))
            and not c.__name__.startswith("_") and not inspect.isabstract(c)]


def all_repository_classes() -> List[Tuple[str, type]]:
    out = []
    for name in repository_modules():
        module = quiet(importlib.import_module, name)
        out.extend((name, cls) for cls in repository_classes(module))
    return out


def is_ibkr(module_name: str) -> bool:
    return ".ibkr_repo." in module_name


def is_local_factor(module_name: str) -> bool:
    return ".local_repo.factor." in module_name


class Database:
    """One in-memory schema; each check gets its own session + factory."""

    def __init__(self):
        from src.infrastructure.models import ModelBase
        from src.infrastructure.repositories.repository_factory import RepositoryFactory
        # factories built here must never open a real IBKR connection
        self._no_ibkr = patch.object(RepositoryFactory, "create_ibkr_client", return_value=None)
        self._no_ibkr.start()
        self.engine = create_engine("sqlite:///:memory:")
        ModelBase.metadata.create_all(self.engine)

    def factory(self):
        from src.infrastructure.repositories.repository_factory import RepositoryFactory
        session = Session(self.engine)
        return session, quiet(RepositoryFactory, session)

    def dispose(self):
        self.engine.dispose()
        self._no_ibkr.stop()


def build(cls: type, session, factory):
    """Instantiate a repository from its constructor signature."""
    kwargs = {}
    engine = session.get_bind()
    for name, param in inspect.signature(cls.__init__).parameters.items():
        if name == "self" or param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
            continue
        if name == "session":
            kwargs[name] = session
        elif name == "factory":
            kwargs[name] = factory
        elif name in ("ibkr_client", "ib_client", "client", "ib_broker", "broker"):
            kwargs[name] = MagicMock(name="ibkr_client")
        elif name == "engine":
            kwargs[name] = engine
        elif name in ("local_repo", "local_repository"):
            kwargs[name] = MagicMock(name="local_repo")
        elif param.default is param.empty:
            raise TypeError(f"no test value for required parameter {name!r}")
    return quiet(cls, **kwargs)


# Raw IBKR bar factors have no defaults on purpose: group / frequency come from the request
# (bar size drives the raw frequency), so the round trip passes them like real callers do.
REQUIRED_CREATE_KWARGS = {
    "CompanyShareFactorRepository": {"group": "price", "subgroup": "ohlc", "frequency": "1d"},
}


def factor_round_trip(cls: type, session, factory) -> Optional[str]:
    """None when _create_or_get / get_by_name / get_by_id / FactorMapper agree, else the problem."""
    from src.infrastructure.repositories.mappers.factor.factor_mapper import FactorMapper
    repo = build(cls, session, factory)
    entity_cls = getattr(repo, "entity_class", None)
    name = f"rt_{cls.__name__}"
    kwargs = REQUIRED_CREATE_KWARGS.get(cls.__name__, {})
    try:
        first = quiet(repo._create_or_get, entity_cls, primary_key=name, **kwargs)
        second = quiet(repo._create_or_get, entity_cls, primary_key=name, **kwargs)
    except Exception as e:
        return f"_create_or_get raised {type(e).__name__}: {e}"
    if first is None:
        return "_create_or_get returned None with the repository defaults"
    if second is None or second.id != first.id:
        return "_create_or_get is not idempotent"
    if entity_cls is not None and type(first) is not entity_cls:
        return f"returned {type(first).__name__}, entity_class is {entity_cls.__name__}"
    by_name = repo.get_by_name(name) if hasattr(repo, "get_by_name") else first
    if by_name is None or by_name.id != first.id:
        return "get_by_name does not find the created factor"
    if hasattr(repo, "get_by_id"):
        by_id = repo.get_by_id(first.id)
        if by_id is None or by_id.name != name:
            return "get_by_id does not find the created factor"
    orm = session.query(repo.model_class).filter(repo.model_class.id == first.id).one()
    dispatched = FactorMapper.to_domain(orm)
    if type(dispatched) is not type(first):
        return f"FactorMapper.to_domain gives {type(dispatched).__name__} for {type(first).__name__}"
    return None


def discriminator_map_has(entity_cls) -> bool:
    from src.infrastructure.repositories.mappers.factor.factor_mapper import DISCRIMINATOR_CLASS_MAP
    return entity_cls in DISCRIMINATOR_CLASS_MAP.values()


def factor_repository_classes() -> List[Tuple[str, type]]:
    return [(m, c) for m, c in all_repository_classes()
            if is_local_factor(m) and hasattr(c, "_create_or_get") and hasattr(c, "get_by_name")
            and c.__name__ not in ("FactorRepository", "FactorValueRepository")]


def report():
    db = Database()
    session, factory = db.factory()
    registered = {type(r) for r in factory.create_local_repositories().values()}
    for module_name, cls in all_repository_classes():
        if not is_ibkr(module_name) and cls not in registered:
            print(f"UNREG {cls.__name__}")
        if not is_ibkr(module_name):
            try:
                repo = build(cls, *db.factory())
            except Exception:
                continue
            if hasattr(repo, "get_all"):
                try:
                    rows = quiet(repo.get_all)
                    if not isinstance(rows, list):
                        print(f"GETALL {cls.__name__}: returned {type(rows).__name__}")
                except Exception as e:
                    print(f"GETALL {cls.__name__}: {type(e).__name__}: {str(e)[:100]}")
    try:
        ib = quiet(factory.create_ibkr_repositories, MagicMock(name="ibkr_client"))
        print(f"IBKR registry: {len(ib or {})} repos, None values: {[k for k, v in (ib or {}).items() if v is None]}")
    except Exception as e:
        print(f"IBKR registry failed: {type(e).__name__}: {e}")
    for module_name, cls in factor_repository_classes():
        try:
            ent = build(cls, *db.factory()).entity_class
            if ent is not None and not discriminator_map_has(ent):
                print(f"NOMAP {cls.__name__} ({ent.__name__})")
        except Exception:
            pass
    for module_name, cls in all_repository_classes():
        session, factory = db.factory()
        try:
            build(cls, session, factory)
        except Exception as e:
            print(f"INIT  {cls.__name__}: {type(e).__name__}: {str(e)[:120]}")
            continue
        if is_local_factor(module_name) and hasattr(cls, "_create_or_get") and hasattr(cls, "get_by_name") \
                and cls.__name__ not in ("FactorRepository", "FactorValueRepository"):
            problem = factor_round_trip(cls, session, factory)
            if problem:
                print(f"FACTOR {cls.__name__}: {problem[:160]}")
        session.close()
    db.dispose()


if __name__ == "__main__":
    report()
