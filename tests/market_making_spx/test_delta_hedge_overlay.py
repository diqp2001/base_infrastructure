"""
Delta-hedge overlay (domain, construction/delta_hedge.py) used by the SPX call-spread Strategy of both projects.

Regression: ``OLD_evaluate_portfolio_delta_hedge`` below is Strategy.evaluate_portfolio_delta_hedge before the move
(commit f0f49bba), frozen verbatim; on random books the refactored Strategy (v1 and v2 copies) returns the same
decision (every key but the timestamps), including the error path.
"""

import math
import random
import unittest
from datetime import datetime
from typing import Any, Dict, Optional

from src.application.managers.project_managers.market_making_SPX_call_spread_project import config as v1_config
from src.application.managers.project_managers.market_making_SPX_call_spread_project.strategy.hedging.rebalancing_bands import (  # noqa: E501
    compute_hedge_band,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project.strategy.market_making_strategy import (  # noqa: E501
    Strategy as V1Strategy,
)
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2 import config as v2_config
from src.application.managers.project_managers.market_making_SPX_call_spread_project_v2.strategy.market_making_strategy import (  # noqa: E501
    Strategy as V2Strategy,
)
from src.domain.entities.factor.trading_strategy.spx_call_spread_strategy import SPXCallSpreadTradingStrategy
from src.domain.entities.factor.trading_strategy.trading_strategy import TradingStrategy
from src.domain.entities.finance.portfolio.construction.delta_hedge import (
    OptionExposure,
    aggregate_book_greeks,
    delta_hedge_decision,
)


# ------------------------------------------------------------------ frozen pre-refactor method (verbatim)
def OLD_evaluate_portfolio_delta_hedge(
    self,
    market_data: Dict[str, Any],
    positions: Optional[Dict[str, Any]] = None,
    position_market_data: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Evaluate whether the aggregate portfolio delta requires a hedge trade.

    Sums position deltas and gammas across all active positions to get the
    net book exposure, then applies the no-trade band to that aggregate.
    This produces ONE hedge decision for the whole portfolio, which is the
    correct framing for a delta-neutral market-making strategy.

    The implied-vol and time-to-expiry inputs for the band model are computed
    as |gamma|-weighted averages across positions so the most gamma-sensitive
    legs dominate the band width.

    Args:
        market_data: Dict with at minimum:
            spx_price (float): Current SPX spot price.
            implied_vol (float, optional): Last-resort fallback vol when no position
                greeks and no position_market_data entry carry one.
        positions: Active position store; falls back to self.active_positions.
        position_market_data: Per-symbol factor values from _load_position_market_data,
            keyed by option symbol.  Used as the second-priority IV source (after
            pos['greeks']['implied_vol'], before market_data['implied_vol']).

    Returns:
        Dict with keys:
            should_hedge (bool)
            portfolio_delta (float): Sum of all position deltas.
            portfolio_gamma (float): Sum of all position gammas.
            net_residual_delta (float): portfolio_delta + current_hedge.
            band_half_width (float)
            model_used (str)
            current_hedge_delta (float)
            position_count (int)
            evaluation_timestamp (str)
            hedge_direction, hedge_trade_delta, target_hedge_delta — only when should_hedge.
    """
    _PORTFOLIO_KEY = '_portfolio'
    try:
        _positions = positions if positions is not None else self.active_positions

        portfolio_delta = 0.0
        portfolio_gamma = 0.0
        total_gamma_weight = 0.0
        weighted_iv = 0.0
        weighted_tau = 0.0

        _pmd = position_market_data or {}

        for pos in _positions.values():
            greeks = pos.get('greeks', {})
            # signed quantity: negative for short positions (quantity stored signed from DB)
            size = pos.get('size', 1)

            # position delta: ∂V/∂S × signed contracts  (net_ key used when spread legs are pre-netted)
            # size is negative for short → p_delta is negative for a short call (positive BSM delta)
            p_delta = greeks.get('net_delta', greeks.get('delta', 0)) * size
            # position gamma: ∂²V/∂S² × signed contracts
            p_gamma = greeks.get('net_gamma', greeks.get('gamma', 0)) * size
            # |gamma| used as the weighting factor for IV and tau averages
            abs_gamma = abs(p_gamma)

            # running sum: Σ(delta_i × size_i) → net portfolio delta
            portfolio_delta += p_delta
            # running sum: Σ(gamma_i × size_i) → net portfolio gamma (signed)
            portfolio_gamma += p_gamma
            # running sum: Σ|gamma_i × size_i| → total weight for weighted averages
            total_gamma_weight += abs_gamma

            # IV priority: stored greek > position_market_data resolved value > market_data fallback later
            iv = greeks.get('implied_vol')
            if iv is None:
                symbol = pos.get('symbol')
                if symbol:
                    iv = _pmd.get(symbol, {}).get('greeks', {}).get('implied_vol')

            # time to expiry in years; fall back to 30 calendar days if not stored
            tau = float(pos.get('time_to_expiry', pos.get('days_to_expiry', 30) / 365.25))
            # accumulate |gamma|-weighted IV numerator: Σ(|gamma_i| × iv_i)
            if iv is not None:
                weighted_iv += abs_gamma * float(iv)
            # accumulate |gamma|-weighted tau numerator: Σ(|gamma_i| × tau_i)
            weighted_tau += abs_gamma * tau

        # aggregate gamma = signed sum of all position gammas (used for band width formula)
        agg_gamma = portfolio_gamma
        if total_gamma_weight > 0:
            # |gamma|-weighted average IV: Σ(|γ_i|·σ_i) / Σ|γ_i|  — None if no IV was available
            implied_vol_agg = weighted_iv / total_gamma_weight if weighted_iv > 0 else None
            # |gamma|-weighted average time-to-expiry: Σ(|γ_i|·τ_i) / Σ|γ_i|
            time_to_expiry = weighted_tau / total_gamma_weight
        else:
            # no positions with gamma — cannot weight; set sensible defaults
            implied_vol_agg = None
            time_to_expiry = 30.0 / 365.25

        # last-resort IV fallback: bar-level market_data (e.g. VIX proxy) if no position supplied one
        if implied_vol_agg is None:
            _iv = market_data.get('implied_vol')
            implied_vol_agg = float(_iv) if _iv is not None else None

        # Extract SPY spot from Slice.bars (Symbol keys; options have spaces, equity does not)
        _spy_bar = next(
            (bar for sym, bar in getattr(market_data, 'bars', {}).items()
             if str(getattr(sym, 'value', sym)) == 'SPY'),
            None,
        )
        spot = float(_spy_bar.close) if _spy_bar is not None else float(
            market_data.get('spy_price', market_data.get('spx_price', market_data.get('spot', 500.0)))
        )
        cost_rate = float(self.config.get('hedge_transaction_cost_rate', 0.0001))
        risk_aversion = float(self.config.get('hedge_risk_aversion', 1.0))
        risk_free_rate = float(self.config.get('interest_rate', 0.05))

        method_name = self.select_hedge_method({'regime': self.market_regime}, cost_rate)

        needs_vol = method_name == 'zakamouline' or (
            method_name == 'ww_ntbn' and self._ntbn_policy._loaded
        )
        if needs_vol and implied_vol_agg is None:
            self.logger.debug(
                "Skipping portfolio delta hedge: implied_vol absent (method=%s)", method_name
            )
            return {
                'should_hedge': False,
                'reason': 'no_implied_vol',
                'portfolio_delta': portfolio_delta,
                'portfolio_gamma': portfolio_gamma,
                'position_count': len(_positions),
                'evaluation_timestamp': datetime.now().isoformat(),
            }

        self.logger.info(
            "Portfolio delta hedge method: %s (regime=%s, net_delta=%.4f, net_gamma=%.4f)",
            method_name, self.market_regime, portfolio_delta, portfolio_gamma,
        )

        if method_name == 'ww_ntbn':
            ntbn_result = self._ntbn_policy.compute_hedge(
                gamma_net=agg_gamma,
                spot=spot,
                strike=spot,
                tau=time_to_expiry,
                vol=implied_vol_agg or 0.0,
                prev_hedge=float(
                    self.hedge_band_state.get(_PORTFOLIO_KEY, {}).get('hedge_delta', 0.0)
                ),
                r=risk_free_rate,
                cost_rate=cost_rate,
                risk_aversion=risk_aversion,
            )
            band_info: Dict[str, Any] = {
                'half_width': ntbn_result['half_width'],
                'model_used': ntbn_result['model_used'],
                'regime': self.market_regime,
                'ww_half_width': ntbn_result.get('ww_prior'),
                'zakamouline_half_width': None,
                'ntbn_residual': ntbn_result.get('residual'),
            }
        else:
            regime_map_override = dict(self.config.get('hedge_band_regime_map', {}))
            regime_map_override[self.market_regime] = method_name
            band_info = compute_hedge_band(
                gamma=agg_gamma,
                spot=spot,
                cost_rate=cost_rate,
                risk_aversion=risk_aversion,
                regime=self.market_regime,
                time_to_expiry=time_to_expiry,
                implied_vol=implied_vol_agg,
                risk_free_rate=risk_free_rate,
                regime_map=regime_map_override,
            )

        half_width = band_info['half_width']
        current_hedge_delta = float(
            self.hedge_band_state.get(_PORTFOLIO_KEY, {}).get('hedge_delta', 0.0)
        )
        net_residual_delta = portfolio_delta + current_hedge_delta

        base = {
            'portfolio_delta': portfolio_delta,
            'portfolio_gamma': portfolio_gamma,
            'net_residual_delta': net_residual_delta,
            'band_half_width': half_width,
            'model_used': band_info['model_used'],
            'current_hedge_delta': current_hedge_delta,
            'band_info': band_info,
            'position_count': len(_positions),
            'evaluation_timestamp': datetime.now().isoformat(),
        }

        if abs(net_residual_delta) <= half_width:
            return {'should_hedge': False, **base}

        # Band breached: hedge all the way to delta=0, not just to the band edge.
        # target_hedge_delta = -portfolio_delta  →  net residual after hedge = 0
        target_hedge_delta = -portfolio_delta
        # incremental SPY trade on top of the hedge already in place
        hedge_trade_delta = target_hedge_delta - current_hedge_delta

        return {
            'should_hedge': True,
            'hedge_direction': 'buy' if hedge_trade_delta > 0 else 'sell',
            'hedge_trade_delta': abs(hedge_trade_delta),
            'target_hedge_delta': target_hedge_delta,
            **base,
        }

    except Exception as e:
        self.logger.error(f"Error evaluating portfolio delta hedge: {e}")
        return {
            'should_hedge': False,
            'error': str(e),
            'evaluation_timestamp': datetime.now().isoformat(),
        }


# ------------------------------------------------------------------ random books
def _book(rng):
    positions, pmd = {}, {}
    for i in range(rng.randint(0, 6)):
        symbol = f"SPY   2812{i:02d}C00{rng.randint(500, 800)}000"
        greeks = {}
        key = rng.choice(["delta", "net_delta"])
        greeks[key] = rng.uniform(-1, 1)
        if rng.random() < 0.9:
            greeks[rng.choice(["gamma", "net_gamma"])] = rng.choice([0.0, rng.uniform(-0.05, 0.05)])
        u = rng.random()
        if u < 0.4:
            greeks["implied_vol"] = rng.uniform(0.05, 0.6)
        elif u < 0.7:
            pmd[symbol] = {"greeks": {"implied_vol": rng.uniform(0.05, 0.6)}}
        pos = {"symbol": symbol, "greeks": greeks, "size": rng.choice([-10, -2, -1, 1, 3])}
        v = rng.random()
        if v < 0.3:
            pos["time_to_expiry"] = rng.uniform(0.01, 1.0)
        elif v < 0.6:
            pos["days_to_expiry"] = rng.randint(1, 400)
        positions[f"p{i}"] = pos
    market = {"spy_price": rng.uniform(400, 700)}
    if rng.random() < 0.5:
        market["implied_vol"] = rng.uniform(0.1, 0.4)
    return positions, market, pmd


def _strategy(cls, config, rng):
    s = cls(dict(config, hedge_transaction_cost_rate=rng.choice([0.0001, 0.001, 0.01]),
                 hedge_risk_aversion=rng.choice([0.5, 1.0, 3.0])))
    s.market_regime = rng.choice(["normal", "low_vol", "high_vol"])
    if rng.random() < 0.6:
        s.hedge_band_state["_portfolio"] = {"hedge_delta": rng.uniform(-8, 8)}
    return s


def _without_timestamps(d):
    return {k: v for k, v in d.items() if k not in ("evaluation_timestamp",)}


class DeltaHedgeRegressionTest(unittest.TestCase):

    def _compare(self, cls, config, seed):
        rng = random.Random(seed)
        hedged = quiet = 0
        for i in range(400):
            positions, market, pmd = _book(rng)
            state = rng.getstate()
            old_s, new_s = _strategy(cls, config, rng), None
            rng.setstate(state)
            new_s = _strategy(cls, config, rng)
            old = OLD_evaluate_portfolio_delta_hedge(old_s, market, positions, position_market_data=pmd)
            new = new_s.evaluate_portfolio_delta_hedge(market, positions, position_market_data=pmd)
            self.assertEqual(_without_timestamps(new), _without_timestamps(old), i)
            hedged += bool(old.get("should_hedge"))
            quiet += old.get("should_hedge") is False
        self.assertGreater(hedged, 20)
        self.assertGreater(quiet, 20)

    def test_v1_strategy_decides_as_before(self):
        self._compare(V1Strategy, v1_config.get_config(), 1)

    def test_v2_strategy_decides_as_before(self):
        self._compare(V2Strategy, v2_config.get_config(), 2)

    def test_a_broken_greek_is_the_same_error(self):
        for cls, cfg in ((V1Strategy, v1_config.get_config()), (V2Strategy, v2_config.get_config())):
            positions = {"p": {"symbol": "X", "greeks": {"delta": None, "gamma": 0.01}, "size": -1}}
            old = OLD_evaluate_portfolio_delta_hedge(cls(cfg), {"spy_price": 500.0}, positions)
            new = cls(cfg).evaluate_portfolio_delta_hedge({"spy_price": 500.0}, positions)
            self.assertEqual(_without_timestamps(new), _without_timestamps(old))
            self.assertIn("error", new)


class OverlayTest(unittest.TestCase):

    def test_aggregation_weights_iv_and_expiry_by_absolute_gamma(self):
        book = aggregate_book_greeks([OptionExposure(0.6, 0.02, -10, 0.2, 0.1),
                                      OptionExposure(0.4, 0.01, 5, None, 0.5)])
        self.assertAlmostEqual(book.delta, -6 + 2)
        self.assertAlmostEqual(book.gamma, -0.2 + 0.05)
        self.assertAlmostEqual(book.implied_vol, 0.2 * 0.2 / 0.25)
        self.assertAlmostEqual(book.time_to_expiry, (0.2 * 0.1 + 0.05 * 0.5) / 0.25)
        empty = aggregate_book_greeks([])
        self.assertEqual((empty.implied_vol, empty.time_to_expiry, empty.position_count), (None, 30 / 365.25, 0))

    def test_inside_the_band_no_trade_outside_back_to_delta_zero(self):
        self.assertFalse(delta_hedge_decision(-5.0, 4.0, 1.5).should_hedge)
        d = delta_hedge_decision(-5.0, 1.0, 1.5)
        self.assertEqual((d.should_hedge, d.target_hedge, d.trade, d.direction), (True, 5.0, 4.0, "buy"))

    def test_the_strategy_builds_the_entry_and_hedge_targets(self):
        spx = SPXCallSpreadTradingStrategy(option_symbol="OPT", entry_weight=-0.2, hedge_symbol="SPY")
        self.assertIsInstance(spx, TradingStrategy)
        self.assertEqual(spx.calculate_dependencies, [])
        self.assertTrue(spx.wants_entry(0))
        self.assertFalse(spx.wants_entry(-2))
        entry = spx.entry_target(datetime(2026, 8, 24, 16))
        self.assertEqual([(p.symbol, p.target_weight, p.asset_type, p.target_quantity) for p in entry],
                         [("OPT", -0.2, "CompanyShareOption", None)])
        hedge = spx.hedge_target(-120.0)
        self.assertEqual([(p.symbol, p.target_quantity, p.asset_type) for p in hedge],
                         [("SPY", -120.0, "CompanyShare")])
        self.assertEqual(hedge.construction, "delta_hedge")
        with self.assertRaises(ValueError):
            spx.hedge_target(math.nan)
        self.assertFalse(SPXCallSpreadTradingStrategy().wants_entry(0))      # no option configured


class AlgorithmSourceTest(unittest.TestCase):

    def test_both_projects_send_target_portfolios(self):
        import ast
        from pathlib import Path
        root = Path(__file__).resolve().parents[2] / "src/application/managers/project_managers"
        for rel in ("market_making_SPX_call_spread_project/backtesting/base_project_algorithm.py",
                    "market_making_SPX_call_spread_project_v2/strategy/trading_cycle.py"):
            tree = ast.parse((root / rel).read_text(encoding="utf-8"))
            for call in [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                         and n.func.attr == "set_holdings"]:
                self.assertNotIsInstance(call.args[0], ast.Dict, (rel, ast.unparse(call)))


if __name__ == "__main__":
    unittest.main()
