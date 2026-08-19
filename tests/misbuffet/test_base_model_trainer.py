"""Tests for misbuffet/engine/base_model_trainer.py — mocked DB, no real connections."""

import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

import pandas as pd

from src.application.services.misbuffet.engine.base_model_trainer import BaseModelTrainer


# ------------------------------------------------------------------
# Minimal concrete subclass for testing (BaseModelTrainer is ABC)
# ------------------------------------------------------------------

class _ConcreteTrainer(BaseModelTrainer):
    pass


def _make_trainer(config=None):
    db = MagicMock()
    db.session = MagicMock()
    cfg = config or {'factors': [], 'universe': {}}

    with (
        patch('src.application.services.misbuffet.engine.base_model_trainer.BaseDataLoader'),
        patch('src.application.services.misbuffet.engine.base_model_trainer.FactorManager'),
        patch('src.application.services.misbuffet.engine.base_model_trainer.FactorNormalizer'),
    ):
        return _ConcreteTrainer(db, cfg)


# ------------------------------------------------------------------
# Initialisation
# ------------------------------------------------------------------

class TestBaseModelTrainerInit(unittest.TestCase):

    def test_config_stored(self):
        cfg = {'factors': [], 'universe': {}, 'foo': 'bar'}
        trainer = _make_trainer(cfg)
        self.assertEqual(trainer.config, cfg)

    def test_training_config_defaults_to_empty(self):
        trainer = _make_trainer()
        self.assertEqual(trainer.training_config, {})

    def test_model_and_tensor_splitter_none(self):
        trainer = _make_trainer()
        self.assertIsNone(trainer.model)
        self.assertIsNone(trainer.tensor_splitter)

    def test_features_config_is_config(self):
        cfg = {'factors': []}
        trainer = _make_trainer(cfg)
        self.assertIs(trainer.features_config, trainer.config)


# ------------------------------------------------------------------
# _ensure_factors_exist
# ------------------------------------------------------------------

class TestEnsureFactorsExist(unittest.TestCase):

    def test_empty_factors_config(self):
        trainer = _make_trainer({'factors': [], 'universe': {}})
        result = trainer._ensure_factors_exist()
        self.assertIn('factors_created', result)
        self.assertEqual(result['factors_created'], 0)

    def test_returns_dict_with_error_key_on_exception(self):
        trainer = _make_trainer({'factors': [], 'universe': {}})
        # Force an exception inside _ensure_factors_exist by breaking create_factors
        trainer.create_factors = MagicMock(side_effect=RuntimeError("boom"))
        trainer.config['factors'] = [{'name': 'test_factor'}]
        result = trainer._ensure_factors_exist()
        self.assertIn('errors', result)
        self.assertTrue(len(result['errors']) > 0)


# ------------------------------------------------------------------
# create_factors
# ------------------------------------------------------------------

class TestCreateFactors(unittest.TestCase):

    def _trainer_with_mock_loader(self):
        trainer = _make_trainer()
        mock_entity = MagicMock()
        mock_entity.name = 'test_factor'
        trainer.data_loader.market_data_history_service._create_or_get.return_value = mock_entity
        return trainer, mock_entity

    def test_creates_factor_from_valid_config(self):
        trainer, mock_entity = self._trainer_with_mock_loader()
        factors_config = [{'name': 'momentum_1d', 'group': 'momentum', 'subgroup': 'daily'}]
        result = trainer.create_factors(factors_config)
        self.assertEqual(result['factors_created'], 1)
        self.assertEqual(len(result['factor_details']), 1)

    def test_skips_non_dict_entries(self):
        trainer, _ = self._trainer_with_mock_loader()
        result = trainer.create_factors(['not_a_dict', None, 42])
        self.assertEqual(result['factors_created'], 0)

    def test_skips_entries_without_name(self):
        trainer, _ = self._trainer_with_mock_loader()
        result = trainer.create_factors([{'group': 'price'}])
        self.assertEqual(result['factors_created'], 0)

    def test_records_error_on_failed_creation(self):
        trainer = _make_trainer()
        trainer.data_loader.market_data_history_service._create_or_get.return_value = None
        result = trainer.create_factors([{'name': 'bad_factor'}])
        self.assertEqual(result['factors_created'], 0)
        self.assertTrue(len(result['errors']) > 0)

    def test_multiple_factors(self):
        trainer, mock_entity = self._trainer_with_mock_loader()
        configs = [
            {'name': 'f1', 'group': 'price'},
            {'name': 'f2', 'group': 'momentum'},
            {'name': 'f3', 'group': 'technical'},
        ]
        result = trainer.create_factors(configs)
        self.assertEqual(result['factors_created'], 3)


# ------------------------------------------------------------------
# _prepare_factor_data (mocked service chain)
# ------------------------------------------------------------------

class TestPrepareFactorData(unittest.TestCase):

    def test_calls_set_frontier_and_batch_fetch(self):
        trainer = _make_trainer({'factors': [], 'universe': {}})
        trainer._ensure_factors_exist = MagicMock(return_value={
            'config_factor_details': [],
        })
        trainer.data_loader.market_data_history_service._create_or_get_factor_value_batch\
            .return_value = {}

        result = trainer._prepare_factor_data(datetime(2024, 1, 1), '1 day', '1 Y')

        trainer.data_loader.market_data_history_service.set_frontier.assert_called_once()
        trainer.data_loader.market_data_history_service._create_or_get_factor_value_batch\
            .assert_called_once()
        self.assertEqual(result, {})

    def test_uses_now_when_date_is_none(self):
        trainer = _make_trainer({'factors': [], 'universe': {}})
        trainer._ensure_factors_exist = MagicMock(return_value={'config_factor_details': []})
        trainer.data_loader.market_data_history_service._create_or_get_factor_value_batch\
            .return_value = {}

        # Should not raise even with date=None
        trainer._prepare_factor_data(None, '1 day', '1 Y')
        trainer.data_loader.market_data_history_service.set_frontier.assert_called_once()


if __name__ == '__main__':
    unittest.main()
