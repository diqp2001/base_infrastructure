"""Tests for misbuffet/data/factor_normalizer.py — pure utility methods, no DB required."""

import unittest
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from src.application.services.misbuffet.data.factor_normalizer import (
    FactorNormalizer,
    NormalizationConfig,
    NormalizationMethod,
    NormalizationScope,
)


def _make_normalizer() -> FactorNormalizer:
    """Build a FactorNormalizer with a fully mocked DatabaseService."""
    db = MagicMock()
    db.session = MagicMock()
    with patch(
        'src.application.services.misbuffet.data.factor_normalizer.CompanyShareRepositoryLocal',
        return_value=MagicMock(),
    ):
        return FactorNormalizer(db)


class TestNormalizationEnums(unittest.TestCase):

    def test_normalization_methods_exist(self):
        self.assertEqual(NormalizationMethod.Z_SCORE.value, 'z_score')
        self.assertEqual(NormalizationMethod.MIN_MAX.value, 'min_max')
        self.assertEqual(NormalizationMethod.RANK.value, 'rank')
        self.assertEqual(NormalizationMethod.QUANTILE.value, 'quantile')

    def test_normalization_scopes_exist(self):
        self.assertEqual(NormalizationScope.CROSS_SECTIONAL.value, 'cross_sectional')
        self.assertEqual(NormalizationScope.TIME_SERIES.value, 'time_series')
        self.assertEqual(NormalizationScope.GLOBAL.value, 'global')


class TestNormalizationConfig(unittest.TestCase):

    def test_defaults(self):
        cfg = NormalizationConfig(
            method=NormalizationMethod.Z_SCORE,
            scope=NormalizationScope.CROSS_SECTIONAL,
        )
        self.assertIsNone(cfg.lookback_periods)
        self.assertEqual(cfg.min_observations, 10)
        self.assertIsNone(cfg.winsorize_percentiles)

    def test_custom_values(self):
        cfg = NormalizationConfig(
            method=NormalizationMethod.MIN_MAX,
            scope=NormalizationScope.TIME_SERIES,
            lookback_periods=63,
            min_observations=5,
            winsorize_percentiles=(0.01, 0.99),
        )
        self.assertEqual(cfg.lookback_periods, 63)
        self.assertEqual(cfg.min_observations, 5)
        self.assertEqual(cfg.winsorize_percentiles, (0.01, 0.99))


class TestZscoreNormalize(unittest.TestCase):

    def setUp(self):
        self.fn = _make_normalizer()

    def test_mean_zero_std_one(self):
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = self.fn._zscore_normalize(values)
        self.assertAlmostEqual(np.mean(result), 0.0, places=10)
        self.assertAlmostEqual(np.std(result), 1.0, places=10)

    def test_constant_values_unchanged(self):
        values = np.array([3.0, 3.0, 3.0])
        result = self.fn._zscore_normalize(values)
        np.testing.assert_array_equal(result, values)

    def test_negative_values(self):
        values = np.array([-3.0, -1.0, 0.0, 1.0, 3.0])
        result = self.fn._zscore_normalize(values)
        self.assertAlmostEqual(np.mean(result), 0.0, places=10)


class TestMinMaxNormalize(unittest.TestCase):

    def setUp(self):
        self.fn = _make_normalizer()

    def test_range_zero_to_one(self):
        values = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        result = self.fn._minmax_normalize(values)
        self.assertAlmostEqual(result.min(), 0.0)
        self.assertAlmostEqual(result.max(), 1.0)

    def test_constant_values_unchanged(self):
        values = np.array([5.0, 5.0, 5.0])
        result = self.fn._minmax_normalize(values)
        np.testing.assert_array_equal(result, values)

    def test_two_distinct_values(self):
        values = np.array([0.0, 10.0])
        result = self.fn._minmax_normalize(values)
        self.assertAlmostEqual(result[0], 0.0)
        self.assertAlmostEqual(result[1], 1.0)


class TestRankNormalize(unittest.TestCase):

    def setUp(self):
        self.fn = _make_normalizer()

    def test_monotone_preserving(self):
        values = np.array([1.0, 2.0, 3.0, 4.0])
        result = self.fn._rank_normalize(values)
        # Ranks should be monotonically non-decreasing
        self.assertTrue(all(result[i] <= result[i + 1] for i in range(len(result) - 1)))

    def test_bounds_zero_to_one(self):
        values = np.array([10.0, 20.0, 30.0, 40.0, 50.0])
        result = self.fn._rank_normalize(values)
        self.assertAlmostEqual(result.min(), 0.0)
        self.assertAlmostEqual(result.max(), 1.0)


class TestWinsorize(unittest.TestCase):

    def setUp(self):
        self.fn = _make_normalizer()

    def test_clips_outliers(self):
        values = np.array([0.0, 1.0, 2.0, 3.0, 100.0])
        result = self.fn._winsorize(values, (0.01, 0.99))
        self.assertLess(result.max(), 100.0)

    def test_no_change_within_bounds(self):
        values = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        result = self.fn._winsorize(values, (0.0, 1.0))
        np.testing.assert_array_almost_equal(result, values)


class TestGetDefaultNormalizationConfigs(unittest.TestCase):

    def setUp(self):
        self.fn = _make_normalizer()

    def test_returns_dict(self):
        configs = self.fn._get_default_normalization_configs()
        self.assertIsInstance(configs, dict)

    def test_known_factors_present(self):
        configs = self.fn._get_default_normalization_configs()
        for factor in ('Close', 'deep_momentum_1d', 'norm_daily_return', 'macd_8_24'):
            self.assertIn(factor, configs)

    def test_all_values_are_config_objects(self):
        configs = self.fn._get_default_normalization_configs()
        for v in configs.values():
            self.assertIsInstance(v, NormalizationConfig)


if __name__ == '__main__':
    unittest.main()
