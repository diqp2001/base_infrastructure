"""
Checklist section 9 — every repository under src/infrastructure/repositories is tested.

Generic checks run on all modules (in-memory SQLite, MagicMock IBKR client, nothing connects):
  * every module imports;
  * every concrete repository class can be built;
  * every local repository is registered in RepositoryFactory (bases excepted);
  * every local repository's get_all() works on an empty database (bases excepted);
  * the IBKR registry builds with a client;
  * every local factor repository round-trips: _create_or_get (idempotent) -> get_by_name /
    get_by_id -> FactorMapper.to_domain returns the same class -> DISCRIMINATOR_CLASS_MAP entry.

Known defects are listed in KNOWN_* below with the reason. A listed repository must still fail
(the test says so when it is fixed: then delete the entry), and any new failure fails the suite.
"""

import importlib
import unittest
from unittest.mock import MagicMock

from tests.repositories.repository_checks import (
    Database, all_repository_classes, build, discriminator_map_has, factor_repository_classes,
    factor_round_trip, is_ibkr, quiet, repository_modules,
)

KNOWN_INIT = {}

# Base / infrastructure classes that are not meant to be in the factory registry.
NOT_REGISTERED_BY_DESIGN = {"BaseLocalRepository", "BaseFactorRepository", "GeographicRepository",
                            "MonitoringReadRepository", "FmpRepository",
                            # duplicates used by factor_repository_registry; the factory registers
                            # local_repo.factor.{continent,country}_factor_repository
                            "local_repo.factor.geographic.continent_factor_repository.ContinentFactorRepository",
                            "local_repo.factor.geographic.country_factor_repository.CountryFactorRepository"}
KNOWN_UNREGISTERED = set()

# Abstract-style bases: no model of their own, never used directly.
BASE_CLASSES = {"BaseLocalRepository", "BaseFactorRepository", "GeographicRepository"}

# Every factor repository round-trips and is in DISCRIMINATOR_CLASS_MAP (all fixed 2026-10-13);
# a new failure fails the suite.
KNOWN_FACTOR_ROUND_TRIP = {}
KNOWN_NO_DISCRIMINATOR_MAP = set()


def key(module_name, cls, classes):
    """Class name, or module-qualified when the same class name exists in several modules."""
    if sum(1 for _, c in classes if c.__name__ == cls.__name__) > 1:
        return f"{module_name.replace('src.infrastructure.repositories.', '')}.{cls.__name__}"
    return cls.__name__


class Known:
    """Assert a check passes, or — for a listed name — that it still fails."""

    def __init__(self, test, known, what):
        self.test, self.known, self.what = test, known, what

    def check(self, name, problem):
        if name in self.known:
            self.test.assertIsNotNone(problem, f"{name}: {self.what} now works — remove it from the known list "
                                               f"({self.known[name] if isinstance(self.known, dict) else 'listed'})")
        else:
            self.test.assertIsNone(problem, f"{name}: {self.what}: {problem}")


class AllRepositoriesTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        # import every repository first: some models (backtests, models, universes, ...) are only
        # registered on ModelBase.metadata by their repository module, and must exist before create_all
        cls.classes = all_repository_classes()
        cls.db = Database()

    @classmethod
    def tearDownClass(cls):
        cls.db.dispose()

    def test_every_module_imports(self):
        modules = repository_modules()
        self.assertGreater(len(modules), 250)
        for name in modules:
            with self.subTest(module=name):
                quiet(importlib.import_module, name)

    def test_every_repository_can_be_built(self):
        known = Known(self, KNOWN_INIT, "construction")
        for module_name, cls in self.classes:
            with self.subTest(repository=cls.__name__):
                session, factory = self.db.factory()
                try:
                    build(cls, session, factory)
                    problem = None
                except Exception as e:
                    problem = f"{type(e).__name__}: {e}"
                known.check(key(module_name, cls, self.classes), problem)
                session.close()

    def test_every_local_repository_is_in_the_factory(self):
        session, factory = self.db.factory()
        registered = {type(r) for r in factory.create_local_repositories().values()}
        known = Known(self, {n: "unregistered" for n in KNOWN_UNREGISTERED}, "factory registration")
        for module_name, cls in self.classes:
            if is_ibkr(module_name) or key(module_name, cls, self.classes) in NOT_REGISTERED_BY_DESIGN \
                    or cls.__name__ in NOT_REGISTERED_BY_DESIGN:
                continue
            with self.subTest(repository=cls.__name__):
                known.check(key(module_name, cls, self.classes),
                            None if cls in registered else "not in RepositoryFactory.create_local_repositories")
        session.close()

    def test_get_all_on_an_empty_database(self):
        known = Known(self, {}, "get_all()")
        for module_name, cls in self.classes:
            if is_ibkr(module_name) or cls.__name__ in KNOWN_INIT or cls.__name__ in BASE_CLASSES:
                continue
            session, factory = self.db.factory()
            repo = build(cls, session, factory)
            if not hasattr(repo, "get_all"):
                session.close()
                continue
            with self.subTest(repository=cls.__name__):
                try:
                    rows = quiet(repo.get_all)
                    problem = None if isinstance(rows, list) else f"returned {type(rows).__name__}"
                except Exception as e:
                    problem = f"{type(e).__name__}: {str(e)[:200]}"
                known.check(key(module_name, cls, self.classes), problem)
            session.rollback()
            session.close()

    def test_ibkr_registry_builds_with_a_client(self):
        session, factory = self.db.factory()
        repos = quiet(factory.create_ibkr_repositories, MagicMock(name="ibkr_client"))
        self.assertGreater(len(repos), 100)
        self.assertEqual([k for k, v in repos.items() if v is None], [])
        session.close()

    def test_factory_without_client_never_offers_ibkr(self):
        session, factory = self.db.factory()
        self.assertFalse(factory._available_repository_families["ibkr"])
        self.assertEqual(factory._ibkr_repositories, {})
        session.close()

    def test_every_factor_repository_round_trips(self):
        repos = factor_repository_classes()
        self.assertGreater(len(repos), 100)
        known = Known(self, KNOWN_FACTOR_ROUND_TRIP, "factor round trip")
        for module_name, cls in repos:
            with self.subTest(repository=cls.__name__):
                session, factory = self.db.factory()
                try:
                    problem = factor_round_trip(cls, session, factory)
                finally:
                    session.rollback()
                    session.close()
                known.check(cls.__name__, problem)

    def test_every_factor_class_is_in_the_discriminator_map(self):
        known = Known(self, {n: "missing" for n in KNOWN_NO_DISCRIMINATOR_MAP}, "DISCRIMINATOR_CLASS_MAP")
        for module_name, cls in factor_repository_classes():
            session, factory = self.db.factory()
            entity_cls = build(cls, session, factory).entity_class
            session.close()
            if entity_cls is None:
                continue
            with self.subTest(repository=cls.__name__):
                known.check(cls.__name__, None if discriminator_map_has(entity_cls)
                            else f"{entity_cls.__name__} not in DISCRIMINATOR_CLASS_MAP")


if __name__ == "__main__":
    unittest.main()
