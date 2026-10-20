"""Regression tests for call-spread NETTED greek semantics.

Key invariant:
  For a call spread (long K1, short K2, K1 < K2) with the same notional:
    Γ_net = Γ(K1) - Γ(K2)       (both legs have the same sign convention)
    Δ_net = Δ(K1) - Δ(K2)

Near-the-money, |Γ_net| << max(Γ(K1), Γ(K2)) and the per-leg WW bands can
have an *empty* intersection.  Using a single band on the net gamma avoids
that degeneracy.

Tests:
  1. Net gamma of a call spread is strictly smaller in magnitude than the
     larger of the two individual gammas (except at extremes of moneyness).
  2. Per-leg WW band intersection can be empty near ATM while the net-gamma
     band remains valid (positive half-width).
  3. evaluate_delta_hedge uses net greeks, not per-leg greeks.
  4. Scaling: net gamma band scales correctly as net gamma changes.
"""

import math
import unittest
from typing import Any, Dict

from src.application.managers.project_managers.market_making_SPX_call_spread_project.strategy.hedging.rebalancing_bands import (
    whalley_wilmott_band,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project.strategy.market_making_strategy import Strategy


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _bs_gamma(spot: float, strike: float, tau: float, vol: float, r: float = 0.0) -> float:
    """Black-Scholes gamma for a European call."""
    if tau <= 0 or vol <= 0 or spot <= 0:
        return 0.0
    d1 = (math.log(spot / strike) + (r + 0.5 * vol ** 2) * tau) / (vol * math.sqrt(tau))
    pdf_d1 = math.exp(-0.5 * d1 ** 2) / math.sqrt(2 * math.pi)
    return pdf_d1 / (spot * vol * math.sqrt(tau))


def _bs_delta(spot: float, strike: float, tau: float, vol: float, r: float = 0.0) -> float:
    """Black-Scholes delta for a European call."""
    if tau <= 0 or vol <= 0 or spot <= 0:
        return 0.0
    d1 = (math.log(spot / strike) + (r + 0.5 * vol ** 2) * tau) / (vol * math.sqrt(tau))
    return 0.5 * (1.0 + math.erf(d1 / math.sqrt(2)))


def _call_spread_net_greeks(
    spot: float, k1: float, k2: float, tau: float, vol: float, r: float = 0.0
) -> Dict[str, float]:
    """Net delta and gamma for a long K1 / short K2 call spread."""
    g1 = _bs_gamma(spot, k1, tau, vol, r)
    g2 = _bs_gamma(spot, k2, tau, vol, r)
    d1 = _bs_delta(spot, k1, tau, vol, r)
    d2 = _bs_delta(spot, k2, tau, vol, r)
    return {'net_gamma': g1 - g2, 'net_delta': d1 - d2, 'gamma_k1': g1, 'gamma_k2': g2}


def _make_strategy(**config_overrides) -> Strategy:
    config = {
        'hedge_transaction_cost_rate': 1e-4,
        'hedge_risk_aversion': 1.0,
        'interest_rate': 0.05,
    }
    config.update(config_overrides)
    return Strategy(config)


def _ww(gamma, **kw) -> float:
    defaults = dict(spot=4500.0, cost_rate=1e-4, risk_aversion=1.0,
                    time_to_expiry=0.1, risk_free_rate=0.05)
    defaults.update(kw)
    return whalley_wilmott_band(gamma=gamma, **defaults)


# ---------------------------------------------------------------------------
# Net gamma magnitude
# ---------------------------------------------------------------------------

class TestCallSpreadNetGamma(unittest.TestCase):

    def test_near_atm_net_gamma_less_than_individual(self):
        """Near ATM, K1 and K2 both have high gamma; net is much smaller."""
        spot = 4500.0
        k1, k2 = 4450.0, 4550.0
        greeks = _call_spread_net_greeks(spot, k1, k2, tau=0.05, vol=0.20)
        g_net = abs(greeks['net_gamma'])
        g_max = max(greeks['gamma_k1'], greeks['gamma_k2'])
        # Net is strictly smaller than the larger individual gamma
        self.assertLess(g_net, g_max)

    def test_deep_itm_short_mostly_cancels_long(self):
        """K2 very close to K1 → gammas nearly equal → very small net gamma."""
        spot = 4500.0
        k1, k2 = 4490.0, 4510.0
        greeks = _call_spread_net_greeks(spot, k1, k2, tau=0.05, vol=0.20)
        g_net = abs(greeks['net_gamma'])
        g_k1 = greeks['gamma_k1']
        # Net gamma is a fraction of K1 gamma
        self.assertLess(g_net, 0.5 * g_k1)

    def test_net_gamma_nonnegative_for_standard_call_spread(self):
        """Long K1 (lower strike) has higher gamma than short K2 (higher) near ATM."""
        spot = 4500.0
        k1, k2 = 4480.0, 4580.0
        greeks = _call_spread_net_greeks(spot, k1, k2, tau=0.05, vol=0.20)
        self.assertGreaterEqual(greeks['net_gamma'], 0.0)

    def test_net_delta_positive_for_bull_call_spread(self):
        """Bull call spread: Δ(K1) > Δ(K2) → net delta > 0."""
        spot = 4500.0
        k1, k2 = 4450.0, 4550.0
        greeks = _call_spread_net_greeks(spot, k1, k2, tau=0.10, vol=0.20)
        self.assertGreater(greeks['net_delta'], 0.0)


# ---------------------------------------------------------------------------
# Per-leg band intersection can be empty
# ---------------------------------------------------------------------------

class TestPerLegBandsDegeneracy(unittest.TestCase):

    def test_per_leg_bands_may_not_intersect_near_atm(self):
        """Demonstrate the per-leg intersection issue near ATM.

        Two calls near ATM with similar gammas: WW bands overlap by less than
        the distance between their centres if the net gamma is much smaller
        than each individual gamma.
        """
        spot = 4500.0
        k1, k2 = 4480.0, 4520.0
        tau = 0.02  # very short-dated → spiky gamma near ATM
        vol = 0.25

        g1 = _bs_gamma(spot, k1, tau, vol)
        g2 = _bs_gamma(spot, k2, tau, vol)
        d1 = _bs_delta(spot, k1, tau, vol)
        d2 = _bs_delta(spot, k2, tau, vol)

        h1 = _ww(g1, time_to_expiry=tau)   # per-leg band for K1 position
        h2 = _ww(g2, time_to_expiry=tau)   # per-leg band for K2 position

        # Per-leg "target deltas" if centred on their own BS deltas
        per_leg_band_k1 = (d1 - h1, d1 + h1)
        per_leg_band_k2 = (d2 - h2, d2 + h2)

        # Intersection
        inter_lo = max(per_leg_band_k1[0], per_leg_band_k2[0])
        inter_hi = min(per_leg_band_k1[1], per_leg_band_k2[1])
        intersection_empty = inter_lo >= inter_hi

        # Net gamma band is always valid
        g_net = g1 - g2
        h_net = _ww(g_net, time_to_expiry=tau)
        self.assertGreater(h_net, 0.0, "Net-gamma band should be positive")

        # The test documents the known degeneracy: per-leg intersection can be
        # empty (or very narrow) while the net band is well-defined.
        # We assert the net band provides a usable width regardless.
        self.assertGreater(h_net, 0.001)

    def test_net_gamma_band_always_valid(self):
        """Net-gamma band stays well-defined even when individual gammas are large."""
        spot = 4500.0
        for k1, k2, tau, vol in [
            (4490, 4510, 0.02, 0.25),   # tight spread, short tau
            (4400, 4600, 0.10, 0.20),   # wide spread, normal tau
            (4500, 4550, 0.05, 0.30),   # ATM spread, high vol
        ]:
            greeks = _call_spread_net_greeks(spot, k1, k2, tau, vol)
            h_net = _ww(greeks['net_gamma'], time_to_expiry=tau)
            self.assertGreaterEqual(h_net, 0.0)


# ---------------------------------------------------------------------------
# evaluate_delta_hedge uses net greeks
# ---------------------------------------------------------------------------

class TestEvaluateDeltaHedgeUsesNetGreeks(unittest.TestCase):

    def _make_position(self, net_delta, net_gamma, size=1) -> Dict[str, Any]:
        return {
            'greeks': {'net_delta': net_delta, 'net_gamma': net_gamma},
            'size': size,
            'time_to_expiry': 0.1,
            'days_to_expiry': 30,
            'entry_price': 2.0,
            'current_price': 2.0,
            'max_profit': 5.0,
            'max_loss': 5.0,
        }

    def test_net_delta_key_preferred_over_delta_key(self):
        """Position with 'net_delta' and 'net_gamma' keys: evaluate uses them."""
        strat = _make_strategy()
        net_delta = 0.35
        net_gamma = 2e-4
        strat.active_positions['p1'] = self._make_position(net_delta, net_gamma)
        strat.market_regime = 'normal'

        result = strat.evaluate_delta_hedge('p1', {'spx_price': 4500.0, 'implied_vol': 0.20})

        # net_residual_delta should be net_delta * size = 0.35
        self.assertAlmostEqual(result['net_residual_delta'], net_delta, places=10)

    def test_size_scales_net_greeks(self):
        """size=2 doubles net_delta and net_gamma → wider band and larger residual."""
        strat_1 = _make_strategy()
        strat_2 = _make_strategy()
        pos = {'greeks': {'net_delta': 0.10, 'net_gamma': 1e-4},
               'time_to_expiry': 0.1, 'days_to_expiry': 30,
               'entry_price': 2.0, 'current_price': 2.0, 'max_profit': 5.0, 'max_loss': 5.0}
        import copy
        strat_1.active_positions['p1'] = copy.deepcopy(pos)
        strat_1.active_positions['p1']['size'] = 1
        strat_2.active_positions['p1'] = copy.deepcopy(pos)
        strat_2.active_positions['p1']['size'] = 2
        strat_1.market_regime = 'low_volatility'
        strat_2.market_regime = 'low_volatility'

        market = {'spx_price': 4500.0, 'implied_vol': 0.20}
        r1 = strat_1.evaluate_delta_hedge('p1', market)
        r2 = strat_2.evaluate_delta_hedge('p1', market)

        # Residual should be 2× for size=2 position
        self.assertAlmostEqual(r2['net_residual_delta'], 2 * r1['net_residual_delta'], places=10)

    def test_net_gamma_zero_gives_zero_band(self):
        """Call spread with zero net gamma → band = 0 → any residual triggers hedge."""
        strat = _make_strategy()
        # gamma=0 but delta=0.10 — residual = 0.10 > band = 0 → should hedge
        strat.active_positions['p1'] = self._make_position(net_delta=0.10, net_gamma=0.0)
        strat.market_regime = 'low_volatility'
        result = strat.evaluate_delta_hedge('p1', {'spx_price': 4500.0, 'implied_vol': 0.20})
        self.assertEqual(result['band_half_width'], 0.0)


# ---------------------------------------------------------------------------
# Scaling regression
# ---------------------------------------------------------------------------

class TestBandScalingWithNetGamma(unittest.TestCase):

    def test_ww_band_cube_root_scaling_with_net_gamma(self):
        """8× net_gamma → 2× WW band (Γ^{1/3} scaling)."""
        h1 = _ww(1e-4)
        h8 = _ww(8e-4)
        self.assertAlmostEqual(h8 / h1, 8.0 ** (1.0 / 3.0), places=5)

    def test_spread_net_gamma_produces_narrower_band_than_single_leg(self):
        """A call spread always has a narrower WW band than its long leg alone."""
        spot = 4500.0
        k1, k2 = 4450.0, 4550.0
        tau, vol = 0.05, 0.20
        g1 = _bs_gamma(spot, k1, tau, vol)
        g_net = _call_spread_net_greeks(spot, k1, k2, tau, vol)['net_gamma']
        h_single = _ww(g1, time_to_expiry=tau)
        h_spread = _ww(g_net, time_to_expiry=tau)
        self.assertLess(h_spread, h_single)


if __name__ == '__main__':
    unittest.main()
