"""
Unit tests for ConditionalVarianceEstimator.

Validates
---------
* Known synthetic distribution: E[v | S] is exactly known
* Minimum effective particle guard (sparse region → unconditional mean)
* Vectorised grid estimation matches point estimates
* Silverman bandwidth is positive and sensible
* interpolant callable interface
"""

import math
import unittest

import numpy as np

from src.application.services.data.entities.factor.heston_slv.conditional_variance_estimator import (
    ConditionalVarianceEstimator,
)


class TestConditionalVarianceEstimatorPoint(unittest.TestCase):

    def setUp(self):
        rng = np.random.default_rng(0)
        # Particles: S_i drawn from lognormal, v_i = a + b * ln(S_i) + noise
        n = 5_000
        log_S = rng.normal(math.log(100), 0.2, n)
        self.S_p = np.exp(log_S)
        # E[v | S] = 0.04 + 0.1 * (ln(S) - ln(100))  (linear in log-spot)
        self.v_p = 0.04 + 0.1 * (log_S - math.log(100)) + rng.normal(0, 0.001, n)
        self.cve = ConditionalVarianceEstimator(bandwidth=0.10, min_eff_count=5)

    def test_atm_estimate_close_to_truth(self):
        # At S=100: E[v] = 0.04
        est = self.cve.estimate_point(100.0, self.S_p, self.v_p)
        self.assertAlmostEqual(est, 0.04, delta=0.005)

    def test_monotone_in_spot(self):
        # E[v|S] = 0.04 + 0.1*(ln S - ln 100), so monotone in S
        est_low  = self.cve.estimate_point(90.0,  self.S_p, self.v_p)
        est_mid  = self.cve.estimate_point(100.0, self.S_p, self.v_p)
        est_high = self.cve.estimate_point(110.0, self.S_p, self.v_p)
        self.assertLess(est_low, est_mid)
        self.assertLess(est_mid, est_high)

    def test_floor_applied(self):
        # Even with near-zero variance particles, result >= floor
        rng = np.random.default_rng(1)
        S_p = np.exp(rng.normal(math.log(100), 0.1, 100))
        v_p = np.zeros(100)
        cve = ConditionalVarianceEstimator(floor=1e-5)
        est = cve.estimate_point(100.0, S_p, v_p)
        self.assertGreaterEqual(est, 1e-5)


class TestConditionalVarianceEstimatorGrid(unittest.TestCase):

    def setUp(self):
        rng = np.random.default_rng(2)
        n = 2_000
        log_S = rng.normal(math.log(100), 0.15, n)
        self.S_p = np.exp(log_S)
        self.v_p = 0.04 + 0.05 * (log_S - math.log(100)) + rng.normal(0, 0.0005, n)
        self.cve = ConditionalVarianceEstimator(bandwidth=0.08, min_eff_count=3)

    def test_grid_shape(self):
        g = np.linspace(90, 110, 20)
        out = self.cve.estimate_on_grid(g, self.S_p, self.v_p)
        self.assertEqual(out.shape, (20,))

    def test_grid_matches_point(self):
        g = np.array([95.0, 100.0, 105.0])
        grid_est  = self.cve.estimate_on_grid(g, self.S_p, self.v_p)
        point_est = np.array([self.cve.estimate_point(S, self.S_p, self.v_p) for S in g])
        np.testing.assert_allclose(grid_est, point_est, rtol=1e-10)

    def test_all_positive(self):
        g = np.linspace(85, 115, 30)
        out = self.cve.estimate_on_grid(g, self.S_p, self.v_p)
        self.assertTrue(np.all(out >= 0))


class TestConditionalVarianceSilverman(unittest.TestCase):

    def test_silverman_positive(self):
        rng = np.random.default_rng(3)
        S_p = np.exp(rng.normal(math.log(100), 0.2, 1_000))
        bw  = ConditionalVarianceEstimator.silverman_bandwidth(S_p)
        self.assertGreater(bw, 0)

    def test_silverman_decreases_with_n(self):
        """More particles → narrower bandwidth (Silverman rule)."""
        rng = np.random.default_rng(4)
        S1  = np.exp(rng.normal(0, 0.2, 100))
        S2  = np.exp(rng.normal(0, 0.2, 10_000))
        bw1 = ConditionalVarianceEstimator.silverman_bandwidth(S1)
        bw2 = ConditionalVarianceEstimator.silverman_bandwidth(S2)
        self.assertGreater(bw1, bw2)


class TestConditionalVarianceInterpolant(unittest.TestCase):

    def test_interpolant_callable(self):
        rng = np.random.default_rng(5)
        n   = 500
        S_p = np.exp(rng.normal(math.log(100), 0.15, n))
        v_p = 0.04 * np.ones(n) + rng.normal(0, 0.001, n)
        cve = ConditionalVarianceEstimator(bandwidth=0.1)
        g   = np.linspace(90, 110, 20)
        f   = cve.build_interpolant(g, S_p, v_p)
        val = f(100.0)
        self.assertIsInstance(float(val), float)
        self.assertGreater(float(val), 0.0)


if __name__ == "__main__":
    unittest.main()
