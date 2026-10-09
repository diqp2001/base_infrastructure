"""
Look-ahead bias tests.

Each test builds a "future" that would dramatically change the answer
(prices x10 after the decision date) and checks that nothing computed for
the decision date moves: features, normalisation, model input, artifact
selection, signals, and the signal/return date alignment.
"""

import shutil
import tempfile
import unittest

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_artifact_store import (
    STMArtifactStore,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_backtest import (
    captured_returns,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_dataset import (
    build_feature_panel,
    build_inference_input,
    make_split,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_model_provider import (
    SpatioTemporalMomentumModelProvider,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_walk_forward import (
    STMWalkForwardTrainer,
)
from tests.spatio_temporal_momentum.helpers import (
    ASSETS,
    make_factory,
    overwrite_closes_after,
    seed_closes,
    synthetic_closes,
    tiny_config,
)

ENTITY_IDS = {a: 100 + i for i, a in enumerate(ASSETS)}


def _shock_future(closes: pd.DataFrame, after, factor: float = 10.0) -> pd.DataFrame:
    shocked = closes.copy()
    shocked.loc[shocked.index > pd.Timestamp(after)] *= factor
    return shocked


class TestNoLookAheadPure(unittest.TestCase):

    def setUp(self):
        self.cfg = tiny_config()
        self.closes = synthetic_closes(1000)
        self.d = self.closes.index[700]

    def test_features_at_or_before_decision_date_ignore_the_future(self):
        base = build_feature_panel(self.closes, self.cfg.features)
        shocked = build_feature_panel(_shock_future(self.closes, self.d), self.cfg.features)
        i = base.index_at_or_before(self.d)
        np.testing.assert_array_equal(base.features[: i + 1], shocked.features[: i + 1])
        np.testing.assert_array_equal(base.daily_vol[: i + 1], shocked.daily_vol[: i + 1])
        self.assertFalse(np.allclose(base.features[i + 2], shocked.features[i + 2], equal_nan=True),
                         "sanity: the shock does change later features")

    def test_inference_tensor_ignores_the_future(self):
        base = build_feature_panel(self.closes, self.cfg.features)
        shocked = build_feature_panel(_shock_future(self.closes, self.d), self.cfg.features)
        x0, d0 = build_inference_input(base, self.d, 12)
        x1, d1 = build_inference_input(shocked, self.d, 12)
        self.assertEqual(d0, self.d)
        np.testing.assert_array_equal(x0, x1)

    def test_truncated_history_gives_the_same_inference_input(self):
        """Inference with data only up to D equals inference with the full history."""
        full = build_feature_panel(self.closes, self.cfg.features)
        truncated = build_feature_panel(self.closes.loc[: self.d], self.cfg.features)
        np.testing.assert_array_equal(build_inference_input(full, self.d, 12)[0],
                                      build_inference_input(truncated, self.d, 12)[0])

    def test_scaler_is_fitted_on_training_rows_only(self):
        self.cfg.training.scaling = "standard"
        start = "2016-09-01"
        base = make_split(build_feature_panel(self.closes, self.cfg.features), start, self.cfg)
        shocked = make_split(build_feature_panel(_shock_future(self.closes, start), self.cfg.features),
                             start, self.cfg)
        np.testing.assert_allclose(base.scaler["a"], shocked.scaler["a"])
        np.testing.assert_allclose(base.scaler["b"], shocked.scaler["b"])
        np.testing.assert_array_equal(base.train.X, shocked.train.X)

    def test_training_labels_never_reach_past_the_split_start(self):
        panel = build_feature_panel(self.closes, self.cfg.features)
        split = make_split(panel, "2016-09-01", self.cfg)
        last = panel.dates.get_loc(split.train.dates[-1])
        self.assertLessEqual(panel.dates[last + self.cfg.prediction_horizon], pd.Timestamp("2016-09-01"))

    def test_signal_at_t_earns_the_return_from_t_to_t_plus_1(self):
        """An oracle that knows tomorrow's sign earns a high Sharpe only through the label alignment."""
        panel = build_feature_panel(self.closes, self.cfg.features)
        rows = slice(400, 900)
        labels = panel.target[rows]
        oracle = np.sign(labels)
        realised = captured_returns(oracle, labels, panel.daily_vol[rows], 0)
        self.assertTrue((realised > 0).all())
        # the same oracle shifted to use only information up to t has no edge
        lagged = np.sign(np.vstack([np.zeros((1, labels.shape[1])), labels[:-1]]))
        self.assertLess(abs(np.mean(captured_returns(lagged, labels, panel.daily_vol[rows], 0))),
                        np.mean(realised) / 5)


class TestNoLookAheadWithDatabase(unittest.TestCase):

    def setUp(self):
        SpatioTemporalMomentumModelProvider.clear_cache()
        self.tmp = tempfile.mkdtemp()
        self.cfg = tiny_config(tmp_dir=self.tmp)
        self.factory, self.session, self.engine = make_factory()
        self.closes = synthetic_closes(1000)
        self.close_factor_id = seed_closes(self.session, self.closes, ENTITY_IDS)
        panel = build_feature_panel(self.closes, self.cfg.features)
        self.results = STMWalkForwardTrainer(self.cfg, factory=self.factory).run(panel, ENTITY_IDS)

    def tearDown(self):
        SpatioTemporalMomentumModelProvider.clear_cache()
        self.session.close()
        self.engine.dispose()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_signals_do_not_change_when_stored_future_prices_change(self):
        d = self.results[0].test.dates[10]
        before = SpatioTemporalMomentumModelProvider(factory=self.factory, config=self.cfg).score_universe(d)
        overwrite_closes_after(self.session, self.close_factor_id, ENTITY_IDS, d, multiplier=10.0)
        SpatioTemporalMomentumModelProvider.clear_cache()
        after = SpatioTemporalMomentumModelProvider(factory=self.factory, config=self.cfg).score_universe(d)
        self.assertTrue(before)
        for eid in before:
            self.assertAlmostEqual(before[eid], after[eid], places=10)

    def test_artifact_selected_for_a_date_never_saw_that_date(self):
        store = STMArtifactStore(self.factory, self.cfg)
        for r in self.results:
            for d in r.test.dates:
                artifact, meta = store.select(d)
                self.assertLess(pd.Timestamp(meta["validation_end"]), d)
                self.assertLessEqual(pd.Timestamp(meta["training_end"]), pd.Timestamp(meta["validation_end"]))
        for r in self.results:
            for d in r.val.dates:
                selected = store.select(d)
                if selected is not None:
                    self.assertLess(pd.Timestamp(selected[1]["validation_end"]), d)


if __name__ == "__main__":
    unittest.main()
