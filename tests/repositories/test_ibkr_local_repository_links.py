"""Every IBKR repository finds its local counterpart (the IRX import failed: 'index_factor' was not a registry key)."""

import pathlib
import re
from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.repositories.repository_factory import RepositoryFactory, RepositoryRegistry

IBKR_ROOT = pathlib.Path(__file__).resolve().parents[2] / "src" / "infrastructure" / "repositories" / "ibkr_repo"


@pytest.fixture(scope="module")
def factory():
    with patch.object(RepositoryFactory, "create_ibkr_client", return_value=None):
        f = RepositoryFactory(MagicMock())
    f.create_local_repositories()
    return f


def test_the_registry_accepts_snake_case_keys():
    registry = RepositoryRegistry({"IndexFactor": "repo"})
    assert registry.get("index_factor") == "repo" and registry.get("IndexFactor") == "repo"
    assert registry.get("missing_factor") is None and registry.get("missing_factor", 0) == 0


def test_every_ibkr_repository_finds_its_local_repository(factory):
    keys = set()
    for path in IBKR_ROOT.rglob("*.py"):
        keys.update(re.findall(r"_local_repositories\.get\('([A-Za-z_]+)'\)", path.read_text(encoding="utf-8")))
    assert keys, "no lookup found"
    missing = sorted(k for k in keys if factory._local_repositories.get(k) is None)
    assert missing == []


def test_the_ibkr_index_factor_repository_is_linked(factory):
    from src.infrastructure.repositories.ibkr_repo.factor.finance.financial_assets.index.ibkr_index_factor_repository import (
        IBKRIndexFactorRepository,
    )
    assert IBKRIndexFactorRepository(ibkr_client=None, factory=factory).local_repo is not None


def test_every_registered_ibkr_factor_repository_is_found_by_its_class():
    from src.infrastructure.repositories.mappers.factor.factor_mapper import DISCRIMINATOR_CLASS_MAP
    from src.domain.entities.factor.finance.financial_assets.index.index_factor import IndexFactor
    with patch.object(RepositoryFactory, "create_ibkr_client", return_value=MagicMock()):
        f = RepositoryFactory(MagicMock(), ibkr_client=MagicMock())
    assert type(f.get_ibkr_repository(IndexFactor)).__name__ == "IBKRIndexFactorRepository"
    repos = f.create_ibkr_repositories()
    missing = sorted(cls.__name__ for cls in set(DISCRIMINATOR_CLASS_MAP.values())
                     if cls.__name__ in repos and f.get_ibkr_repository(cls) is None)
    assert missing == []


def test_the_local_index_factor_repository_accepts_the_ibkr_keyword_call():
    """IBKRIndexFactorRepository calls local_repo._create_or_get(primary_key=...) without entity_cls (IRX import)."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import src.infrastructure.models  # noqa: F401  (registers every ORM table)
    from src.infrastructure.models import ModelBase
    from src.infrastructure.repositories.local_repo.factor.finance.financial_assets.index.index_factor_repository import (
        IndexFactorRepository,
    )

    engine = create_engine("sqlite://")
    ModelBase.metadata.create_all(engine)
    repo = IndexFactorRepository(sessionmaker(bind=engine)())
    created = repo._create_or_get(primary_key="close", group="price", subgroup="TRADES", frequency="1d")
    assert created is not None and created.name == "close"
    again = repo._create_or_get(primary_key="close", group="price", subgroup="TRADES", frequency="1d")
    assert again is not None and again.id == created.id
