"""Tests for the four pluggable delta-calculation methods and supporting types.

Coverage
--------
* OptionMarketState / DeltaResult construction
* DeltaCalculationMethod BS helpers (_bs_delta, _bs_price, _d1_d2)
* BSMinimumVarianceDelta:  zero-coeff → pure BS, nonzero correction, from_fit
* fit_quadratic_coefficients: recovers known coefficients from synthetic data
* DiscreteRLHedgeDelta:  no-policy fallback, stub policy, out-of-range clamping
* ContinuousRLHedgeDelta:  no-policy fallback, stub policy, action clipping, 6D state
* VolForecastTriggeredBSDelta:  no-forecaster passthrough, all three trigger strategies,
  should_hedge flag, reset_history
* DeltaCalculationMethodFactory:  create all four, unknown name, register custom
"""

import math
import unittest
from typing import List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.bs_minimum_variance_delta import (
    BSMinimumVarianceDelta,
    fit_quadratic_coefficients,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.continuous_rl_hedge_delta import (
    ContinuousRLHedgeDelta,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.delta_calculation_method import (
    DeltaCalculationMethod,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.delta_calculation_method_factory import (
    DeltaCalculationMethodFactory,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.delta_result import (
    DeltaResult,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.discrete_rl_hedge_delta import (
    DiscreteRLHedgeDelta,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.option_market_state import (
    OptionMarketState,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.rebalancing_trigger import (
    RebalancingTrigger,
)
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.delta_calculation.vol_forecast_triggered_bs_delta import (
    VolForecastTriggeredBSDelta,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _atm_state(
    spot: float = 100.0,
    sigma: float = 0.20,
    tau: float = 0.25,
    r: float = 0.05,
    q: float = 0.0,
    hedge: float = 0.0,
    option_type: str = "call",
) -> OptionMarketState:
    return OptionMarketState(
        spot=spot,
        strike=spot,
        tau=tau,
        r=r,
        q=q,
        implied_vol=sigma,
        realized_vol=sigma,
        current_hedge_position=hedge,
        option_type=option_type,
    )


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _bs_delta_call(S, K, r, sigma, T, q=0.0) -> float:
    d1 = (math.log(S / K) + (r - q + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return math.exp(-q * T) * _norm_cdf(d1)


class StubDiscretePolicy:
    """Always returns a fixed action index."""
    def __init__(self, action_idx: int = 3):
        self._idx = action_idx

    def predict(self, obs):
        return self._idx


class StubContinuousPolicy:
    """Always returns a fixed float adjustment."""
    def __init__(self, adjustment: float = 0.05):
        self._adj = adjustment

    def predict(self, obs):
        return self._adj


class StubVolForecaster:
    """Always returns a fixed volatility forecast."""
    def __init__(self, vol: float = 0.25):
        self._vol = vol

    def predict(self, state):
        return self._vol


# ---------------------------------------------------------------------------
# OptionMarketState
# ---------------------------------------------------------------------------

class TestOptionMarketState(unittest.TestCase):

    def test_basic_construction(self):
        state = _atm_state()
        self.assertEqual(state.spot, 100.0)
        self.assertEqual(state.strike, 100.0)
        self.assertEqual(state.option_type, "call")
        self.assertIsNone(state.historical_returns)
        self.assertIsNone(state.prior_states)

    def test_put_option_type(self):
        state = _atm_state(option_type="put")
        self.assertEqual(state.option_type, "put")

    def test_optional_lists_set(self):
        state = OptionMarketState(
            spot=100, strike=100, tau=0.25, r=0.05, q=0.0,
            implied_vol=0.20, realized_vol=0.18,
            current_hedge_position=0.5,
            historical_returns=[0.01, -0.02, 0.03],
        )
        self.assertEqual(len(state.historical_returns), 3)


# ---------------------------------------------------------------------------
# DeltaResult
# ---------------------------------------------------------------------------

class TestDeltaResult(unittest.TestCase):

    def test_defaults(self):
        r = DeltaResult(delta=0.5, method_name="test")
        self.assertEqual(r.delta, 0.5)
        self.assertFalse(r.is_discrete)
        self.assertIsNone(r.should_hedge)
        self.assertEqual(r.diagnostics, {})

    def test_is_discrete_and_should_hedge(self):
        r = DeltaResult(delta=0.3, method_name="x", is_discrete=True, should_hedge=False)
        self.assertTrue(r.is_discrete)
        self.assertFalse(r.should_hedge)


# ---------------------------------------------------------------------------
# BSMinimumVarianceDelta
# ---------------------------------------------------------------------------

class TestBSMinimumVarianceDelta(unittest.TestCase):

    def test_zero_coefficients_matches_bs_delta_call(self):
        state = _atm_state(spot=100, sigma=0.20, tau=0.25, r=0.05)
        method = BSMinimumVarianceDelta(a=0, b=0, c=0)
        result = method.compute_delta(state)
        expected = _bs_delta_call(100, 100, 0.05, 0.20, 0.25)
        self.assertAlmostEqual(result.delta, expected, places=10)

    def test_zero_coefficients_matches_bs_delta_put(self):
        state = _atm_state(option_type="put")
        method = BSMinimumVarianceDelta()
        result = method.compute_delta(state)
        expected = _bs_delta_call(100, 100, 0.05, 0.20, 0.25) - 1.0
        self.assertAlmostEqual(result.delta, expected, places=10)

    def test_nonzero_a_shifts_delta(self):
        state = _atm_state()
        base = BSMinimumVarianceDelta().compute_delta(state).delta
        shifted = BSMinimumVarianceDelta(a=0.5).compute_delta(state).delta
        # a > 0 should increase delta (positive phi_weight * a)
        self.assertGreater(shifted, base)

    def test_nonzero_a_negative_reduces_delta(self):
        state = _atm_state()
        base = BSMinimumVarianceDelta().compute_delta(state).delta
        shifted = BSMinimumVarianceDelta(a=-0.5).compute_delta(state).delta
        self.assertLess(shifted, base)

    def test_method_name(self):
        self.assertEqual(BSMinimumVarianceDelta().method_name, "bs_minimum_variance")

    def test_diagnostics_contains_delta_bs(self):
        result = BSMinimumVarianceDelta().compute_delta(_atm_state())
        self.assertIn("delta_bs", result.diagnostics)
        self.assertIn("correction", result.diagnostics)

    def test_is_discrete_false(self):
        result = BSMinimumVarianceDelta().compute_delta(_atm_state())
        self.assertFalse(result.is_discrete)

    def test_invalid_inputs_returns_fallback(self):
        bad_state = OptionMarketState(
            spot=-1, strike=100, tau=0.25, r=0.05, q=0.0,
            implied_vol=0.20, realized_vol=0.20, current_hedge_position=0.0,
        )
        result = BSMinimumVarianceDelta().compute_delta(bad_state)
        self.assertIn("error", result.diagnostics)

    def test_with_dividend_yield(self):
        state = _atm_state(q=0.02)
        result = BSMinimumVarianceDelta().compute_delta(state)
        # delta < N(d1) because of exp(-q*T) discount
        expected = _bs_delta_call(100, 100, 0.05, 0.20, 0.25, q=0.02)
        self.assertAlmostEqual(result.delta, expected, places=10)

    def test_from_fit_classmethod(self):
        bs_deltas = [0.3, 0.4, 0.5, 0.6, 0.7]
        corrections = [0.02, 0.03, 0.04, 0.03, 0.02]
        method = BSMinimumVarianceDelta.from_fit(bs_deltas, corrections)
        self.assertIsInstance(method, BSMinimumVarianceDelta)

    def test_deep_itm_call_delta_near_one(self):
        state = OptionMarketState(
            spot=200, strike=100, tau=0.25, r=0.05, q=0.0,
            implied_vol=0.20, realized_vol=0.20, current_hedge_position=0.0,
        )
        result = BSMinimumVarianceDelta().compute_delta(state)
        self.assertGreater(result.delta, 0.95)


# ---------------------------------------------------------------------------
# fit_quadratic_coefficients
# ---------------------------------------------------------------------------

class TestFitQuadraticCoefficients(unittest.TestCase):

    def test_exact_recovery_pure_constant(self):
        # correction = 0.05 everywhere → a=0.05, b≈0, c≈0
        deltas = [0.2, 0.4, 0.5, 0.6, 0.8]
        corrections = [0.05] * 5
        a, b, c = fit_quadratic_coefficients(deltas, corrections)
        self.assertAlmostEqual(a, 0.05, places=6)
        self.assertAlmostEqual(b, 0.0, places=4)
        self.assertAlmostEqual(c, 0.0, places=4)

    def test_exact_recovery_linear(self):
        # correction = 0.1 * delta  → a=0, b=0.1, c≈0
        deltas = [0.1, 0.3, 0.5, 0.7, 0.9]
        corrections = [0.1 * d for d in deltas]
        a, b, c = fit_quadratic_coefficients(deltas, corrections)
        self.assertAlmostEqual(a, 0.0, places=5)
        self.assertAlmostEqual(b, 0.1, places=5)
        self.assertAlmostEqual(c, 0.0, places=4)

    def test_exact_recovery_quadratic(self):
        # correction = 0.02 * delta^2  → a≈0, b≈0, c≈0.02
        deltas = [0.1, 0.3, 0.5, 0.7, 0.9]
        corrections = [0.02 * d ** 2 for d in deltas]
        a, b, c = fit_quadratic_coefficients(deltas, corrections)
        self.assertAlmostEqual(c, 0.02, places=5)

    def test_insufficient_data_returns_zeros(self):
        a, b, c = fit_quadratic_coefficients([0.5, 0.6], [0.01, 0.02])
        self.assertEqual((a, b, c), (0.0, 0.0, 0.0))

    def test_mismatched_lengths_returns_zeros(self):
        a, b, c = fit_quadratic_coefficients([0.5, 0.6, 0.7], [0.01, 0.02])
        self.assertEqual((a, b, c), (0.0, 0.0, 0.0))

    def test_returns_floats(self):
        deltas = [0.2, 0.4, 0.6, 0.8]
        corrections = [0.01, 0.02, 0.03, 0.04]
        a, b, c = fit_quadratic_coefficients(deltas, corrections)
        for val in (a, b, c):
            self.assertIsInstance(val, float)


# ---------------------------------------------------------------------------
# DiscreteRLHedgeDelta
# ---------------------------------------------------------------------------

class TestDiscreteRLHedgeDelta(unittest.TestCase):

    def test_no_policy_fallback_to_bs(self):
        state = _atm_state()
        result = DiscreteRLHedgeDelta().compute_delta(state)
        expected = _bs_delta_call(100, 100, 0.05, 0.20, 0.25)
        self.assertAlmostEqual(result.delta, expected, places=10)
        self.assertTrue(result.is_discrete)
        self.assertEqual(result.diagnostics["fallback"], "bs")

    def test_stub_policy_action_applied(self):
        # Default action space neutral (index 3) → adjustment 0.0
        state = _atm_state(hedge=0.40)
        policy = StubDiscretePolicy(action_idx=3)  # 0.0 adjustment
        result = DiscreteRLHedgeDelta(policy=policy).compute_delta(state)
        self.assertAlmostEqual(result.delta, 0.40, places=10)

    def test_stub_policy_positive_adjustment(self):
        state = _atm_state(hedge=0.40)
        # action_idx=5 → +0.05 in default space
        policy = StubDiscretePolicy(action_idx=5)
        result = DiscreteRLHedgeDelta(policy=policy).compute_delta(state)
        self.assertAlmostEqual(result.delta, 0.45, places=10)

    def test_stub_policy_negative_adjustment(self):
        state = _atm_state(hedge=0.40)
        # action_idx=1 → -0.05 in default space
        policy = StubDiscretePolicy(action_idx=1)
        result = DiscreteRLHedgeDelta(policy=policy).compute_delta(state)
        self.assertAlmostEqual(result.delta, 0.35, places=10)

    def test_out_of_range_action_clamped_to_neutral(self):
        state = _atm_state(hedge=0.40)
        policy = StubDiscretePolicy(action_idx=999)
        method = DiscreteRLHedgeDelta(policy=policy)
        result = method.compute_delta(state)
        # Neutral (middle index = 3) → 0.0 adjustment → delta unchanged
        self.assertAlmostEqual(result.delta, 0.40, places=10)

    def test_is_discrete_always_true(self):
        state = _atm_state()
        result = DiscreteRLHedgeDelta().compute_delta(state)
        self.assertTrue(result.is_discrete)

    def test_method_name(self):
        self.assertEqual(DiscreteRLHedgeDelta().method_name, "discrete_rl_hedge")

    def test_custom_action_space(self):
        custom_space = [-0.20, 0.0, 0.20]
        state = _atm_state(hedge=0.30)
        policy = StubDiscretePolicy(action_idx=2)  # +0.20
        method = DiscreteRLHedgeDelta(policy=policy, action_space=custom_space)
        result = method.compute_delta(state)
        self.assertAlmostEqual(result.delta, 0.50, places=10)

    def test_state_encoding_moneyness(self):
        state = _atm_state(spot=110, sigma=0.20)
        state.strike = 100.0
        method = DiscreteRLHedgeDelta()
        obs = method._encode_state(state)
        self.assertAlmostEqual(obs[0], 1.10, places=10)  # S/K


# ---------------------------------------------------------------------------
# ContinuousRLHedgeDelta
# ---------------------------------------------------------------------------

class TestContinuousRLHedgeDelta(unittest.TestCase):

    def test_no_policy_fallback_to_bs(self):
        state = _atm_state()
        result = ContinuousRLHedgeDelta().compute_delta(state)
        expected = _bs_delta_call(100, 100, 0.05, 0.20, 0.25)
        self.assertAlmostEqual(result.delta, expected, places=10)
        self.assertEqual(result.diagnostics["fallback"], "bs")

    def test_stub_policy_adjustment_applied(self):
        state = _atm_state(hedge=0.50)
        result = ContinuousRLHedgeDelta(policy=StubContinuousPolicy(0.05)).compute_delta(state)
        self.assertAlmostEqual(result.delta, 0.55, places=10)

    def test_action_clip_upper(self):
        state = _atm_state(hedge=0.50)
        # Policy returns 2.0 but clip is 1.0
        result = ContinuousRLHedgeDelta(
            policy=StubContinuousPolicy(2.0), action_clip=1.0
        ).compute_delta(state)
        self.assertAlmostEqual(result.delta, 1.50, places=10)
        self.assertAlmostEqual(result.diagnostics["clipped_action"], 1.0, places=10)

    def test_action_clip_lower(self):
        state = _atm_state(hedge=0.50)
        result = ContinuousRLHedgeDelta(
            policy=StubContinuousPolicy(-2.0), action_clip=1.0
        ).compute_delta(state)
        self.assertAlmostEqual(result.delta, -0.50, places=10)
        self.assertAlmostEqual(result.diagnostics["clipped_action"], -1.0, places=10)

    def test_method_name(self):
        self.assertEqual(ContinuousRLHedgeDelta().method_name, "continuous_rl_hedge")

    def test_is_discrete_false(self):
        result = ContinuousRLHedgeDelta().compute_delta(_atm_state())
        self.assertFalse(result.is_discrete)

    def test_6d_state_encoding_length(self):
        state = _atm_state()
        method = ContinuousRLHedgeDelta()
        obs = method._encode_state_6d(state)
        self.assertEqual(len(obs), 6)

    def test_6d_state_encoding_spot(self):
        state = _atm_state(spot=110)
        method = ContinuousRLHedgeDelta()
        obs = method._encode_state_6d(state)
        self.assertEqual(obs[1], 110.0)

    def test_6d_state_moneyness(self):
        state = OptionMarketState(
            spot=110, strike=100, tau=0.25, r=0.05, q=0.0,
            implied_vol=0.20, realized_vol=0.20, current_hedge_position=0.0,
        )
        method = ContinuousRLHedgeDelta()
        obs = method._encode_state_6d(state)
        self.assertAlmostEqual(obs[3], 1.10, places=10)  # S/K

    def test_6d_state_option_price_positive(self):
        state = _atm_state()
        method = ContinuousRLHedgeDelta()
        obs = method._encode_state_6d(state)
        self.assertGreater(obs[0], 0.0)


# ---------------------------------------------------------------------------
# VolForecastTriggeredBSDelta
# ---------------------------------------------------------------------------

class TestVolForecastTriggeredBSDelta(unittest.TestCase):

    def test_no_forecaster_uses_implied_vol(self):
        state = _atm_state(sigma=0.20)
        method = VolForecastTriggeredBSDelta()
        result = method.compute_delta(state)
        expected = _bs_delta_call(100, 100, 0.05, 0.20, 0.25)
        self.assertAlmostEqual(result.delta, expected, places=10)
        self.assertEqual(result.diagnostics["sigma_forecast"], 0.20)

    def test_forecaster_changes_delta(self):
        # Higher vol → higher N(d1) → higher call delta
        state = _atm_state(sigma=0.20)
        forecaster = StubVolForecaster(vol=0.40)
        method = VolForecastTriggeredBSDelta(vol_forecaster=forecaster)
        result = method.compute_delta(state)
        expected_high_vol = _bs_delta_call(100, 100, 0.05, 0.40, 0.25)
        self.assertAlmostEqual(result.delta, expected_high_vol, places=10)

    def test_should_hedge_is_bool(self):
        method = VolForecastTriggeredBSDelta()
        result = method.compute_delta(_atm_state())
        self.assertIsInstance(result.should_hedge, bool)

    def test_first_observation_always_hedges(self):
        method = VolForecastTriggeredBSDelta()
        result = method.compute_delta(_atm_state(sigma=0.20))
        self.assertTrue(result.should_hedge)

    def test_trigger_median_above_median(self):
        method = VolForecastTriggeredBSDelta(trigger_strategy=RebalancingTrigger.MEDIAN)
        low_vol_state = _atm_state(sigma=0.10)
        for _ in range(5):
            method.compute_delta(low_vol_state)
        # Now observe high vol — should trigger
        high_vol_state = _atm_state(sigma=0.30)
        result = method.compute_delta(high_vol_state)
        self.assertTrue(result.should_hedge)

    def test_trigger_median_below_median_no_hedge(self):
        method = VolForecastTriggeredBSDelta(trigger_strategy=RebalancingTrigger.MEDIAN)
        high_vol_state = _atm_state(sigma=0.30)
        for _ in range(5):
            method.compute_delta(high_vol_state)
        # Now observe low vol — should not trigger
        low_vol_state = _atm_state(sigma=0.05)
        result = method.compute_delta(low_vol_state)
        self.assertFalse(result.should_hedge)

    def test_trigger_trend_rising(self):
        method = VolForecastTriggeredBSDelta(trigger_strategy=RebalancingTrigger.TREND)
        method.compute_delta(_atm_state(sigma=0.20))
        result = method.compute_delta(_atm_state(sigma=0.25))
        self.assertTrue(result.should_hedge)

    def test_trigger_trend_falling(self):
        method = VolForecastTriggeredBSDelta(trigger_strategy=RebalancingTrigger.TREND)
        method.compute_delta(_atm_state(sigma=0.25))
        result = method.compute_delta(_atm_state(sigma=0.20))
        self.assertFalse(result.should_hedge)

    def test_trigger_percentile90_above_threshold(self):
        method = VolForecastTriggeredBSDelta(
            trigger_strategy=RebalancingTrigger.PERCENTILE_90,
            trigger_percentile=0.90,
        )
        for vol in [0.10, 0.12, 0.14, 0.16, 0.18, 0.20, 0.22, 0.24, 0.26, 0.28]:
            method.compute_delta(_atm_state(sigma=vol))
        result = method.compute_delta(_atm_state(sigma=0.50))
        self.assertTrue(result.should_hedge)

    def test_reset_history_clears_state(self):
        method = VolForecastTriggeredBSDelta(trigger_strategy=RebalancingTrigger.MEDIAN)
        for _ in range(10):
            method.compute_delta(_atm_state(sigma=0.30))
        method.reset_history()
        # After reset, next observation behaves like first (no prior history)
        result = method.compute_delta(_atm_state(sigma=0.05))
        self.assertTrue(result.should_hedge)  # first observation always hedges

    def test_method_name(self):
        self.assertEqual(
            VolForecastTriggeredBSDelta().method_name,
            "vol_forecast_triggered_bs",
        )

    def test_diagnostics_contains_sigma_forecast(self):
        result = VolForecastTriggeredBSDelta().compute_delta(_atm_state(sigma=0.22))
        self.assertIn("sigma_forecast", result.diagnostics)
        self.assertAlmostEqual(result.diagnostics["sigma_forecast"], 0.22)


# ---------------------------------------------------------------------------
# DeltaCalculationMethodFactory
# ---------------------------------------------------------------------------

class TestDeltaCalculationMethodFactory(unittest.TestCase):

    def test_create_bs_minimum_variance(self):
        m = DeltaCalculationMethodFactory.create("bs_minimum_variance")
        self.assertIsInstance(m, BSMinimumVarianceDelta)

    def test_create_discrete_rl(self):
        m = DeltaCalculationMethodFactory.create("discrete_rl")
        self.assertIsInstance(m, DiscreteRLHedgeDelta)

    def test_create_continuous_rl(self):
        m = DeltaCalculationMethodFactory.create("continuous_rl")
        self.assertIsInstance(m, ContinuousRLHedgeDelta)

    def test_create_vol_forecast_triggered_bs(self):
        m = DeltaCalculationMethodFactory.create("vol_forecast_triggered_bs")
        self.assertIsInstance(m, VolForecastTriggeredBSDelta)

    def test_create_unknown_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            DeltaCalculationMethodFactory.create("nonexistent_method")
        self.assertIn("nonexistent_method", str(ctx.exception))

    def test_create_with_kwargs_forwarded(self):
        m = DeltaCalculationMethodFactory.create("bs_minimum_variance", a=0.1, b=0.2, c=0.3)
        self.assertIsInstance(m, BSMinimumVarianceDelta)
        state = _atm_state()
        result = m.compute_delta(state)
        # Should differ from zero-coeff version
        base = DeltaCalculationMethodFactory.create("bs_minimum_variance").compute_delta(state).delta
        self.assertNotAlmostEqual(result.delta, base, places=4)

    def test_available_methods_lists_four(self):
        methods = DeltaCalculationMethodFactory.available_methods()
        self.assertIn("bs_minimum_variance", methods)
        self.assertIn("discrete_rl", methods)
        self.assertIn("continuous_rl", methods)
        self.assertIn("vol_forecast_triggered_bs", methods)

    def test_register_custom_method(self):
        class AlwaysHalfDelta(DeltaCalculationMethod):
            @property
            def method_name(self):
                return "always_half"

            def compute_delta(self, state):
                return DeltaResult(delta=0.5, method_name=self.method_name)

        DeltaCalculationMethodFactory.register("always_half", AlwaysHalfDelta)
        m = DeltaCalculationMethodFactory.create("always_half")
        self.assertIsInstance(m, AlwaysHalfDelta)
        self.assertEqual(m.compute_delta(_atm_state()).delta, 0.5)
        # Clean up
        del DeltaCalculationMethodFactory._registry["always_half"]

    def test_register_non_subclass_raises_type_error(self):
        with self.assertRaises(TypeError):
            DeltaCalculationMethodFactory.register("bad", object)

    def test_available_methods_sorted(self):
        methods = DeltaCalculationMethodFactory.available_methods()
        self.assertEqual(methods, sorted(methods))


if __name__ == "__main__":
    unittest.main()
