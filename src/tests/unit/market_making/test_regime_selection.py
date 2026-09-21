"""Unit tests for select_hedge_method (pure function and Strategy method).

Covers:
  - Regime-only dispatch: low_vol, normal, high_vol
  - Cost-rate threshold: low-cost vs. high-cost cross-over
  - Unrecognised regime treated as 'normal' → zakamouline
  - Strategy.select_hedge_method: reads config threshold, delegates correctly
  - Integration with evaluate_delta_hedge: method_used label matches selection
"""

import unittest
from typing import Any, Dict

from src.application.managers.project_managers.market_making_SPX_call_spread_project.strategy.hedging.rebalancing_bands import (
    select_hedge_method,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project.strategy.market_making_strategy import Strategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_strategy(**config_overrides) -> Strategy:
    config = {
        'hedge_transaction_cost_rate': 1e-4,
        'hedge_risk_aversion': 1.0,
        'interest_rate': 0.05,
    }
    config.update(config_overrides)
    return Strategy(config)


def _make_position(**kw) -> Dict[str, Any]:
    p = {
        'greeks': {'delta': 0.05, 'gamma': 2e-4},
        'size': 1,
        'time_to_expiry': 0.1,
        'days_to_expiry': 30,
        'entry_price': 2.0,
        'current_price': 2.0,
        'max_profit': 5.0,
        'max_loss': 5.0,
    }
    p.update(kw)
    return p


def _market(**kw) -> Dict[str, Any]:
    d = {'spx_price': 4500.0, 'vix': 18.0, 'implied_vol': 0.18}
    d.update(kw)
    return d


# ---------------------------------------------------------------------------
# Pure function: select_hedge_method
# ---------------------------------------------------------------------------

class TestSelectHedgeMethodPure(unittest.TestCase):

    # --- Regime-driven, low cost ---

    def test_low_vol_low_cost_returns_ww(self):
        self.assertEqual(select_hedge_method('low_volatility', 1e-4), 'whalley_wilmott')

    def test_normal_low_cost_returns_zakamouline(self):
        self.assertEqual(select_hedge_method('normal', 1e-4), 'zakamouline')

    def test_high_vol_low_cost_returns_ww_ntbn(self):
        self.assertEqual(select_hedge_method('high_volatility', 1e-4), 'ww_ntbn')

    # --- Cost threshold ---

    def test_high_cost_overrides_low_vol_to_ww_ntbn(self):
        """Even in low-vol regime, high cost triggers WW-NTBN."""
        self.assertEqual(select_hedge_method('low_volatility', 0.01), 'ww_ntbn')

    def test_high_cost_overrides_normal_to_ww_ntbn(self):
        self.assertEqual(select_hedge_method('normal', 0.01), 'ww_ntbn')

    def test_cost_exactly_at_threshold_is_high(self):
        """cost_rate == threshold is treated as high cost."""
        self.assertEqual(select_hedge_method('normal', 0.005, 0.005), 'ww_ntbn')

    def test_cost_just_below_threshold_is_low(self):
        self.assertEqual(select_hedge_method('normal', 0.00499, 0.005), 'zakamouline')

    def test_custom_threshold_respected(self):
        self.assertEqual(select_hedge_method('normal', 1e-4, cost_high_threshold=1e-5), 'ww_ntbn')

    # --- Unrecognised regime ---

    def test_unknown_regime_low_cost_returns_zakamouline(self):
        self.assertEqual(select_hedge_method('mystery', 1e-4), 'zakamouline')

    def test_empty_regime_low_cost_returns_zakamouline(self):
        self.assertEqual(select_hedge_method('', 1e-4), 'zakamouline')

    # --- Return values are always valid model names ---

    def test_all_outputs_are_known_methods(self):
        known = {'whalley_wilmott', 'zakamouline', 'ww_ntbn'}
        for regime in ('low_volatility', 'normal', 'high_volatility', 'other'):
            for cost in (1e-5, 1e-4, 0.005, 0.01):
                method = select_hedge_method(regime, cost)
                self.assertIn(method, known)


# ---------------------------------------------------------------------------
# Strategy.select_hedge_method (thin wrapper)
# ---------------------------------------------------------------------------

class TestStrategySelectHedgeMethod(unittest.TestCase):

    def test_normal_low_cost_returns_zakamouline(self):
        strat = _make_strategy()
        strat.market_regime = 'normal'
        result = strat.select_hedge_method({'regime': 'normal'}, 1e-4)
        self.assertEqual(result, 'zakamouline')

    def test_high_vol_returns_ww_ntbn(self):
        strat = _make_strategy()
        strat.market_regime = 'high_volatility'
        result = strat.select_hedge_method({'regime': 'high_volatility'}, 1e-4)
        self.assertEqual(result, 'ww_ntbn')

    def test_low_vol_returns_ww(self):
        strat = _make_strategy()
        result = strat.select_hedge_method({'regime': 'low_volatility'}, 1e-4)
        self.assertEqual(result, 'whalley_wilmott')

    def test_high_cost_overrides_regime(self):
        strat = _make_strategy(hedge_cost_high_threshold=0.005)
        result = strat.select_hedge_method({'regime': 'low_volatility'}, 0.01)
        self.assertEqual(result, 'ww_ntbn')

    def test_config_threshold_is_used(self):
        strat = _make_strategy(hedge_cost_high_threshold=0.001)
        result = strat.select_hedge_method({'regime': 'normal'}, 0.002)
        self.assertEqual(result, 'ww_ntbn')

    def test_market_analysis_regime_takes_precedence_over_self(self):
        """Regime from market_analysis arg is used, not self.market_regime."""
        strat = _make_strategy()
        strat.market_regime = 'high_volatility'
        result = strat.select_hedge_method({'regime': 'low_volatility'}, 1e-4)
        self.assertEqual(result, 'whalley_wilmott')

    def test_fallback_to_self_market_regime_when_not_in_analysis(self):
        strat = _make_strategy()
        strat.market_regime = 'low_volatility'
        result = strat.select_hedge_method({}, 1e-4)
        self.assertEqual(result, 'whalley_wilmott')


# ---------------------------------------------------------------------------
# Integration: evaluate_delta_hedge respects select_hedge_method
# ---------------------------------------------------------------------------

class TestEvaluateDeltaHedgeRegimeDispatch(unittest.TestCase):

    def _setup(self, regime, net_delta=0.05, initial_hedge=None):
        strat = _make_strategy()
        strat.active_positions['p1'] = _make_position()
        strat.active_positions['p1']['greeks']['delta'] = net_delta
        strat.market_regime = regime
        if initial_hedge is not None:
            strat.hedge_band_state['p1'] = {'hedge_delta': initial_hedge}
        return strat

    def test_normal_regime_uses_zakamouline_model(self):
        strat = self._setup('normal', net_delta=0.001, initial_hedge=-0.001)
        result = strat.evaluate_delta_hedge('p1', _market())
        self.assertEqual(result['model_used'], 'zakamouline')

    def test_low_vol_regime_uses_ww_model(self):
        strat = self._setup('low_volatility', net_delta=0.001, initial_hedge=-0.001)
        result = strat.evaluate_delta_hedge('p1', _market())
        self.assertEqual(result['model_used'], 'whalley_wilmott')

    def test_high_vol_regime_uses_ww_ntbn_model(self):
        strat = self._setup('high_volatility', net_delta=0.001, initial_hedge=-0.001)
        result = strat.evaluate_delta_hedge('p1', _market(implied_vol=0.40))
        self.assertIn('ww_ntbn', result['model_used'])

    def test_high_cost_config_uses_ww_ntbn(self):
        strat = _make_strategy(
            hedge_transaction_cost_rate=0.01,   # 1% — above default 0.5% threshold
        )
        strat.active_positions['p1'] = _make_position()
        strat.active_positions['p1']['greeks']['delta'] = 0.001
        strat.hedge_band_state['p1'] = {'hedge_delta': -0.001}
        strat.market_regime = 'low_volatility'
        result = strat.evaluate_delta_hedge('p1', _market())
        self.assertIn('ww_ntbn', result['model_used'])


if __name__ == '__main__':
    unittest.main()
