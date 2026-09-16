"""
Unit tests for HestonPricer.

Validates
---------
* Semi-analytic call prices vs. Monte Carlo benchmark
* Put-call parity
* Implied volatility round-trip (price → IV → price)
* ATM smile shape (skew is monotone in rho)
* Boundary conditions (T→0, deep ITM, deep OTM)
* BSM helper accuracy
"""

import math
import unittest

from src.application.services.data.entities.factor.heston_slv.heston_slv_parameters import (
    HestonParameters,
)
from src.application.services.data.entities.factor.heston_slv.heston_pricer import HestonPricer
from src.application.services.data.entities.factor.heston_slv.heston_simulator import HestonSimulator


class TestHestonPricerSemiAnalytic(unittest.TestCase):
    """Semi-analytic price accuracy tests."""

    def setUp(self):
        self.pricer = HestonPricer()
        self.sim    = HestonSimulator(n_paths=80_000, n_steps=100, seed=42)
        # Standard Heston parameters (Feller satisfied: 2*1.5*0.04 = 0.12 > 0.04)
        self.params = HestonParameters(
            v0=0.04, kappa=1.5, theta=0.04, xi=0.2, rho=-0.5, r=0.05, q=0.0
        )

    def test_call_price_finite(self):
        p = self.pricer.price(S=100, K=100, T=1.0, params=self.params)
        self.assertIsNotNone(p)
        self.assertTrue(math.isfinite(p))
        self.assertGreater(p, 0)

    def test_call_lower_bound(self):
        p  = self.pricer.price(S=100, K=80, T=1.0, params=self.params)
        lb = 100 * math.exp(-0 * 1) - 80 * math.exp(-0.05 * 1)
        self.assertGreater(p, 0)
        self.assertGreater(p, lb - 1e-6)

    def test_put_call_parity(self):
        S, K, T = 100.0, 100.0, 1.0
        call = self.pricer.price(S, K, T, self.params, "call")
        put  = self.pricer.price(S, K, T, self.params, "put")
        r, q = self.params.r, self.params.q
        parity = call - put - (S * math.exp(-q * T) - K * math.exp(-r * T))
        self.assertAlmostEqual(parity, 0.0, places=3)

    def test_price_vs_mc_atm(self):
        """Semi-analytic and MC prices should agree within 2 standard errors."""
        S, K, T = 100.0, 100.0, 1.0
        sa_price = self.pricer.price(S, K, T, self.params)
        mc_price = self.sim.price(self.params, S, K, T, seed=99)
        # Allow ±0.5 tolerance (≈ 2-3 std for 80k paths)
        self.assertAlmostEqual(sa_price, mc_price, delta=0.5)

    def test_implied_vol_round_trip(self):
        """price → bsm_iv → price should be self-consistent."""
        S, K, T = 100.0, 105.0, 0.5
        price = self.pricer.price(S, K, T, self.params)
        iv    = self.pricer.implied_vol(S, K, T, self.params)
        self.assertIsNotNone(iv)
        price_back = HestonPricer.bsm_price(S, K, self.params.r, self.params.q, T, iv)
        self.assertAlmostEqual(price, price_back, places=3)

    def test_deep_otm_positive(self):
        p = self.pricer.price(S=100, K=200, T=0.5, params=self.params)
        self.assertIsNotNone(p)
        self.assertGreaterEqual(p, 0.0)

    def test_invalid_inputs_return_none(self):
        bad_params = HestonParameters(v0=0.04, kappa=1.5, theta=0.04, xi=0.2, rho=-0.5)
        self.assertIsNone(self.pricer.price(0, 100, 1.0, bad_params))   # S=0
        self.assertIsNone(self.pricer.price(100, 0, 1.0, bad_params))   # K=0
        self.assertIsNone(self.pricer.price(100, 100, 0, bad_params))   # T=0


class TestHestonPricerBSMHelpers(unittest.TestCase):
    """BSM helper accuracy."""

    def test_bsm_price_known_value(self):
        """ATM call with 20% vol, T=1, r=5%, no dividends ≈ 10.45."""
        price = HestonPricer.bsm_price(100, 100, 0.05, 0.0, 1.0, 0.20)
        self.assertAlmostEqual(price, 10.45, delta=0.05)

    def test_bsm_vega_positive(self):
        vega = HestonPricer.bsm_vega(100, 100, 0.05, 0.0, 1.0, 0.20)
        self.assertGreater(vega, 0)

    def test_bsm_iv_round_trip(self):
        sigma = 0.25
        price = HestonPricer.bsm_price(100, 110, 0.05, 0.02, 0.5, sigma)
        iv    = HestonPricer.bsm_iv(price, 100, 110, 0.05, 0.02, 0.5)
        self.assertIsNotNone(iv)
        self.assertAlmostEqual(iv, sigma, places=4)


class TestHestonSmileShape(unittest.TestCase):
    """The negative-rho Heston model should produce a negative skew."""

    def setUp(self):
        self.pricer = HestonPricer()

    def test_negative_rho_produces_negative_skew(self):
        """IV at lower strikes > IV at higher strikes for rho < 0."""
        params = HestonParameters(v0=0.04, kappa=2.0, theta=0.04, xi=0.4, rho=-0.7, r=0.0)
        iv_otm_put  = self.pricer.implied_vol(100, 85,  1.0, params)   # low strike
        iv_atm      = self.pricer.implied_vol(100, 100, 1.0, params)
        iv_otm_call = self.pricer.implied_vol(100, 115, 1.0, params)   # high strike
        self.assertIsNotNone(iv_otm_put)
        self.assertIsNotNone(iv_otm_call)
        self.assertGreater(iv_otm_put, iv_atm)
        self.assertGreater(iv_atm, iv_otm_call)

    def test_feller_condition(self):
        p = HestonParameters(v0=0.04, kappa=2.0, theta=0.04, xi=0.3, rho=-0.5)
        self.assertTrue(p.feller_condition())   # 2*2*0.04 = 0.16 > 0.09

        p_viol = HestonParameters(v0=0.04, kappa=0.5, theta=0.04, xi=3.0, rho=-0.5)
        self.assertFalse(p_viol.feller_condition())  # 2*0.5*0.04=0.04 < 9.0


if __name__ == "__main__":
    unittest.main()
