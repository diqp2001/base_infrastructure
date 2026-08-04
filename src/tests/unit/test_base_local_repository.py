"""
Unit tests for BaseLocalRepository.

Uses ModelRepository (backtest) as the concrete implementation with an
in-memory SQLite database.  Methods that ModelRepository overrides
(add, get_all, update) are called explicitly on the base class so that
the base-class behaviour is what is under test.
"""
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ModelBase must be imported first so that all shared models (FactorModel etc.)
# are registered before the backtest ORM models that depend on them.
from src.infrastructure.models import ModelBase

# Explicit imports register these tables with ModelBase.metadata.
# They are NOT imported by src/infrastructure/models/__init__.py.
from src.infrastructure.models.backtest.model import ModelModel              # noqa: F401
from src.infrastructure.models.backtest.backtest import BacktestModel        # noqa: F401
from src.infrastructure.models.backtest.universe import UniverseModel        # noqa: F401
from src.infrastructure.models.backtest.backtest_factor_backtest import (    # noqa: F401
    BacktestFactorBacktestModel,
)

from src.infrastructure.repositories.local_repo.base_repository import BaseLocalRepository
from src.infrastructure.repositories.local_repo.backtest.model_repository import ModelRepository


class TestBaseLocalRepository(unittest.TestCase):
    """Tests for the shared CRUD methods defined in BaseLocalRepository."""

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
    # add  (calls BaseLocalRepository.add directly — ModelRepository overrides it)
    # ------------------------------------------------------------------

    def test_add_persists_model(self):
        """BaseLocalRepository.add saves an ORM model and makes it retrievable."""
        orm_model = ModelModel(id=1, name="test")
        returned = BaseLocalRepository.add(self.repo, orm_model)
        self.assertIsNotNone(returned)
        retrieved = self.session.get(ModelModel, 1)
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.name, "test")

    # ------------------------------------------------------------------
    # get  (not overridden in ModelRepository)
    # ------------------------------------------------------------------

    def test_get_returns_correct_model(self):
        """get returns the ORM model whose primary key matches the given id."""
        self.session.add(ModelModel(id=1, name="hello"))
        self.session.commit()
        result = self.repo.get(1)
        self.assertIsNotNone(result)
        self.assertEqual(result.id, 1)
        self.assertEqual(result.name, "hello")

    def test_get_returns_none_for_missing(self):
        """get returns None when no record exists for the given id."""
        result = self.repo.get(999)
        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # update  (ModelRepository overrides with different signature;
    #          we call the base-class version explicitly)
    # ------------------------------------------------------------------

    def test_update_changes_fields(self):
        """BaseLocalRepository.update applies the supplied updates dict."""
        self.session.add(ModelModel(id=1, name="original"))
        self.session.commit()
        result = BaseLocalRepository.update(self.repo, 1, {"name": "updated"})
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "updated")
        # Confirm the change was committed to the DB.
        fresh = self.session.get(ModelModel, 1)
        self.assertEqual(fresh.name, "updated")

    def test_update_returns_none_for_missing(self):
        """BaseLocalRepository.update returns None when the id does not exist."""
        result = BaseLocalRepository.update(self.repo, 999, {"name": "x"})
        self.assertIsNone(result)

    # ------------------------------------------------------------------
    # delete  (ModelRepository.delete has the same observable behaviour
    #          as the base, so calling self.repo.delete is fine here)
    # ------------------------------------------------------------------

    def test_delete_removes_model(self):
        """delete removes the record; a subsequent get returns None."""
        self.session.add(ModelModel(id=1, name="to_delete"))
        self.session.commit()
        success = self.repo.delete(1)
        self.assertTrue(success)
        self.assertIsNone(self.repo.get(1))

    def test_delete_returns_false_for_missing(self):
        """delete returns False when no record exists for the given id."""
        result = self.repo.delete(999)
        self.assertFalse(result)

    # ------------------------------------------------------------------
    # get_all  (ModelRepository overrides to return domain entities;
    #           call the base version to test the ORM-level behaviour)
    # ------------------------------------------------------------------

    def test_get_all_returns_all(self):
        """BaseLocalRepository.get_all returns every ORM model in the table."""
        for i, name in enumerate(["m1", "m2", "m3"], start=1):
            self.session.add(ModelModel(id=i, name=name))
        self.session.commit()
        results = BaseLocalRepository.get_all(self.repo)
        self.assertEqual(len(results), 3)

    def test_get_all_empty(self):
        """BaseLocalRepository.get_all returns an empty list when the table is empty."""
        results = BaseLocalRepository.get_all(self.repo)
        self.assertEqual(results, [])

    # ------------------------------------------------------------------
    # _get_next_available_id  (not overridden)
    # ------------------------------------------------------------------

    def test_get_next_available_id_empty_table(self):
        """_get_next_available_id returns 1 when the table contains no rows."""
        result = self.repo._get_next_available_id()
        self.assertEqual(result, 1)

    def test_get_next_available_id_with_records(self):
        """_get_next_available_id returns max_id + 1 when rows already exist."""
        self.session.add(ModelModel(id=5, name="anchor"))
        self.session.commit()
        result = self.repo._get_next_available_id()
        self.assertEqual(result, 6)


if __name__ == "__main__":
    unittest.main()
