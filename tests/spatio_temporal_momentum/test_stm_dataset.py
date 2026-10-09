"""Dataset tests: tensor dimensions, asset / temporal ordering, missing data, splits."""

import unittest

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_dataset import (
    align_close_panel,
    build_feature_panel,
    build_inference_input,
    build_samples,
    make_split,
)
from tests.spatio_temporal_momentum.helpers import ASSETS, synthetic_closes, tiny_config


class TestDataset(unittest.TestCase):

    def setUp(self):
        self.cfg = tiny_config()
        self.closes = synthetic_closes(1000)
        self.panel = build_feature_panel(self.closes, self.cfg.features)

    def test_panel_shapes_and_order(self):
        self.assertEqual(self.panel.features.shape, (1000, len(ASSETS), 8))
        self.assertEqual(self.panel.assets, ASSETS)
        self.assertEqual(self.panel.feature_names, self.cfg.features.feature_names())
        self.assertTrue(self.panel.dates.is_monotonic_increasing)

    def test_sample_tensor_dimensions(self):
        split = make_split(self.panel, "2016-09-01", self.cfg)
        tr = split.train
        self.assertEqual(tr.X.shape[1:], (len(ASSETS), 12, 8))          # [S, N, T, F]
        self.assertEqual(tr.y.shape[1:], (12 - 8, len(ASSETS)))         # TFT decoder steps x assets
        self.assertEqual(len(tr.X), len(tr.y))

    def test_asset_and_temporal_ordering(self):
        i = 700
        s = build_samples(self.panel, [i], 12, 4)
        for a in range(len(ASSETS)):
            np.testing.assert_array_equal(s.X[0, a], self.panel.features[i - 11:i + 1, a, :])
        self.assertEqual(s.dates[0], self.panel.dates[i])
        # last row of the window is the decision date
        np.testing.assert_array_equal(s.X[0, :, -1, :], self.panel.features[i])

    def test_samples_before_warmup_are_excluded(self):
        s = build_samples(self.panel, list(range(0, 400)), 12, 4)
        self.assertTrue((s.dates >= self.panel.dates[self.panel.first_valid_row]).all())

    def test_missing_data_is_reported_not_filled(self):
        closes = self.closes.copy()
        closes.iloc[500, 2] = np.nan            # one missing close for CCC
        closes["EEE"] = np.nan                  # an asset with no history at all
        closes.loc[closes.index[:50], "EEE"] = 50.0
        aligned, report = align_close_panel(closes, required_rows=300)
        self.assertIn("EEE", report["dropped_assets_insufficient_history"])
        self.assertEqual(report["dropped_dates_missing_any_asset"], 1)
        self.assertFalse(aligned.isna().any().any())
        with self.assertRaises(ValueError):
            build_feature_panel(closes, self.cfg.features)  # unaligned panel is rejected

    def test_inference_window_rejects_missing_features(self):
        with self.assertRaises(ValueError):
            build_inference_input(self.panel, self.panel.dates[100], 12)  # inside warm-up

    def test_split_boundaries_and_purge(self):
        split = make_split(self.panel, "2016-09-01", self.cfg)
        start = pd.Timestamp("2016-09-01")
        self.assertTrue((split.train.dates <= start).all())
        self.assertTrue(((split.val.dates > start) & (split.val.dates <= split.val_end)).all())
        self.assertTrue(((split.test.dates > split.val_end) & (split.test.dates <= split.test_end)).all())
        # purge: the last training sample's label (next-day return) is realised on or before start
        last_train = split.train.dates[-1]
        next_day = self.panel.dates[self.panel.dates.get_loc(last_train) + 1]
        self.assertLessEqual(next_day, start)


if __name__ == "__main__":
    unittest.main()
