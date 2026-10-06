"""Feature tests: momentum horizons, vol normalisation, MACD, ordering, reference parity."""

import unittest

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMFeatureConfig,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_features import (
    compute_asset_features,
    winsorise_prices,
)
from tests.spatio_temporal_momentum.helpers import synthetic_closes


# ── Reference oracle: verbatim formulas of the reference src/features.py (with .bfill()) ──
def _ref_prepare(srs, half_winsore=252, vol_threshold=5, eps=1e-6):
    srs = srs.loc[(srs.notnull()) & (srs > eps)].copy()
    ewm = srs.ewm(halflife=half_winsore)
    means, stds = ewm.mean(), ewm.std()
    srs = np.minimum(srs, means + vol_threshold * stds)
    return np.maximum(srs, means - vol_threshold * stds)


def _ref_features(close):
    srs = _ref_prepare(close)
    df = pd.DataFrame({"srs": srs})
    df["daily_returns"] = df["srs"] / df["srs"].shift(1) - 1.0
    df["daily_vol"] = df["daily_returns"].ewm(span=60, min_periods=60).std().bfill()
    ann = df["daily_vol"] * np.sqrt(252)
    df["target_returns"] = (df["daily_returns"] * 0.15 / ann.shift(1)).shift(-1)
    for name, off in [("norm_daily_return", 1), ("norm_monthly_return", 21), ("norm_quarterly_return", 63),
                      ("norm_biannual_return", 126), ("norm_annual_return", 252)]:
        df[name] = (df["srs"] / df["srs"].shift(off) - 1.0) / df["daily_vol"] / np.sqrt(off)

    def halflife(t):
        return np.log(0.5) / (np.log(1 - 1 / t) + 1e-9)

    for s, l in [(8, 24), (16, 48), (32, 96)]:
        macd = df["srs"].ewm(halflife=halflife(s)).mean() - df["srs"].ewm(halflife=halflife(l)).mean()
        q = macd / (df["srs"].rolling(63).std().bfill() + 1e-9)
        df[f"macd_{s}_{l}"] = q / (q.rolling(252).std().bfill() + 1e-9)
    return df


class TestFeatureDefinitions(unittest.TestCase):

    def setUp(self):
        self.cfg = STMFeatureConfig()
        self.close = synthetic_closes(900)["AAA"]
        self.feats = compute_asset_features(self.close, self.cfg)
        self.srs = winsorise_prices(self.close, 252, 5.0).reindex(self.close.index)

    def test_feature_order_is_reference_order(self):
        self.assertEqual(self.cfg.feature_names(), [
            "norm_daily_return", "norm_monthly_return", "norm_quarterly_return",
            "norm_biannual_return", "norm_annual_return", "macd_8_24", "macd_16_48", "macd_32_96",
        ])
        self.assertEqual(list(self.feats.columns[:8]), self.cfg.feature_names())

    def test_momentum_horizons_are_vol_normalised_returns(self):
        t = 600
        vol = self.feats["daily_vol"].iloc[t]
        for h, name in zip((1, 21, 63, 126, 252), self.cfg.return_feature_names()):
            expected = (self.srs.iloc[t] / self.srs.iloc[t - h] - 1.0) / vol / np.sqrt(h)
            self.assertAlmostEqual(self.feats[name].iloc[t], expected, places=10, msg=name)

    def test_daily_vol_is_ewm_std_span_60(self):
        r = self.srs / self.srs.shift(1) - 1.0
        expected = r.ewm(span=60, min_periods=60).std()
        np.testing.assert_allclose(self.feats["daily_vol"].dropna(), expected.dropna(), rtol=1e-12)
        self.assertTrue(self.feats["daily_vol"].iloc[:60].isna().all(), "no back-filled vol")

    def test_target_is_next_day_return_scaled_by_vol_known_today(self):
        t = 500
        ann_vol = self.feats["daily_vol"].iloc[t] * np.sqrt(252)
        expected = (self.srs.iloc[t + 1] / self.srs.iloc[t] - 1.0) * 0.15 / ann_vol
        self.assertAlmostEqual(self.feats["target_returns"].iloc[t], expected, places=12)
        self.assertTrue(np.isnan(self.feats["target_returns"].iloc[-1]), "last label unknown")

    def test_matches_reference_on_every_causal_row(self):
        ref = _ref_features(self.close)
        first = 314  # first row whose 252-day MACD normalisation needs no back-fill
        for name in self.cfg.feature_names() + ["daily_vol", "target_returns"]:
            np.testing.assert_allclose(
                self.feats[name].iloc[first:].to_numpy(), ref[name].iloc[first:].to_numpy(),
                rtol=1e-9, atol=1e-12, err_msg=name,
            )

    def test_macd_rows_needing_backfill_are_left_missing(self):
        self.assertTrue(self.feats["macd_8_24"].iloc[:313].isna().all())
        self.assertFalse(np.isnan(self.feats["macd_8_24"].iloc[314]))


if __name__ == "__main__":
    unittest.main()
