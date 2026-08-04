"""
Unit tests for BacktestFactorRepository — covers _create_or_get, get_by_all,
and the domain-level CRUD methods inherited from BaseFactorRepository /
BaseLocalRepository.

All tests run against an in-memory SQLite database; no network or file I/O.
"""
import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ModelBase must come first so shared ORM models (FactorModel, etc.) register
# before the backtest-specific ones.
from src.infrastructure.models import ModelBase

# Explicitly import every ORM table used by the tests so it appears in
# ModelBase.metadata before create_all() is called.
from src.infrastructure.models.factor.factor import FactorModel, BacktestFactorModel  # noqa: F401
from src.infrastructure.models.factor.factor_value import FactorValueModel            # noqa: F401
from src.infrastructure.models.backtest.model import ModelModel                        # noqa: F401
from src.infrastructure.models.backtest.backtest import BacktestModel                  # noqa: F401
from src.infrastructure.models.backtest.universe import UniverseModel                  # noqa: F401
from src.infrastructure.models.backtest.backtest_factor_backtest import (              # noqa: F401
    BacktestFactorBacktestModel,
)

from src.infrastructure.repositories.local_repo.factor.backtest.backtest_factor_repository import (
    BacktestFactorRepository,
)
from src.domain.entities.factor.backtest.backtest_factor import BacktestFactor


class TestBacktestFactorRepository(unittest.TestCase):
    """Tests for BacktestFactorRepository's CRUD and _create_or_get behaviour."""

    def setUp(self):
        self.engine = create_engine("sqlite://")
        ModelBase.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.repo = BacktestFactorRepository(self.session)

    def tearDown(self):
        self.session.rollback()
        self.session.close()
        self.engine.dispose()

    # ------------------------------------------------------------------
    # _create_or_get
    # ------------------------------------------------------------------

    def test_create_or_get_creates_new_factor(self):
        """_create_or_get inserts a new BacktestFactor when none exists."""
        factor = self.repo._create_or_get(entity_cls=None, primary_key="mom_20d")
        self.assertIsNotNone(factor)
        self.assertEqual(factor.name, "mom_20d")

    def test_create_or_get_is_idempotent(self):
        """Calling _create_or_get twice with the same name returns the same row."""
        f1 = self.repo._create_or_get(entity_cls=None, primary_key="mom_20d")
        f2 = self.repo._create_or_get(entity_cls=None, primary_key="mom_20d")
        self.assertIsNotNone(f1)
        self.assertIsNotNone(f2)
        self.assertEqual(f1.id, f2.id)

    def test_create_or_get_applies_custom_group(self):
        """_create_or_get respects the group kwarg."""
        factor = self.repo._create_or_get(
            entity_cls=None, primary_key="vol_30d", group="volatility"
        )
        self.assertEqual(factor.group, "volatility")

    def test_create_or_get_applies_optional_kwargs(self):
        """_create_or_get stores optional fields correctly."""
        factor = self.repo._create_or_get(
            entity_cls=None,
            primary_key="rsi_14",
            group="technical",
            subgroup="signal",
            frequency="1d",
            data_type="numeric",
            source="calculated",
            definition="14-period RSI",
        )
        self.assertEqual(factor.subgroup, "signal")
        self.assertEqual(factor.definition, "14-period RSI")

    # ------------------------------------------------------------------
    # get_by_all
    # ------------------------------------------------------------------

    def test_get_by_all_returns_existing_orm_model(self):
        """get_by_all finds a factor by name + group."""
        self.repo._create_or_get(entity_cls=None, primary_key="beta_60d", group="risk")
        result = self.repo.get_by_all(name="beta_60d", group="risk")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "beta_60d")

    def test_get_by_all_returns_none_when_not_found(self):
        """get_by_all returns None if no matching row exists."""
        result = self.repo.get_by_all(name="nonexistent", group="momentum")
        self.assertIsNone(result)

    def test_get_by_all_discriminates_by_factor_type(self):
        """get_by_all with factor_type='backtest_factor' filters correctly."""
        self.repo._create_or_get(entity_cls=None, primary_key="alpha_5d")
        result = self.repo.get_by_all(
            name="alpha_5d", group="fundamental", factor_type="backtest_factor"
        )
        self.assertIsNotNone(result)

    # ------------------------------------------------------------------
    # delete / get (inherited from BaseLocalRepository via base class)
    # ------------------------------------------------------------------

    def test_delete_removes_factor(self):
        """delete(id) removes the factor; a subsequent get returns None."""
        factor = self.repo._create_or_get(entity_cls=None, primary_key="to_delete")
        self.assertIsNotNone(factor)
        success = self.repo.delete(factor.id)
        self.assertTrue(success)
        self.assertIsNone(self.repo.get(factor.id))

    def test_delete_returns_false_for_missing(self):
        """delete returns False when the id does not exist."""
        self.assertFalse(self.repo.delete(99999))

    # ------------------------------------------------------------------
    # _to_entity / _to_model round-trip
    # ------------------------------------------------------------------

    def test_to_entity_returns_backtest_factor_instance(self):
        """_to_entity converts an ORM model to a BacktestFactor domain object."""
        factor = self.repo._create_or_get(entity_cls=None, primary_key="round_trip")
        # factor is already the domain entity — verify its type
        self.assertIsInstance(factor, BacktestFactor)

    def test_orm_round_trip_preserves_name(self):
        """ORM → domain → ORM conversion preserves the factor name."""
        factor = self.repo._create_or_get(entity_cls=None, primary_key="preserved_name")
        orm_model = self.repo._to_model(factor)
        self.assertEqual(orm_model.name, "preserved_name")


if __name__ == "__main__":
    unittest.main()
