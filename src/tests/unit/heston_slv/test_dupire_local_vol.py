"""
Unit tests for the Dupire local-volatility pipeline.

Covers
------
* ImpliedVolatilitySurface interpolation
* OptionPriceSurface call prices and derivatives
* DupireLocalVolatility.compute_point numerical sanity
* LocalVolatilitySurface interpolation and extrapolation
* Flat surface → flat local vol (Dupire consistency check)
"""

import math
import unittest

import numpy as np

from src.application.services.data.entities.factor.heston_slv.implied_vol_surface import (
    ImpliedVolatilitySurface,
    OptionPriceSurface,
    MarketQuote,
    _bsm_call,
)
from src.application.services.data.entities.factor.heston_slv.dupire_local_vol import (
    DupireLocalVolatility,
    LocalVolatilitySurface,
)


def _flat_surface(S0=100.0, sigma=0.20, r=0.05, q=0.0, n_strikes=7, n_mats=5):
    """Build a flat IV surface at constant sigma."""
    strikes    = np.linspace(80, 120, n_strikes)
    maturities = np.linspace(0.25, 2.0, n_mats)
    quotes = [
        MarketQuote(strike=K, maturity=T, iv=sigma)
        for K in strikes
        for T in maturities
    ]
    return ImpliedVolatilitySurface(quotes, S0, r, q)


class TestImpliedVolatilitySurface(unittest.TestCase):

    def setUp(self):
        self.surface = _flat_surface()

    def test_interpolation_at_node(self):
        iv = self.surface.iv(100.0, 0.5)
        self.assertAlmostEqual(iv, 0.20, places=2)

    def test_interpolation_off_node(self):
        iv = self.surface.iv(95.0, 0.75)
        self.assertGreater(iv, 0.0)
        self.assertTrue(math.isfinite(iv))

    def test_extrapolation_does_not_crash(self):
        # Outside calibrated range
        iv = self.surface.iv(50.0, 5.0)
        self.assertGreater(iv, 0.0)

    def test_call_price_positive(self):
        c = self.surface.call_price(100.0, 1.0)
        self.assertGreater(c, 0.0)

    def test_T_max_attribute(self):
        self.assertAlmostEqual(self.surface.T_max, 2.0, places=6)


class TestOptionPriceSurface(unittest.TestCase):

    def setUp(self):
        iv_surface = _flat_surface()
        strikes    = np.linspace(85.0, 115.0, 10)
        maturities = np.linspace(0.3, 1.8, 8)
        self.ps    = OptionPriceSurface(iv_surface, strikes, maturities)

    def test_price_positive(self):
        p = self.ps.price(100.0, 1.0)
        self.assertGreater(p, 0.0)

    def test_dC_dT_positive(self):
        # Time value of a call is increasing in T
        dT = self.ps.dC_dT(100.0, 1.0)
        self.assertGreater(dT, 0.0)

    def test_dC_dK_negative(self):
        # Call delta w.r.t. strike is negative (price falls as K rises)
        dK = self.ps.dC_dK(100.0, 1.0)
        self.assertLess(dK, 0.0)

    def test_d2C_dK2_positive(self):
        # Butterfly condition: second derivative should be positive (convexity)
        d2 = self.ps.d2C_dK2(100.0, 1.0)
        self.assertGreater(d2, 0.0)


class TestDupireLocalVolatility(unittest.TestCase):

    def test_flat_surface_gives_flat_local_vol(self):
        """
        For a flat IV surface sigma_imp = sigma_0,
        the Dupire local vol should also be ≈ sigma_0.
        """
        sigma0     = 0.20
        iv_surface = _flat_surface(sigma=sigma0, n_strikes=12, n_mats=8)
        strikes    = np.linspace(85.0, 115.0, 12)
        maturities = np.linspace(0.3, 1.8, 8)
        ps         = OptionPriceSurface(iv_surface, strikes, maturities)
        dupire     = DupireLocalVolatility(sigma_min=0.005, sigma_max=3.0)
        lv         = dupire.calibrate(ps)

        # Dupire local vol at ATM mid-maturity should be close to sigma0
        sigma_mid = lv(100.0, 1.0)
        self.assertAlmostEqual(sigma_mid, sigma0, delta=0.04)

    def test_local_vol_surface_clipped(self):
        iv_surface = _flat_surface()
        strikes    = np.linspace(85.0, 115.0, 8)
        maturities = np.linspace(0.3, 1.8, 6)
        ps         = OptionPriceSurface(iv_surface, strikes, maturities)
        dupire     = DupireLocalVolatility(sigma_min=0.01, sigma_max=2.0)
        lv         = dupire.calibrate(ps)

        for K in [90.0, 100.0, 110.0]:
            for T in [0.5, 1.0]:
                s = lv(K, T)
                self.assertGreaterEqual(s, 0.01)
                self.assertLessEqual(s, 2.0)


class TestLocalVolatilitySurface(unittest.TestCase):

    def _make_lv(self):
        K_grid = np.array([80.0, 90.0, 100.0, 110.0, 120.0])
        T_grid = np.array([0.25, 0.5, 1.0, 2.0])
        sigma  = np.full((5, 4), 0.20)
        return LocalVolatilitySurface(K_grid, T_grid, sigma)

    def test_interpolation_exact_node(self):
        lv = self._make_lv()
        self.assertAlmostEqual(lv(100.0, 1.0), 0.20, places=5)

    def test_extrapolation_clipped(self):
        lv = self._make_lv()
        # Outside grid → nearest-boundary extrapolation, within [sigma_min, sigma_max]
        val = lv(50.0, 0.1)
        self.assertGreaterEqual(val, lv.sigma_min)

    def test_smooth_does_not_change_shape(self):
        lv = self._make_lv()
        lv_s = lv.smooth(sigma=0.5)
        self.assertEqual(lv_s.sigma_grid.shape, lv.sigma_grid.shape)

    def test_evaluate_grid_shape(self):
        lv    = self._make_lv()
        S_g   = np.array([90.0, 100.0, 110.0])
        T_g   = np.array([0.5, 1.0])
        result = lv.evaluate_grid(S_g, T_g)
        self.assertEqual(result.shape, (3, 2))


if __name__ == "__main__":
    unittest.main()
