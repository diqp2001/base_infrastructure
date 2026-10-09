"""Training tests: loss parity with the reference, a small synthetic training run, evaluation."""

import unittest

import numpy as np
import torch

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_backtest import (
    captured_returns,
    evaluate_with_baselines,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_dataset import (
    build_feature_panel,
    make_split,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_losses import sharpe_loss
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_metrics import (
    max_drawdown,
    sharpe_ratio,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_models import build_model
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_training import (
    predict_last_step,
    train_window,
)
from tests.spatio_temporal_momentum.helpers import ASSETS, synthetic_closes, tiny_config


class TestLossAndMetrics(unittest.TestCase):

    def test_sharpe_loss_is_negative_mean_asset_sharpe(self):
        torch.manual_seed(0)
        preds = torch.randn(16, 5, 3)
        rets = torch.randn(16, 5, 3) * 0.01
        R = (preds * rets).numpy()
        per_asset = []
        for a in range(3):
            r = R[:, :, a].ravel()
            per_asset.append(-np.sqrt(252) * r.mean() / np.sqrt((r ** 2).mean() - r.mean() ** 2 + 1e-9))
        self.assertAlmostEqual(sharpe_loss(preds, rets).item(), float(np.mean(per_asset)), places=5)

    def test_metrics(self):
        r = np.array([0.01, -0.02, 0.015, 0.0, 0.005])
        self.assertAlmostEqual(sharpe_ratio(r), r.mean() / r.std(ddof=1) * np.sqrt(252), places=10)
        self.assertAlmostEqual(max_drawdown(np.array([0.1, -0.5, 0.2])), -0.5, places=10)

    def test_turnover_costs_reduce_returns(self):
        preds = np.array([[1.0, -1.0], [-1.0, 1.0], [1.0, -1.0]])
        rets = np.full((3, 2), 0.001)
        vols = np.full((3, 2), 0.01)
        self.assertTrue((captured_returns(preds, rets, vols, 10) < captured_returns(preds, rets, vols, 0)).all())


class TestTraining(unittest.TestCase):

    def test_small_synthetic_training_completes(self):
        cfg = tiny_config()
        panel = build_feature_panel(synthetic_closes(1000), cfg.features)
        split = make_split(panel, "2016-09-01", cfg)
        res = train_window(lambda: build_model(len(ASSETS), 8, cfg.model), split.train, split.val, cfg.training)
        self.assertEqual(res.epochs_run, cfg.training.n_epochs)
        self.assertTrue(res.state_dict)
        net = build_model(len(ASSETS), 8, cfg.model)
        net.load_state_dict(res.state_dict)
        preds = predict_last_step(net, split.test, 16)
        self.assertEqual(preds.shape, (len(split.test), len(ASSETS)))
        evaluation = evaluate_with_baselines(preds, split.test, panel.feature_names)
        self.assertEqual(set(evaluation), {"stm", "long_only", "tsmom", "csmom", "macd"})
        self.assertIn(5, evaluation["stm"]["by_cost"])

    def test_training_is_reproducible_with_the_same_seed(self):
        cfg = tiny_config(model_type="mlp")
        cfg.training.n_epochs = 2
        panel = build_feature_panel(synthetic_closes(1000), cfg.features)
        split = make_split(panel, "2016-09-01", cfg)
        a = train_window(lambda: build_model(len(ASSETS), 8, cfg.model), split.train, split.val, cfg.training)
        b = train_window(lambda: build_model(len(ASSETS), 8, cfg.model), split.train, split.val, cfg.training)
        for k in a.state_dict:
            torch.testing.assert_close(a.state_dict[k], b.state_dict[k])


if __name__ == "__main__":
    unittest.main()
