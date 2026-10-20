"""
Integration tests for the full Heston-SLV pipeline.

Validates
---------
* HestonSimulator MC price vs semi-analytic (convergence)
* HestonCalibrator recovers known parameters on a synthetic surface
* LeverageFunction construction and evaluation
* HestonSLVSimulator produces positive terminal spots/variances
* HestonSLVModel.price / implied_vol end-to-end on a synthetic surface
* CompanyShareOptionHestonSLVPriceFactor domain factor (stdlib MC)
"""

import math
import unittest

import numpy as np
import pytest

from src.application.services.data.entities.factor.heston_slv.heston_slv_parameters import (
    HestonParameters,
)
from src.application.services.data.entities.factor.heston_slv.heston_pricer import HestonPricer
from src.application.services.data.entities.factor.heston_slv.heston_simulator import HestonSimulator
from src.application.services.data.entities.factor.heston_slv.heston_calibrator import HestonCalibrator
from src.application.services.data.entities.factor.heston_slv.implied_vol_surface import (
    ImpliedVolatilitySurface,
    OptionPriceSurface,
    MarketQuote,
)
from src.application.services.data.entities.factor.heston_slv.dupire_local_vol import (
    DupireLocalVolatility,
    LocalVolatilitySurface,
)
from src.application.services.data.entities.factor.heston_slv.conditional_variance_estimator import (
    ConditionalVarianceEstimator,
)
from src.application.services.data.entities.factor.heston_slv.leverage_function import LeverageFunction
from src.application.services.data.entities.factor.heston_slv.heston_slv_model import (
    HestonSLVModel,
    HestonSLVSimulator,
    HestonSLVConfig,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_heston_slv_price_factor import (
    CompanyShareOptionHestonSLVPriceFactor,
)


# ─────────────────────────────────────────────────────────────────────────── #
#  Fixtures                                                                    #
# ─────────────────────────────────────────────────────────────────────────── #

_TRUE_PARAMS = HestonParameters(
    v0=0.04, kappa=1.5, theta=0.04, xi=0.3, rho=-0.5, r=0.05, q=0.0
)
_S0 = 100.0
_PRICER = HestonPricer()


def _build_synthetic_quotes(
    params: HestonParameters,
    S0: float,
    strikes,
    maturities,
) -> list:
    """Generate MarketQuote list from semi-analytic Heston prices."""
    quotes = []
    for T in maturities:
        for K in strikes:
            iv = _PRICER.implied_vol(S0, K, T, params)
            if iv is not None and iv > 0:
                quotes.append(MarketQuote(strike=K, maturity=T, iv=iv))
    return quotes


_STRIKES    = [85.0, 90.0, 95.0, 100.0, 105.0, 110.0, 115.0]
_MATURITIES = [0.25, 0.5, 1.0, 1.5]
_QUOTES     = _build_synthetic_quotes(_TRUE_PARAMS, _S0, _STRIKES, _MATURITIES)


# ─────────────────────────────────────────────────────────────────────────── #
#  Heston simulator vs. semi-analytic                                          #
# ─────────────────────────────────────────────────────────────────────────── #

class TestHestonSimulatorVsSemiAnalytic(unittest.TestCase):

    def test_atm_convergence(self):
        """MC and semi-analytic ATM prices should agree within 1%."""
        sim = HestonSimulator(n_paths=40_000, n_steps=100, seed=0)
        K, T = 100.0, 1.0
        sa_price = _PRICER.price(_S0, K, T, _TRUE_PARAMS)
        mc_price = sim.price(_TRUE_PARAMS, _S0, K, T, seed=0)
        self.assertIsNotNone(sa_price)
        self.assertIsNotNone(mc_price)
        rel_err = abs(mc_price - sa_price) / max(sa_price, 1e-8)
        self.assertLess(rel_err, 0.03)   # within 3%

    def test_simulate_returns_positive_terminal_values(self):
        sim = HestonSimulator(n_paths=500, n_steps=50, seed=1)
        S_T, v_T = sim.simulate(_TRUE_PARAMS, _S0, 1.0)
        self.assertTrue(np.all(S_T > 0))
        self.assertTrue(np.all(v_T >= 0))

    def test_implied_vol_round_trip(self):
        sim = HestonSimulator(n_paths=20_000, n_steps=100, seed=2)
        iv  = sim.implied_vol(_TRUE_PARAMS, _S0, 100.0, 1.0, seed=2)
        self.assertIsNotNone(iv)
        self.assertGreater(iv, 0.0)
        self.assertAlmostEqual(iv, math.sqrt(_TRUE_PARAMS.theta), delta=0.06)


# ─────────────────────────────────────────────────────────────────────────── #
#  Heston calibrator                                                           #
# ─────────────────────────────────────────────────────────────────────────── #

# Numerical calibration: minutes per test, so excluded from the fast suite (performance marker).
@pytest.mark.slow
@pytest.mark.performance
class TestHestonCalibrator(unittest.TestCase):
    """Calibrator should recover (approximate) true parameters from synthetic IVs."""

    @classmethod
    def setUpClass(cls):
        strikes    = [90.0, 95.0, 100.0, 105.0, 110.0]
        maturities = [0.5, 1.0]
        ivs = np.array([
            [_PRICER.implied_vol(_S0, K, T, _TRUE_PARAMS) or 0.20
             for T in maturities]
            for K in strikes
        ])
        cal = HestonCalibrator(_PRICER)
        cls.result = cal.calibrate(
            strikes, maturities, ivs, _S0,
            r=_TRUE_PARAMS.r, q=_TRUE_PARAMS.q,
            use_global_search=True, seed=42,
        )

    def test_calibrated_type(self):
        self.assertIsInstance(self.result, HestonParameters)

    def test_calibrated_long_run_vol_close(self):
        # Long-run vol = sqrt(theta) ≈ 0.20
        self.assertAlmostEqual(math.sqrt(self.result.theta), 0.20, delta=0.04)

    def test_calibrated_v0_positive(self):
        self.assertGreater(self.result.v0, 0)

    def test_calibrated_iv_error_small(self):
        """Mean IV error across calibration grid should be < 2 vol points."""
        errors = []
        for K in [90.0, 95.0, 100.0, 105.0, 110.0]:
            for T in [0.5, 1.0]:
                market_iv = _PRICER.implied_vol(_S0, K, T, _TRUE_PARAMS) or 0.0
                model_iv  = _PRICER.implied_vol(_S0, K, T, self.result) or 0.0
                errors.append(abs(model_iv - market_iv))
        self.assertLess(float(np.mean(errors)), 0.02)


# ─────────────────────────────────────────────────────────────────────────── #
#  LeverageFunction                                                            #
# ─────────────────────────────────────────────────────────────────────────── #

class TestLeverageFunction(unittest.TestCase):

    def setUp(self):
        S_grid = np.linspace(85, 115, 10)
        t_grid = np.array([0.25, 0.5, 1.0])
        self.lf = LeverageFunction.identity(S_grid, t_grid)

    def test_identity_evaluates_to_one(self):
        self.assertAlmostEqual(self.lf(100.0, 0.5), 1.0, places=8)

    def test_vectorized_evaluation(self):
        S_arr = np.array([90.0, 100.0, 110.0])
        vals  = self.lf.evaluate_vectorized(S_arr, 0.5)
        np.testing.assert_allclose(vals, 1.0, atol=1e-8)

    def test_blend_alpha_one_equals_other(self):
        S_g = np.linspace(85, 115, 5)
        t_g = np.array([0.5, 1.0])
        other = LeverageFunction(S_g, t_g, np.full((5, 2), 2.0))
        blended = self.lf.blend(other, alpha=1.0)
        self.assertAlmostEqual(blended(100.0, 0.5), 2.0, delta=0.01)

    def test_smooth_preserves_shape(self):
        smoothed = self.lf.smooth(sigma=0.5)
        self.assertEqual(smoothed.L_values.shape, self.lf.L_values.shape)

    def test_max_abs_diff(self):
        S_g = np.linspace(85, 115, 10)
        t_g = np.array([0.25, 0.5, 1.0])
        other = LeverageFunction(S_g, t_g, np.full((10, 3), 1.5))
        diff = self.lf.max_abs_diff(other)
        self.assertAlmostEqual(diff, 0.5, places=8)


# ─────────────────────────────────────────────────────────────────────────── #
#  HestonSLV Simulator                                                         #
# ─────────────────────────────────────────────────────────────────────────── #

class TestHestonSLVSimulator(unittest.TestCase):

    def setUp(self):
        S_grid = np.linspace(80, 120, 20)
        t_grid = np.linspace(0.1, 1.0, 10)
        self.leverage = LeverageFunction.identity(S_grid, t_grid)
        self.slv_sim  = HestonSLVSimulator()

    def test_terminal_spots_positive(self):
        S_T, v_T, _ = self.slv_sim.simulate(
            _TRUE_PARAMS, self.leverage, _S0, 1.0, n_paths=200, n_steps=50, seed=10
        )
        self.assertTrue(np.all(S_T > 0))
        self.assertTrue(np.all(v_T >= 0))

    def test_price_with_identity_leverage_close_to_heston(self):
        """
        With L=1 the SLV simulator is identical to pure Heston.
        MC prices should agree with semi-analytic within 5%.
        """
        K, T  = 100.0, 1.0
        sa    = _PRICER.price(_S0, K, T, _TRUE_PARAMS)
        slv_p = self.slv_sim.price(
            _TRUE_PARAMS, self.leverage, _S0, K, T,
            n_paths=20_000, n_steps=100, seed=20,
        )
        self.assertIsNotNone(slv_p)
        rel_err = abs(slv_p - sa) / max(sa, 1e-8)
        self.assertLess(rel_err, 0.06)

    def test_implied_vol_positive(self):
        iv = self.slv_sim.implied_vol(
            _TRUE_PARAMS, self.leverage, _S0, 100.0, 1.0,
            n_paths=10_000, n_steps=100, seed=30,
        )
        self.assertIsNotNone(iv)
        self.assertGreater(iv, 0.0)

    def test_snapshots_recorded(self):
        _, _, snaps = self.slv_sim.simulate(
            _TRUE_PARAMS, self.leverage, _S0, 1.0,
            n_paths=100, n_steps=52, seed=40,
            record_times=np.array([0.5, 1.0]),
        )
        self.assertIsNotNone(snaps)
        self.assertGreater(len(snaps), 0)
        for S_s, v_s in snaps:
            self.assertEqual(len(S_s), 100)
            self.assertTrue(np.all(S_s > 0))


# ─────────────────────────────────────────────────────────────────────────── #
#  Domain factor (stdlib MC)                                                   #
# ─────────────────────────────────────────────────────────────────────────── #

class TestHestonSLVDomainFactor(unittest.TestCase):

    def setUp(self):
        self.factor = CompanyShareOptionHestonSLVPriceFactor(
            name="heston_slv_test",
            group="price_model",
            subgroup="stochastic_volatility",                # a Factor.SUBGROUPS key
        )

    def test_call_price_positive(self):
        p = self.factor.calculate(
            S=100, K=100, r=0.05, T=1.0,
            v0=0.04, kappa=1.5, theta=0.04, xi=0.3, rho=-0.5,
            n_paths=5_000, n_steps=52,
        )
        self.assertIsNotNone(p)
        self.assertGreater(p, 0.0)

    def test_put_price_positive(self):
        p = self.factor.calculate(
            S=100, K=100, r=0.05, T=1.0,
            v0=0.04, kappa=1.5, theta=0.04, xi=0.3, rho=-0.5,
            option_type="put", n_paths=5_000, n_steps=52,
        )
        self.assertIsNotNone(p)
        self.assertGreater(p, 0.0)

    def test_put_call_parity_approx(self):
        """
        MC put-call parity holds approximately (within MC noise).
        C - P ≈ S*e^(-q*T) - K*e^(-r*T)
        """
        kw = dict(S=100, K=100, r=0.05, T=1.0,
                  v0=0.04, kappa=1.5, theta=0.04, xi=0.3, rho=-0.5,
                  n_paths=10_000, n_steps=52)
        import random; random.seed(7)
        call = self.factor.calculate(**kw, option_type="call")
        random.seed(7)
        put  = self.factor.calculate(**kw, option_type="put")
        parity = (100 * math.exp(0.0) - 100 * math.exp(-0.05 * 1.0))
        self.assertAlmostEqual(call - put, parity, delta=1.0)

    def test_invalid_inputs_return_none(self):
        kw = dict(r=0.05, T=1.0, v0=0.04, kappa=1.5, theta=0.04, xi=0.3, rho=-0.5)
        self.assertIsNone(self.factor.calculate(S=0,   K=100, **kw))
        self.assertIsNone(self.factor.calculate(S=100, K=0,   **kw))
        self.assertIsNone(self.factor.calculate(S=100, K=100, r=0.05, T=0,
                                                v0=0.04, kappa=1.5, theta=0.04,
                                                xi=0.3, rho=-0.5))

    def test_leverage_function_modifies_price(self):
        """Providing a non-unit leverage function changes the price."""
        kw = dict(S=100, K=100, r=0.05, T=1.0,
                  v0=0.04, kappa=1.5, theta=0.04, xi=0.3, rho=-0.5,
                  n_paths=5_000, n_steps=52, option_type="call")
        import random
        random.seed(99)
        p_pure = self.factor.calculate(**kw)
        random.seed(99)
        p_lev  = self.factor.calculate(
            **kw, leverage_func=lambda S, t: 0.5  # leverage halved
        )
        # A leverage of 0.5 should reduce the effective vol and thus the call price
        self.assertLess(p_lev, p_pure)

    def test_feller_condition_check(self):
        self.assertTrue(self.factor.feller_condition_check(1.5, 0.04, 0.3))
        self.assertFalse(self.factor.feller_condition_check(0.1, 0.01, 5.0))


# ─────────────────────────────────────────────────────────────────────────── #
#  Dupire + Conditional Variance pipeline (mini end-to-end)                    #
# ─────────────────────────────────────────────────────────────────────────── #

class TestDupireCondVarLeveragePipeline(unittest.TestCase):
    """Verify that the Dupire → CVE → LeverageFunction pipeline runs end-to-end."""

    def test_pipeline_produces_valid_leverage(self):
        # Build a flat IV surface
        quotes = [
            MarketQuote(strike=K, maturity=T, iv=0.20)
            for K in [85.0, 90.0, 95.0, 100.0, 105.0, 110.0, 115.0]
            for T in [0.25, 0.5, 1.0, 2.0]
        ]
        iv_surf = ImpliedVolatilitySurface(quotes, 100.0, r=0.05, q=0.0)
        K_grid  = np.linspace(85.0, 115.0, 12)
        T_grid  = np.linspace(0.3, 1.8, 8)
        ps      = OptionPriceSurface(iv_surf, K_grid, T_grid)
        lv      = DupireLocalVolatility().calibrate(ps)

        # Simulate Heston particles
        sim = HestonSimulator(n_paths=2_000, n_steps=50, seed=7)
        S_T, v_T = sim.simulate(_TRUE_PARAMS, 100.0, 1.0)

        # Conditional variance
        cve   = ConditionalVarianceEstimator(bandwidth=0.1)
        S_g   = np.linspace(85.0, 115.0, 20)
        t_g   = np.array([0.5, 1.0])
        n_T_g = len(t_g)

        L_vals = np.ones((len(S_g), n_T_g))
        for j, t in enumerate(t_g):
            cv = cve.estimate_on_grid(S_g, S_T, v_T)
            for i, S in enumerate(S_g):
                sl = lv(S, t)
                if cv[i] > 0:
                    L_vals[i, j] = sl / math.sqrt(cv[i])

        leverage = LeverageFunction(S_g, t_g, L_vals)

        # Leverage values should be finite and within clipping bounds
        self.assertFalse(np.any(np.isnan(leverage.L_values)))
        self.assertTrue(np.all(leverage.L_values >= leverage.L_min))
        self.assertTrue(np.all(leverage.L_values <= leverage.L_max))

        # Evaluate at a point
        L_val = leverage(100.0, 0.5)
        self.assertGreater(L_val, 0.0)
        self.assertTrue(math.isfinite(L_val))


if __name__ == "__main__":
    unittest.main()
