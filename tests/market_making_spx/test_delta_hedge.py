"""
Unit and integration tests for the regime-switched delta-hedge rebalancing module.

Covers:
  - whalley_wilmott_band: qualitative monotonicity and scaling laws
  - zakamouline_band: qualitative monotonicity and scaling laws
  - compute_hedge_band: regime dispatch and output shape
  - Strategy.evaluate_delta_hedge: in-band / out-of-band logic, direction, target edge
  - Strategy.manage_existing_positions: hedge wiring and state update
"""

import unittest
from typing import Any, Dict

from src.application.managers.project_managers.market_making_SPX_call_spread_project.strategy.hedging.rebalancing_bands import (
    compute_hedge_band,
    whalley_wilmott_band,
    zakamouline_band,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project.strategy.market_making_strategy import Strategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _spx_base(**overrides):
    """Typical SPX-like parameters for a 7–45 DTE call spread."""
    p = dict(
        gamma=2e-4,
        spot=4500.0,
        cost_rate=1e-4,
        risk_aversion=1.0,
        time_to_expiry=0.1,
        risk_free_rate=0.05,
    )
    p.update(overrides)
    return p


def _make_strategy(**config_overrides) -> Strategy:
    config = {
        'hedge_transaction_cost_rate': 1e-4,
        'hedge_risk_aversion': 1.0,
        'interest_rate': 0.05,
    }
    config.update(config_overrides)
    return Strategy(config)


def _make_position(net_delta=0.05, net_gamma=2e-4, size=1, time_to_expiry=0.1) -> Dict[str, Any]:
    return {
        'greeks': {'delta': net_delta, 'gamma': net_gamma},
        'size': size,
        'time_to_expiry': time_to_expiry,
        'days_to_expiry': 30,   # > 7 so expiry-approach exit is not triggered
        'entry_price': 2.0,
        'current_price': 2.0,
        'max_profit': 5.0,
        'max_loss': 5.0,
    }


def _market(spx=4500.0, vix=18.0, implied_vol=0.18) -> Dict[str, Any]:
    return {'spx_price': spx, 'vix': vix, 'implied_vol': implied_vol}


# ---------------------------------------------------------------------------
# Whalley-Wilmott (1997)
# ---------------------------------------------------------------------------

class TestWhalleyWilmottBand(unittest.TestCase):

    def test_positive_gamma_returns_positive_band(self):
        h = whalley_wilmott_band(**_spx_base())
        self.assertGreater(h, 0.0)

    def test_zero_gamma_returns_zero(self):
        h = whalley_wilmott_band(**_spx_base(gamma=0.0))
        self.assertEqual(h, 0.0)

    def test_negative_gamma_same_magnitude_as_positive(self):
        h_pos = whalley_wilmott_band(**_spx_base(gamma=2e-4))
        h_neg = whalley_wilmott_band(**_spx_base(gamma=-2e-4))
        self.assertAlmostEqual(h_pos, h_neg, places=12)

    def test_band_increases_with_higher_cost(self):
        h_low = whalley_wilmott_band(**_spx_base(cost_rate=1e-4))
        h_high = whalley_wilmott_band(**_spx_base(cost_rate=1e-3))
        self.assertGreater(h_high, h_low)

    def test_band_decreases_with_higher_risk_aversion(self):
        h_low = whalley_wilmott_band(**_spx_base(risk_aversion=1.0))
        h_high = whalley_wilmott_band(**_spx_base(risk_aversion=10.0))
        self.assertLess(h_high, h_low)

    def test_band_increases_with_higher_gamma(self):
        h_low = whalley_wilmott_band(**_spx_base(gamma=1e-4))
        h_high = whalley_wilmott_band(**_spx_base(gamma=1e-3))
        self.assertGreater(h_high, h_low)

    def test_scales_as_cube_root_of_cost(self):
        """8× cost_rate → 2× half-band (k^{1/3} scaling)."""
        h1 = whalley_wilmott_band(**_spx_base(cost_rate=1e-4))
        h8 = whalley_wilmott_band(**_spx_base(cost_rate=8e-4))
        self.assertAlmostEqual(h8 / h1, 8.0 ** (1.0 / 3.0), places=5)

    def test_invalid_cost_rate_raises(self):
        with self.assertRaises(ValueError):
            whalley_wilmott_band(**_spx_base(cost_rate=0.0))

    def test_negative_cost_rate_raises(self):
        with self.assertRaises(ValueError):
            whalley_wilmott_band(**_spx_base(cost_rate=-1e-4))

    def test_invalid_risk_aversion_raises(self):
        with self.assertRaises(ValueError):
            whalley_wilmott_band(**_spx_base(risk_aversion=0.0))

    def test_invalid_spot_raises(self):
        with self.assertRaises(ValueError):
            whalley_wilmott_band(**_spx_base(spot=0.0))

    def test_typical_spx_band_in_plausible_range(self):
        """For typical SPX params, expect a 1–15% delta band."""
        h = whalley_wilmott_band(**_spx_base())
        self.assertGreater(h, 0.01)
        self.assertLess(h, 0.15)


# ---------------------------------------------------------------------------
# Zakamouline (2009)
# ---------------------------------------------------------------------------

class TestZakamoulineBand(unittest.TestCase):

    def _zp(self, **kw):
        p = _spx_base(implied_vol=0.20)
        p.update(kw)
        return p

    def test_positive_gamma_returns_positive_band(self):
        h = zakamouline_band(**self._zp())
        self.assertGreater(h, 0.0)

    def test_zero_gamma_returns_zero(self):
        h = zakamouline_band(**self._zp(gamma=0.0))
        self.assertEqual(h, 0.0)

    def test_band_decreases_with_higher_sigma(self):
        """Higher vol → narrower band (tighter rebalancing)."""
        h_low = zakamouline_band(**self._zp(implied_vol=0.15))
        h_high = zakamouline_band(**self._zp(implied_vol=0.45))
        self.assertLess(h_high, h_low)

    def test_band_increases_with_higher_gamma(self):
        h_low = zakamouline_band(**self._zp(gamma=1e-4))
        h_high = zakamouline_band(**self._zp(gamma=1e-3))
        self.assertGreater(h_high, h_low)

    def test_band_decreases_with_higher_risk_aversion(self):
        h_low = zakamouline_band(**self._zp(risk_aversion=1.0))
        h_high = zakamouline_band(**self._zp(risk_aversion=10.0))
        self.assertLess(h_high, h_low)

    def test_scales_as_sqrt_of_cost(self):
        """4× cost_rate → 2× half-band (k^{1/2} scaling)."""
        h1 = zakamouline_band(**self._zp(cost_rate=1e-4))
        h4 = zakamouline_band(**self._zp(cost_rate=4e-4))
        self.assertAlmostEqual(h4 / h1, 4.0 ** 0.5, places=5)

    def test_default_sigma_used_when_not_provided(self):
        """Should not raise when implied_vol is absent (uses default 0.20)."""
        p = _spx_base()  # no implied_vol key
        h = zakamouline_band(**p)
        self.assertGreater(h, 0.0)

    def test_zero_sigma_raises(self):
        with self.assertRaises(ValueError):
            zakamouline_band(**self._zp(implied_vol=0.0))

    def test_tighter_than_ww_in_high_volatility(self):
        """Well above the crossover sigma, Zakamouline gives a narrower band."""
        base = _spx_base()
        h_ww = whalley_wilmott_band(**base)
        h_z = zakamouline_band(**base, implied_vol=0.50)
        self.assertLess(h_z, h_ww)

    def test_typical_spx_band_in_plausible_range(self):
        h = zakamouline_band(**self._zp())
        self.assertGreater(h, 0.01)
        self.assertLess(h, 0.15)


# ---------------------------------------------------------------------------
# compute_hedge_band regime dispatch
# ---------------------------------------------------------------------------

class TestComputeHedgeBand(unittest.TestCase):

    def _cb(self, regime='normal', **kw):
        p = _spx_base(implied_vol=0.20)
        p.update(kw)
        return compute_hedge_band(regime=regime, **p)

    def test_normal_regime_uses_ww(self):
        self.assertEqual(self._cb(regime='normal')['model_used'], 'whalley_wilmott')

    def test_low_vol_regime_uses_ww(self):
        self.assertEqual(self._cb(regime='low_volatility')['model_used'], 'whalley_wilmott')

    def test_high_vol_regime_uses_zakamouline(self):
        self.assertEqual(self._cb(regime='high_volatility')['model_used'], 'zakamouline')

    def test_result_has_required_keys(self):
        result = self._cb()
        for k in ('half_width', 'model_used', 'regime', 'ww_half_width', 'zakamouline_half_width'):
            self.assertIn(k, result)

    def test_half_width_matches_selected_model_for_high_vol(self):
        result = self._cb(regime='high_volatility')
        self.assertAlmostEqual(result['half_width'], result['zakamouline_half_width'], places=12)

    def test_half_width_matches_selected_model_for_normal(self):
        result = self._cb(regime='normal')
        self.assertAlmostEqual(result['half_width'], result['ww_half_width'], places=12)

    def test_custom_regime_map_overrides_default(self):
        result = self._cb(regime='normal', regime_map={'normal': 'zakamouline'})
        self.assertEqual(result['model_used'], 'zakamouline')

    def test_unknown_regime_falls_back_to_ww(self):
        result = self._cb(regime='mystery_regime')
        self.assertEqual(result['model_used'], 'whalley_wilmott')

    def test_high_vol_without_sigma_raises(self):
        with self.assertRaises(ValueError):
            compute_hedge_band(
                gamma=2e-4, spot=4500.0, cost_rate=1e-4, risk_aversion=1.0,
                regime='high_volatility',
            )

    def test_both_bands_computed_when_sigma_available(self):
        result = self._cb()
        self.assertIsNotNone(result['ww_half_width'])
        self.assertIsNotNone(result['zakamouline_half_width'])

    def test_positive_half_width(self):
        self.assertGreater(self._cb()['half_width'], 0.0)


# ---------------------------------------------------------------------------
# Strategy.evaluate_delta_hedge
# ---------------------------------------------------------------------------

class TestEvaluateDeltaHedge(unittest.TestCase):

    def _strat(self, **kw) -> Strategy:
        return _make_strategy(**kw)

    def _setup(self, net_delta=0.05, regime='normal', initial_hedge=None):
        strat = self._strat()
        strat.active_positions['p1'] = _make_position(net_delta=net_delta)
        strat.market_regime = regime
        if initial_hedge is not None:
            strat.hedge_band_state['p1'] = {'hedge_delta': initial_hedge}
        return strat

    def test_fully_hedged_position_in_band(self):
        """Hedge perfectly offsetting delta → residual zero → no action."""
        strat = self._setup(net_delta=0.10, initial_hedge=-0.10)
        result = strat.evaluate_delta_hedge('p1', _market())
        self.assertFalse(result['should_hedge'])

    def test_large_unhedged_delta_triggers_hedge(self):
        strat = self._setup(net_delta=0.30)  # no hedge → residual 0.30 >> band
        result = strat.evaluate_delta_hedge('p1', _market())
        self.assertTrue(result['should_hedge'])

    def test_long_delta_recommends_sell(self):
        strat = self._setup(net_delta=0.30)
        result = strat.evaluate_delta_hedge('p1', _market())
        self.assertEqual(result['hedge_direction'], 'sell')

    def test_short_delta_recommends_buy(self):
        strat = self._setup(net_delta=-0.30)
        result = strat.evaluate_delta_hedge('p1', _market())
        self.assertEqual(result['hedge_direction'], 'buy')

    def test_hedge_targets_band_edge_not_zero(self):
        """After applying the recommended trade, residual equals ±half_width."""
        strat = self._setup(net_delta=0.30)
        result = strat.evaluate_delta_hedge('p1', _market())
        self.assertTrue(result['should_hedge'])

        net_delta = 0.30
        target_hedge = result['target_hedge_delta']
        half_width = result['band_half_width']
        new_residual = net_delta + target_hedge
        self.assertAlmostEqual(abs(new_residual), half_width, places=10)

    def test_small_deviation_inside_band_no_hedge(self):
        """Residual just below half_width → no action."""
        strat = self._setup(net_delta=0.001)  # tiny net delta, no prior hedge
        # band >> 0.001 for typical params → inside
        result = strat.evaluate_delta_hedge('p1', _market())
        self.assertFalse(result['should_hedge'])

    def test_result_includes_required_keys(self):
        strat = self._setup(net_delta=0.30)
        result = strat.evaluate_delta_hedge('p1', _market())
        for k in ('should_hedge', 'position_id', 'net_residual_delta',
                  'band_half_width', 'model_used', 'current_hedge_delta',
                  'band_info', 'evaluation_timestamp'):
            self.assertIn(k, result)

    def test_high_vol_regime_uses_ww_ntbn(self):
        # high_volatility regime → select_hedge_method returns 'ww_ntbn';
        # without loaded weights the policy falls back to WW prior so model_used
        # contains 'ww_ntbn'.
        strat = self._setup(net_delta=0.001, regime='high_volatility', initial_hedge=-0.001)
        result = strat.evaluate_delta_hedge('p1', _market(implied_vol=0.40))
        self.assertIn('ww_ntbn', result['model_used'])

    def test_missing_position_returns_safe_dict(self):
        strat = self._strat()
        result = strat.evaluate_delta_hedge('nonexistent', {})
        self.assertFalse(result['should_hedge'])
        self.assertEqual(result['position_id'], 'nonexistent')

    def test_hedge_trade_delta_is_positive_scalar(self):
        strat = self._setup(net_delta=0.30)
        result = strat.evaluate_delta_hedge('p1', _market())
        self.assertGreater(result['hedge_trade_delta'], 0.0)

    def test_partial_hedge_detects_residual_correctly(self):
        """Partially hedged position: residual = net_delta + partial_hedge."""
        strat = self._setup(net_delta=0.20, initial_hedge=-0.05)
        result = strat.evaluate_delta_hedge('p1', _market())
        # residual = 0.20 + (-0.05) = 0.15 — almost certainly outside band
        self.assertAlmostEqual(result['net_residual_delta'], 0.15, places=10)


# ---------------------------------------------------------------------------
# Strategy.manage_existing_positions integration
# ---------------------------------------------------------------------------

class TestManageExistingPositionsHedgeIntegration(unittest.TestCase):

    def test_portfolio_hedge_decision_is_returned(self):
        """Since f2844273 (portfolio hedge) the decision is made for the whole book, not per position."""
        strat = _make_strategy()
        strat.active_positions['p1'] = _make_position(net_delta=0.30)
        strat.market_regime = 'normal'

        result = strat.manage_existing_positions(market_data=_market())

        self.assertIn('should_hedge', result['portfolio_hedge'])

    def test_portfolio_hedge_state_updated_when_out_of_band(self):
        strat = _make_strategy()
        strat.active_positions['p1'] = _make_position(net_delta=0.30)
        strat.market_regime = 'normal'

        result = strat.manage_existing_positions(market_data=_market())

        self.assertTrue(result['portfolio_hedge']['should_hedge'])
        self.assertIn('hedge_delta', strat.hedge_band_state['_portfolio'])

    def test_hedge_state_unchanged_when_in_band(self):
        strat = _make_strategy()
        pos = _make_position(net_delta=0.001)
        strat.active_positions['p1'] = pos
        strat.hedge_band_state['p1'] = {'hedge_delta': -0.001}
        strat.market_regime = 'normal'

        strat.manage_existing_positions(market_data=_market())

        # Still in band → hedge_band_state should not change
        self.assertAlmostEqual(
            strat.hedge_band_state['p1']['hedge_delta'], -0.001, places=10
        )

    @unittest.expectedFailure
    def test_hedge_state_cleared_on_position_exit(self):
        """GAP (original project): manage_existing_positions no longer executes exits — management_results and
        exited_position_ids are always empty since the portfolio-hedge rewrite (f2844273), although the docstring
        promises profit taking / loss cutting. A position at its profit target is never closed."""
        strat = _make_strategy()
        pos = _make_position(net_delta=0.30)
        pos['max_profit'] = 1.0
        pos['current_price'] = 3.0   # forces exit (current_pnl = profit_target)
        strat.active_positions['p1'] = pos
        strat.hedge_band_state['p1'] = {'hedge_delta': -0.25}
        strat.market_regime = 'normal'

        strat.manage_existing_positions(market_data=_market())

        self.assertNotIn('p1', strat.hedge_band_state)

    def test_manage_works_without_market_data_argument(self):
        """Backward-compatible call with no market_data."""
        strat = _make_strategy()
        strat.active_positions['p1'] = _make_position(net_delta=0.05)
        strat.market_regime = 'normal'
        result = strat.manage_existing_positions()
        self.assertIn('positions_managed', result)

    def test_multiple_positions_all_evaluated(self):
        strat = _make_strategy()
        for pid in ('p1', 'p2', 'p3'):
            strat.active_positions[pid] = _make_position(net_delta=0.30)
        strat.market_regime = 'normal'

        result = strat.manage_existing_positions(market_data=_market())

        self.assertEqual(result['positions_managed'], 3)
        # one book-level decision on the summed delta of every position
        self.assertTrue(result['portfolio_hedge']['should_hedge'])


if __name__ == '__main__':
    unittest.main()
