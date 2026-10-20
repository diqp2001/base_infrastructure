"""Unit tests for the WW-NTBN hedging module.

Covers:
  - softclamp: bounds, midpoint, monotonicity, invalid range
  - WWNTBNHedgePolicy without weights: fallback to WW prior
  - WWNTBNHedgePolicy with synthetic weights: forward pass correctness,
    residual stays within softclamp bounds, output format
"""

import math
import tempfile
import unittest

import numpy as np

from src.application.managers.project_managers.market_making_SPX_call_spread_project.strategy.hedging.ww_ntbn import (
    WWNTBNHedgePolicy,
    softclamp,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project.strategy.hedging.rebalancing_bands import (
    whalley_wilmott_band,
)


# ---------------------------------------------------------------------------
# softclamp
# ---------------------------------------------------------------------------

class TestSoftclamp(unittest.TestCase):

    def test_output_strictly_within_bounds(self):
        # Use moderate x values — very large |x| saturates to the boundary in float64
        for x in (-3.0, -1.0, 0.0, 1.0, 3.0):
            y = softclamp(x, -1.0, 1.0)
            self.assertGreater(y, -1.0)
            self.assertLess(y, 1.0)

    def test_at_midpoint_returns_midpoint(self):
        mid = softclamp(0.0, -2.0, 2.0)
        self.assertAlmostEqual(mid, 0.0, places=10)

    def test_large_positive_approaches_upper(self):
        y = softclamp(1e6, -1.0, 1.0, beta=10.0)
        self.assertAlmostEqual(y, 1.0, places=4)

    def test_large_negative_approaches_lower(self):
        y = softclamp(-1e6, -1.0, 1.0, beta=10.0)
        self.assertAlmostEqual(y, -1.0, places=4)

    def test_monotone_increasing(self):
        xs = [-5.0, -1.0, 0.0, 1.0, 5.0]
        ys = [softclamp(x, -1.0, 1.0) for x in xs]
        for i in range(len(ys) - 1):
            self.assertLess(ys[i], ys[i + 1])

    def test_equal_bounds_returns_midpoint(self):
        y = softclamp(3.0, 2.0, 2.0)
        self.assertEqual(y, 2.0)

    def test_upper_less_than_lower_returns_midpoint(self):
        y = softclamp(0.0, 1.0, 0.0)
        self.assertEqual(y, 0.5)

    def test_higher_beta_sharper_transition(self):
        """Higher beta → output closer to bounds away from midpoint.
        Use x above midpoint (0.75 vs midpoint 0.5) so the effect is visible.
        """
        y_soft = softclamp(0.75, 0.0, 1.0, beta=1.0)
        y_hard = softclamp(0.75, 0.0, 1.0, beta=100.0)
        self.assertGreater(y_hard, y_soft)  # sharper → pushes toward 1.0


# ---------------------------------------------------------------------------
# WWNTBNHedgePolicy — no weights loaded (fallback path)
# ---------------------------------------------------------------------------

class TestWWNTBNFallback(unittest.TestCase):

    def setUp(self):
        self.policy = WWNTBNHedgePolicy()  # no weights

    def _typical_call(self, **kw):
        params = dict(
            gamma_net=2e-4,
            spot=4500.0,
            strike=4550.0,
            tau=0.1,
            vol=0.20,
            prev_hedge=0.0,
            r=0.05,
            cost_rate=1e-4,
            risk_aversion=1.0,
        )
        params.update(kw)
        return self.policy.compute_hedge(**params)

    def test_model_used_is_fallback_ww(self):
        result = self._typical_call()
        self.assertEqual(result['model_used'], 'ww_ntbn_fallback_ww')

    def test_half_width_equals_ww_prior(self):
        result = self._typical_call()
        expected_ww = whalley_wilmott_band(
            gamma=2e-4, spot=4500.0, cost_rate=1e-4, risk_aversion=1.0,
            time_to_expiry=0.1, risk_free_rate=0.05,
        )
        self.assertAlmostEqual(result['half_width'], expected_ww, places=12)

    def test_residual_is_zero(self):
        result = self._typical_call()
        self.assertEqual(result['residual'], 0.0)

    def test_result_has_required_keys(self):
        result = self._typical_call()
        for k in ('half_width', 'model_used', 'ww_prior', 'residual'):
            self.assertIn(k, result)

    def test_zero_gamma_returns_zero_band(self):
        result = self._typical_call(gamma_net=0.0)
        self.assertEqual(result['half_width'], 0.0)

    def test_positive_half_width_for_normal_params(self):
        result = self._typical_call()
        self.assertGreater(result['half_width'], 0.0)

    def test_bad_weights_path_still_falls_back(self):
        policy = WWNTBNHedgePolicy(weights_path='/nonexistent/path.npz')
        result = policy.compute_hedge(
            gamma_net=2e-4, spot=4500.0, strike=4550.0, tau=0.1,
            vol=0.20, prev_hedge=0.0, r=0.05, cost_rate=1e-4, risk_aversion=1.0,
        )
        self.assertEqual(result['model_used'], 'ww_ntbn_fallback_ww')


# ---------------------------------------------------------------------------
# WWNTBNHedgePolicy — synthetic weights (forward pass path)
# ---------------------------------------------------------------------------

def _make_zero_weights_npz() -> str:
    """Write a 6-layer (5 hidden + 1 output) zero-weight MLP to a temp file.

    Zero weights produce zero pre-activations throughout, so outputs = bias
    of the final layer = 0.  The residual correction is 0 and the half-width
    equals ww_prior (after softclamp centres at 0).
    """
    path = tempfile.mktemp(suffix='.npz')
    arrays = {}
    in_dim = WWNTBNHedgePolicy.INPUT_DIM
    hidden = WWNTBNHedgePolicy.HIDDEN_DIM
    out_dim = WWNTBNHedgePolicy.OUTPUT_DIM
    n_hidden = WWNTBNHedgePolicy.HIDDEN_LAYERS

    # 5 hidden layers
    for i in range(n_hidden):
        d_in = in_dim if i == 0 else hidden
        arrays[f'W{i}'] = np.zeros((hidden, d_in))
        arrays[f'b{i}'] = np.zeros(hidden)
    # output layer
    arrays[f'W{n_hidden}'] = np.zeros((out_dim, hidden))
    arrays[f'b{n_hidden}'] = np.zeros(out_dim)

    np.savez(path, **arrays)
    return path


def _make_identity_like_weights_npz() -> str:
    """Weights that pass through non-trivially; used to check model_used label."""
    path = tempfile.mktemp(suffix='.npz')
    arrays = {}
    in_dim = WWNTBNHedgePolicy.INPUT_DIM
    hidden = WWNTBNHedgePolicy.HIDDEN_DIM
    out_dim = WWNTBNHedgePolicy.OUTPUT_DIM
    n_hidden = WWNTBNHedgePolicy.HIDDEN_LAYERS
    rng = np.random.default_rng(42)

    for i in range(n_hidden):
        d_in = in_dim if i == 0 else hidden
        arrays[f'W{i}'] = rng.normal(0, 0.01, (hidden, d_in))
        arrays[f'b{i}'] = np.zeros(hidden)
    arrays[f'W{n_hidden}'] = rng.normal(0, 0.01, (out_dim, hidden))
    arrays[f'b{n_hidden}'] = np.zeros(out_dim)

    np.savez(path, **arrays)
    return path


class TestWWNTBNWithWeights(unittest.TestCase):

    def setUp(self):
        self.zero_path = _make_zero_weights_npz()
        self.rand_path = _make_identity_like_weights_npz()

    def _policy(self, path) -> WWNTBNHedgePolicy:
        return WWNTBNHedgePolicy(weights_path=path)

    def _call(self, policy, **kw):
        params = dict(
            gamma_net=2e-4, spot=4500.0, strike=4550.0, tau=0.1,
            vol=0.20, prev_hedge=0.0, r=0.05, cost_rate=1e-4, risk_aversion=1.0,
        )
        params.update(kw)
        return policy.compute_hedge(**params)

    def test_zero_weights_model_used_is_ww_ntbn(self):
        result = self._call(self._policy(self.zero_path))
        self.assertEqual(result['model_used'], 'ww_ntbn')

    def test_zero_weights_residual_near_zero(self):
        """Zero-weight MLP → outputs = 0 → softclamp(0, -h, h) = 0 → residual ≈ 0."""
        result = self._call(self._policy(self.zero_path))
        self.assertAlmostEqual(result['residual'], 0.0, places=8)

    def test_zero_weights_half_width_equals_ww_prior(self):
        result = self._call(self._policy(self.zero_path))
        self.assertAlmostEqual(result['half_width'], result['ww_prior'], places=8)

    def test_rand_weights_model_used_is_ww_ntbn(self):
        result = self._call(self._policy(self.rand_path))
        self.assertEqual(result['model_used'], 'ww_ntbn')

    def test_half_width_is_nonnegative(self):
        for path in (self.zero_path, self.rand_path):
            result = self._call(self._policy(path))
            self.assertGreaterEqual(result['half_width'], 0.0)

    def test_residual_bounded_by_ww_prior(self):
        """|residual| <= ww_prior because softclamp bounds are ±ww_prior."""
        result = self._call(self._policy(self.rand_path))
        self.assertLessEqual(abs(result['residual']), result['ww_prior'] + 1e-10)

    def test_output_keys_present(self):
        result = self._call(self._policy(self.zero_path))
        for k in ('half_width', 'model_used', 'ww_prior', 'residual'):
            self.assertIn(k, result)

    def test_loaded_flag_set_on_valid_file(self):
        policy = self._policy(self.zero_path)
        self.assertTrue(policy._loaded)

    def test_loaded_flag_false_without_file(self):
        policy = WWNTBNHedgePolicy()
        self.assertFalse(policy._loaded)


if __name__ == '__main__':
    unittest.main()
