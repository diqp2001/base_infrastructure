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
