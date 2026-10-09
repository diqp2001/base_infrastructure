"""Model tests: dimensions, one output per asset, determinism, batch sizes, reference layout."""

import unittest

import torch

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_models import (
    MODEL_MAPPING,
    SpatioTemporalMomentumNet,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_training import set_seed


def _net(model_type, n=5, f=8, t=12):
    return SpatioTemporalMomentumNet(n, f, t, model_type=model_type,
                                     encoder_length=8 if model_type == "tft" else None)


class TestModels(unittest.TestCase):

    def test_every_reference_architecture_outputs_one_signal_per_asset(self):
        for model_type in MODEL_MAPPING:
            with self.subTest(model=model_type):
                net = _net(model_type).eval()
                x = torch.randn(3, 5, 12, 8)
                self.assertEqual(tuple(net(x).shape), (3, 5))
                expected_steps = 4 if model_type == "tft" else 12
                self.assertEqual(tuple(net.forward_sequence(x).shape), (3, expected_steps, 5))

    def test_different_batch_sizes(self):
        net = _net("tft").eval()
        for b in (1, 2, 17, 64):
            self.assertEqual(tuple(net(torch.randn(b, 5, 12, 8)).shape), (b, 5))

    def test_seeded_construction_and_inference_are_deterministic(self):
        x = torch.randn(4, 5, 12, 8)
        set_seed(42)
        a = _net("tft").eval()(x)
        set_seed(42)
        b = _net("tft").eval()(x)
        torch.testing.assert_close(a, b)

    def test_wrapper_feeds_reference_asset_major_layout(self):
        """[B,N,T,F] must become [B,T,N*F] with asset_0's features first (reference concatenation)."""
        net = _net("slp", n=3, f=2, t=4)
        x = torch.arange(3 * 4 * 2, dtype=torch.float32).reshape(1, 3, 4, 2)
        flat = net._to_reference_layout(x)
        self.assertEqual(tuple(flat.shape), (1, 4, 6))
        for t in range(4):
            expected = torch.cat([x[0, a, t, :] for a in range(3)])
            torch.testing.assert_close(flat[0, t], expected)

    def test_cross_sectional_dependency(self):
        """Changing one asset's input changes other assets' signals (joint universe model)."""
        set_seed(0)
        net = _net("tft").eval()
        x = torch.randn(1, 5, 12, 8)
        y0 = net(x)
        x2 = x.clone()
        x2[0, 0] += 3.0
        y1 = net(x2)
        self.assertFalse(torch.allclose(y0[0, 1:], y1[0, 1:]))

    def test_shape_validation(self):
        net = _net("tft")
        with self.assertRaises(ValueError):
            net(torch.randn(2, 4, 12, 8))   # wrong number of assets


if __name__ == "__main__":
    unittest.main()
