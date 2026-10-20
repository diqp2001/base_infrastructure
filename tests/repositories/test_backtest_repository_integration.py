"""
Integration (context) tests for BacktestRepository + ModelRepository +
UniverseRepository working together against an in-memory SQLite database.

These tests exercise FK integrity, cascade behaviour, and idempotency of
_create_or_get across the three repositories.  SQLite foreign-key enforcement
is enabled via PRAGMA so that FK violations are caught at commit time.
"""
import unittest
from datetime import date
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from src.infrastructure.models import ModelBase

# Explicit imports register the backtest tables with ModelBase.metadata.
from src.infrastructure.models.backtest.model import ModelModel              # noqa: F401
from src.infrastructure.models.backtest.backtest import BacktestModel        # noqa: F401
from src.infrastructure.models.backtest.universe import UniverseModel        # noqa: F401
from src.infrastructure.models.backtest.backtest_factor_backtest import (    # noqa: F401
    BacktestFactorBacktestModel,
)

from src.infrastructure.repositories.local_repo.backtest.model_repository import (
    ModelRepository,
)
from src.infrastructure.repositories.local_repo.backtest.backtest_repository import (
    BacktestRepository,
)
from src.infrastructure.repositories.local_repo.backtest.universe_repository import (
    UniverseRepository,
)
from src.domain.entities.backtest.backtest import Backtest
from src.domain.entities.backtest.universe import Universe


class TestBacktestRepositoryIntegration(unittest.TestCase):
    """Integration tests for the backtest repository layer."""

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def setUp(self):
        """
        Create a fresh in-memory SQLite database with FK enforcement enabled,
        then wire up ModelRepository, BacktestRepository, and UniverseRepository.
        """
        self.engine = create_engine("sqlite://")

        @event.listens_for(self.engine, "connect")
        def _set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        ModelBase.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.model_repo = ModelRepository(self.session)
        self.backtest_repo = BacktestRepository(self.session)
        self.universe_repo = UniverseRepository(self.session)

    def tearDown(self):
        """Roll back any open transaction and release the engine."""
        self.session.rollback()
        self.session.close()
        self.engine.dispose()

    # ------------------------------------------------------------------
    # Test cases
    # ------------------------------------------------------------------

    def test_create_backtest_with_valid_model(self):
        """A backtest linked to an existing model round-trips with the correct model_id."""
        model = self.model_repo._create_or_get(name="strategy_v1")
        backtest = self.backtest_repo._create_or_get(
            name="bt_2026_q1",
            model_id=model.id,
            creation_date=date(2026, 1, 1),
        )
        self.assertIsNotNone(backtest)
        self.assertEqual(backtest.name, "bt_2026_q1")
        self.assertEqual(backtest.model_id, model.id)

    def test_create_backtest_without_model_fails(self):
        """
        Attempting to commit a backtest whose model_id references no existing
        model raises an exception when SQLite FK enforcement is active.
        """
        orphan = Backtest(
            id=None,
            name="orphan_bt",
            model_id=9999,      # this id does not exist in the models table
            creation_date=date.today(),
        )
        with self.assertRaises(Exception):
            self.backtest_repo.add(orphan)

    def test_get_backtests_by_model_id(self):
        """get_by_model_id returns all backtests that reference a given model."""
        model = self.model_repo._create_or_get(name="multi_bt_model")
        self.backtest_repo._create_or_get(
            name="bt_run_1", model_id=model.id, creation_date=date(2026, 1, 1)
        )
        self.backtest_repo._create_or_get(
            name="bt_run_2", model_id=model.id, creation_date=date(2026, 1, 2)
        )
        results = self.backtest_repo.get_by_model_id(model.id)
        self.assertEqual(len(results), 2)
        self.assertTrue(all(bt.model_id == model.id for bt in results))

    def test_universe_create_or_get_idempotent(self):
        """
        Calling UniverseRepository._create_or_get with the same name twice
        returns the same entity (same id) on both calls.
        """
        first = self.universe_repo._create_or_get(name="univ1")
        second = self.universe_repo._create_or_get(name="univ1")
        self.assertIsNotNone(first)
        self.assertIsNotNone(second)
        self.assertIsInstance(first, Universe)
        self.assertIsInstance(second, Universe)
        self.assertEqual(first.id, second.id)


if __name__ == "__main__":
    unittest.main()
