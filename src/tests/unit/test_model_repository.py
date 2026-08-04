"""
Unit tests for ModelRepository (backtest).

Exercises the domain-level CRUD interface that ModelRepository exposes:
add, get_by_id, get_by_name, get_all, update, delete, and _create_or_get.
All tests run against an in-memory SQLite database.
"""
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.models import ModelBase

# Explicit imports register the backtest tables with ModelBase.metadata.
from src.infrastructure.models.backtest.model import ModelModel              # noqa: F401
from src.infrastructure.models.backtest.backtest import BacktestModel        # noqa: F401
from src.infrastructure.models.backtest.universe import UniverseModel        # noqa: F401
from src.infrastructure.models.backtest.backtest_factor_backtest import (    # noqa: F401
    BacktestFactorBacktestModel,
)

from src.infrastructure.repositories.local_repo.backtest.model_repository import ModelRepository
from src.domain.entities.backtest.model import Model


class TestModelRepository(unittest.TestCase):
    """Tests for ModelRepository's domain-level CRUD interface."""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def setUp(self):
        """Create a fresh in-memory SQLite database and a ModelRepository."""
        self.engine = create_engine("sqlite://")
        ModelBase.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.repo = ModelRepository(self.session)

    def tearDown(self):
        """Roll back any open transaction and release the engine."""
        self.session.rollback()
        self.session.close()
        self.engine.dispose()

    # ------------------------------------------------------------------
    # add
    # ------------------------------------------------------------------

    def test_add_returns_domain_entity(self):
        """add persists the entity and returns a Model domain object with a set id."""
        result = self.repo.add(Model(id=None, name="alpha"))
        self.assertIsNotNone(result)
        self.assertIsInstance(result, Model)
        self.assertEqual(result.name, "alpha")
        self.assertIsNotNone(result.id)

    def test_add_is_idempotent_by_name(self):
        """Adding a Model with the same name twice returns the existing entity."""
        first = self.repo.add(Model(id=None, name="gamma"))
        second = self.repo.add(Model(id=None, name="gamma"))
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first.id, second.id)

    # ------------------------------------------------------------------
    # get_by_id
    # ------------------------------------------------------------------

    def test_get_by_id_returns_entity(self):
        """get_by_id returns the correct domain entity for a known id."""
        added = self.repo.add(Model(id=None, name="bravo"))
        result = self.repo.get_by_id(added.id)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, Model)
        self.assertEqual(result.name, "bravo")
        self.assertEqual(result.id, added.id)

    def test_get_by_id_missing_returns_none(self):
        """get_by_id returns None for a non-existent id."""
        result = self.repo.get_by_id(999)
        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # get_by_name
    # ------------------------------------------------------------------

    def test_get_by_name_returns_entity(self):
        """get_by_name returns the correct domain entity for a known name."""
        self.repo.add(Model(id=None, name="charlie"))
        result = self.repo.get_by_name("charlie")
        self.assertIsNotNone(result)
        self.assertIsInstance(result, Model)
        self.assertEqual(result.name, "charlie")

    def test_get_by_name_missing_returns_none(self):
        """get_by_name returns None when the name is not found."""
        result = self.repo.get_by_name("does_not_exist")
        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # get_all
    # ------------------------------------------------------------------

    def test_get_all_returns_entities(self):
        """get_all returns a list of domain Model entities for every stored record."""
        self.repo.add(Model(id=None, name="delta"))
        self.repo.add(Model(id=None, name="echo"))
        results = self.repo.get_all()
        self.assertEqual(len(results), 2)
        self.assertTrue(all(isinstance(r, Model) for r in results))

    def test_get_all_empty(self):
        """get_all returns an empty list when no records exist."""
        results = self.repo.get_all()
        self.assertEqual(results, [])

    # ------------------------------------------------------------------
    # update
    # ------------------------------------------------------------------

    def test_update_entity(self):
        """update modifies the entity in the database and returns the updated entity."""
        added = self.repo.add(Model(id=None, name="foxtrot"))
        modified = Model(id=added.id, name="foxtrot_v2")
        result = self.repo.update(modified)
        self.assertIsNotNone(result)
        self.assertIsInstance(result, Model)
        self.assertEqual(result.name, "foxtrot_v2")
        # Confirm the change was committed.
        fetched = self.repo.get_by_id(added.id)
        self.assertEqual(fetched.name, "foxtrot_v2")

    def test_update_returns_none_for_missing(self):
        """update returns None when the entity id does not exist."""
        phantom = Model(id=999, name="phantom")
        result = self.repo.update(phantom)
        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # delete
    # ------------------------------------------------------------------

    def test_delete_entity(self):
        """delete removes the entity; a subsequent get_by_id returns None."""
        added = self.repo.add(Model(id=None, name="golf"))
        success = self.repo.delete(added.id)
        self.assertTrue(success)
        self.assertIsNone(self.repo.get_by_id(added.id))

    def test_delete_returns_false_for_missing(self):
        """delete returns False when the id does not exist."""
        result = self.repo.delete(999)
        self.assertFalse(result)

    # ------------------------------------------------------------------
    # _create_or_get
    # ------------------------------------------------------------------

    def test_create_or_get_creates_new(self):
        """_create_or_get creates a new entity when none exists with that name."""
        result = self.repo._create_or_get(name="hotel")
        self.assertIsNotNone(result)
        self.assertIsInstance(result, Model)
        self.assertEqual(result.name, "hotel")
        self.assertIsNotNone(result.id)

    def test_create_or_get_returns_existing(self):
        """_create_or_get returns the same entity on repeated calls with the same name."""
        first = self.repo._create_or_get(name="india")
        second = self.repo._create_or_get(name="india")
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertEqual(first.id, second.id)


if __name__ == "__main__":
    unittest.main()
