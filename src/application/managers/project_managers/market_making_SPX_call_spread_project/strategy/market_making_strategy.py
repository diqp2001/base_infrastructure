"""
Call Spread Market Making Strategy for SPX Options

This module implements the core market making strategy for SPX call spreads,
including signal generation, position management, and execution logic.
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from ..models.pricing_model import PricingModel
from ..models.volatility_model import VolatilityModel
from .hedging.rebalancing_bands import compute_hedge_band, select_hedge_method as _select_hedge_method_fn
from .hedging.ww_ntbn import WWNTBNHedgePolicy


class Strategy:
    """
    Market making strategy for SPX call spreads.
    Implements systematic spread selection, pricing, and execution.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the market making strategy.
        
        Args:
            config: Strategy configuration parameters
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize components
        self.pricing_engine = PricingModel()
        self.volatility_model = VolatilityModel()
        
        # Strategy state
        self.active_positions = {}
        self.market_regime = 'normal'
        self.hedge_band_state: Dict[str, Any] = {}

        # WW-NTBN inference policy (loads weights when path is configured)
        self._ntbn_policy = WWNTBNHedgePolicy(
            weights_path=config.get('hedge_ntbn_weights_path', None)
        )

        # Performance tracking
        self.trade_history = []
        
        # Risk limits from config
        self.max_position_size = config.get('max_position_size', 10)
        self.max_daily_loss = config.get('max_daily_loss', 5000)
        self.max_gamma_exposure = config.get('max_gamma_exposure', 1000)
    
    def analyze_market_conditions(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze current market conditions to determine strategy parameters.
        
        Args:
            market_data: Current market data including SPX price, VIX, etc.
            
        Returns:
            Dict containing market analysis
        """
        try:
            spx_price = market_data.get('spx_price', 0)
            vix = market_data.get('vix')

            if vix is None:
                return {
                    'regime': self.market_regime,
                    'analysis_timestamp': datetime.now().isoformat(),
                }

            vix = float(vix)

            # Determine market regime
            if vix > 30:
                regime = 'high_volatility'
                spread_width_multiplier = 1.5
                position_size_multiplier = 0.7
            elif vix < 15:
                regime = 'low_volatility'
                spread_width_multiplier = 0.8
                position_size_multiplier = 1.2
            else:
                regime = 'normal'
                spread_width_multiplier = 1.0
                position_size_multiplier = 1.0

            self.market_regime = regime

            analysis = {
                'regime': regime,
                'vix_level': vix,
                'spx_price': spx_price,
                'spread_width_multiplier': spread_width_multiplier,
                'position_size_multiplier': position_size_multiplier,
                'recommended_spread_type': self._recommend_spread_type(market_data),
                'analysis_timestamp': datetime.now().isoformat(),
            }

            self.logger.info(f"Market regime: {regime}, VIX: {vix:.1f}")
            return analysis

        except Exception as e:
            self.logger.error(f"Error analyzing market conditions: {e}")
            return {
                'regime': 'normal',
                'error': str(e),
                'analysis_timestamp': datetime.now().isoformat(),
            }
    
    def select_hedge_method(
        self,
        market_analysis: Dict[str, Any],
        cost_rate: float,
    ) -> str:
        """Select the hedging model for the current regime and cost level.

        Delegates to the pure ``select_hedge_method`` function in
        ``rebalancing_bands``, reading the cost-high threshold from config.

        Returns one of 'whalley_wilmott', 'zakamouline', 'ww_ntbn'.
        """
        regime = market_analysis.get('regime', self.market_regime)
        threshold = float(self.config.get('hedge_cost_high_threshold', 0.005))
        return _select_hedge_method_fn(regime, cost_rate, threshold)

    def generate_spread_opportunities(
        self,
        spx_price: float,
        option_chain: Dict[str, Any],
        market_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Generate potential call spread opportunities.
        
        Args:
            spx_price: Current SPX price
            option_chain: Available option chain data
            market_analysis: Current market analysis
            
        Returns:
            List of spread opportunities
        """
        try:
            opportunities = []
            
            # Get configuration parameters
            dte_range = self.config.get('default_dte_range', (7, 45))
            delta_range = self.config.get('default_delta_range', (0.15, 0.45))
            max_width = self.config.get('max_spread_width', 50)
            
            # Adjust based on market conditions
            width_multiplier = market_analysis.get('spread_width_multiplier', 1.0)
            max_width_adjusted = int(max_width * width_multiplier)
            
            # Generate opportunities for different expiries
            expiry_dates = self._get_target_expiries(dte_range)
            
            for expiry in expiry_dates:
                days_to_expiry = (expiry - datetime.now()).days
                time_to_expiry = days_to_expiry / 365.25
                
                # Skip if too close to expiry
                if days_to_expiry < dte_range[0]:
                    continue
                
                # Generate bull and bear spread opportunities
                bull_spreads = self._generate_bull_spread_opportunities(
                    spx_price, time_to_expiry, delta_range, max_width_adjusted
                )
                
                bear_spreads = self._generate_bear_spread_opportunities(
                    spx_price, time_to_expiry, delta_range, max_width_adjusted
                )
                
                # Add expiry information
                for spread in bull_spreads + bear_spreads:
                    spread.update({
                        'expiry_date': expiry,
                        'days_to_expiry': days_to_expiry,
                        'time_to_expiry': time_to_expiry,
                    })
                
                opportunities.extend(bull_spreads + bear_spreads)
            
            # Score and rank opportunities
            scored_opportunities = self._score_opportunities(
                opportunities, market_analysis
            )
            
            # Sort by score
            scored_opportunities.sort(key=lambda x: x.get('score', 0), reverse=True)
            
            self.logger.info(f"Generated {len(scored_opportunities)} spread opportunities")
            return scored_opportunities[:20]  # Return top 20
            
        except Exception as e:
            self.logger.error(f"Error generating spread opportunities: {e}")
            return []
    
    def evaluate_spread_entry(self, spread_opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate whether to enter a specific spread position.
        
        Args:
            spread_opportunity: Spread opportunity data
            
        Returns:
            Dict containing entry evaluation
        """
        try:
            # Extract spread parameters
            spread_type = spread_opportunity.get('spread_type')
            k_long = spread_opportunity.get('long_strike')
            k_short = spread_opportunity.get('short_strike')
            time_to_expiry = spread_opportunity.get('time_to_expiry')
            
            # Get current market parameters
            spx_price = spread_opportunity.get('underlying_price', 4500)  # Default
            r = self.config.get('interest_rate', 0.05)
            q = self.config.get('dividend_yield', 0.015)
            
            # Get volatility estimate
            sigma = self.volatility_model.get_implied_volatility(
                k_long, spx_price, time_to_expiry
            )
            
            # Price the spread
            spread_pricing = self.pricing_engine.price_call_spread(
                spx_price, k_long, k_short, time_to_expiry, r, sigma, q, spread_type
            )
            
            # Calculate entry criteria
            min_profit_threshold = 0.15  # 15% minimum profit potential
            max_loss_threshold = 0.8     # Max 80% loss potential
            min_prob_profit = 0.4        # 40% minimum probability of profit
            
            profit_ratio = spread_pricing.get('profit_loss_ratio', 0)
            prob_profit = spread_pricing.get('probability_of_profit', 0)
            
            # Risk checks
            current_gamma = self._calculate_current_gamma_exposure()
            position_gamma = abs(spread_pricing.get('greeks', {}).get('gamma', 0))
            gamma_check = (current_gamma + position_gamma) <= self.max_gamma_exposure
            
            position_count_check = len(self.active_positions) < self.max_position_size
            
            # Entry decision
            should_enter = (
                profit_ratio >= min_profit_threshold and
                profit_ratio <= max_loss_threshold and
                prob_profit >= min_prob_profit and
                gamma_check and
                position_count_check
            )
            
            return {
                'should_enter': should_enter,
                'spread_pricing': spread_pricing,
                'entry_criteria': {
                    'profit_ratio': profit_ratio,
                    'profit_ratio_check': profit_ratio >= min_profit_threshold,
                    'probability_of_profit': prob_profit,
                    'prob_profit_check': prob_profit >= min_prob_profit,
                    'gamma_exposure_check': gamma_check,
                    'position_count_check': position_count_check,
                },
                'recommended_position_size': self._calculate_position_size(spread_pricing),
                'evaluation_timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Error evaluating spread entry: {e}")
            return {
                'should_enter': False,
                'error': str(e),
                'evaluation_timestamp': datetime.now().isoformat(),
            }
    
    def manage_existing_positions(
        self,
        market_data: Optional[Dict[str, Any]] = None,
        positions: Optional[Dict[str, Any]] = None,
        position_market_data: Optional[Dict[str, Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Manage existing spread positions (profit taking, loss cutting, delta hedging).

        Args:
            market_data: Optional market data forwarded to evaluate_portfolio_delta_hedge.
                Should contain at minimum spx_price and implied_vol (or vix).
            positions: The canonical position dict from the algorithm (self.positions).
                Falls back to self.active_positions when not provided.
            position_market_data: Market data for each position, used for evaluating P&L and exit criteria.

        Returns:
            Dict containing position management results
        """
        try:
            management_results = []
            exited_position_ids = []
            _market_data = market_data or {}
            _positions = positions if positions is not None else self.active_positions

            
           
            active_positions = {
                pid: pos for pid, pos in _positions.items()
                if pid not in exited_position_ids
            }
            portfolio_hedge = self.evaluate_portfolio_delta_hedge(
                _market_data, active_positions,
                position_market_data=position_market_data,
            )

            if (portfolio_hedge.get('should_hedge')
                    and portfolio_hedge.get('target_hedge_delta') is not None):
                self.hedge_band_state['_portfolio'] = {
                    'hedge_delta': portfolio_hedge['target_hedge_delta'],
                    'last_hedge_time': datetime.now().isoformat(),
                }

            return {
                'positions_managed': len(_positions),
                'exits_executed': len(management_results),
                'exited_position_ids': exited_position_ids,
                'management_results': management_results,
                'portfolio_hedge': portfolio_hedge,
                'total_pnl': sum(pos.get('current_pnl', 0) for pos in _positions.values()),
                'management_timestamp': datetime.now().isoformat(),
            }

        except Exception as e:
            self.logger.error(f"Error managing existing positions: {e}")
            return {
                'error': str(e),
                'positions_managed': 0,
                'management_timestamp': datetime.now().isoformat(),
            }
    
    def evaluate_portfolio_delta_hedge(
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

    def evaluate_delta_hedge(
        self,
        position_id: str,
        market_data: Dict[str, Any],
        positions: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Evaluate whether the delta hedge for a position needs rebalancing.

        Uses regime-switched no-trade band (NTB) logic to decide if the current
        unhedged delta is outside the allowable range.  When a hedge is warranted
        the recommendation targets the nearest band edge, not zero residual delta,
        to avoid immediately re-triggering the threshold.

        All greeks operate on NETTED spread exposure (both legs combined); per-leg
        bands are NOT used because their intersection can be empty near ATM.

        Args:
            position_id: Position key in ``positions`` (or ``self.active_positions``).
            market_data: Dict with at minimum:
                spx_price (float): Current SPX spot price.
                implied_vol (float, optional): Bar-level override; position greeks take precedence.
            positions: Canonical position store from the algorithm layer.
                Falls back to ``self.active_positions`` when None.

        Returns:
            Dict with keys:
                should_hedge (bool)
                position_id (str)
                net_residual_delta (float): Unhedged delta = position delta + current hedge.
                band_half_width (float)
                model_used (str): Hedging model that was applied.
                current_hedge_delta (float)
                band_info (dict): Full band output from the selected model.
                evaluation_timestamp (str): ISO timestamp.
                hedge_direction (str): 'buy' or 'sell' — only when should_hedge is True.
                hedge_trade_delta (float): Absolute delta to trade — only when should_hedge.
                target_hedge_delta (float): Target hedge delta — only when should_hedge.
        """
        try:
            _positions = positions if positions is not None else self.active_positions
            position = _positions.get(position_id, {})
            greeks = position.get('greeks', {})
            # signed quantity: negative for short positions (quantity stored signed from DB)
            size = position.get('size', 1)

            # NETTED spread greeks: both legs already aggregated; scale by signed contracts
            net_gamma = greeks.get('net_gamma', greeks.get('gamma', 0)) * size
            net_delta = greeks.get('net_delta', greeks.get('delta', 0)) * size

            _spy_bar = next(
                (bar for sym, bar in getattr(market_data, 'bars', {}).items()
                 if str(getattr(sym, 'value', sym)) == 'SPY'),
                None,
            )
            spot = float(_spy_bar.close) if _spy_bar is not None else float(
                market_data.get('spy_price', market_data.get('spx_price', market_data.get('spot', 500.0)))
            )

            # Per-option IV stored at pricing time takes precedence;
            # market_data['implied_vol'] may override it for the current bar.
            _iv = (
                greeks.get('implied_vol')
                or market_data.get('implied_vol')
            )
            implied_vol: Optional[float] = float(_iv) if _iv is not None else None
            time_to_expiry = float(
                position.get('time_to_expiry', position.get('days_to_expiry', 30) / 365.25)
            )
            cost_rate = float(self.config.get('hedge_transaction_cost_rate', 0.0001))
            risk_aversion = float(self.config.get('hedge_risk_aversion', 1.0))
            risk_free_rate = float(self.config.get('interest_rate', 0.05))

            # --- Regime dispatch (audit-logged) ---
            method_name = self.select_hedge_method({'regime': self.market_regime}, cost_rate)

            # Zakamouline requires vol; WW-NTBN with loaded weights also needs vol.
            # If vol is absent, skip hedging — do not substitute a hardcoded default.
            needs_vol = method_name == 'zakamouline' or (
                method_name == 'ww_ntbn' and self._ntbn_policy._loaded
            )
            if needs_vol and implied_vol is None:
                self.logger.debug(
                    "Skipping delta hedge for %s: implied_vol absent (method=%s)",
                    position_id, method_name,
                )
                return {
                    'should_hedge': False,
                    'position_id': position_id,
                    'reason': 'no_implied_vol',
                    'evaluation_timestamp': datetime.now().isoformat(),
                }

            self.logger.info(
                "Delta hedge method selected: %s "
                "(regime=%s, cost_rate=%.4f, position_id=%s)",
                method_name, self.market_regime, cost_rate, position_id,
            )

            if method_name == 'ww_ntbn':
                strike = float(
                    position.get('strikes', {}).get('long', spot)
                    or position.get('strike', spot)
                    or spot
                )
                ntbn_result = self._ntbn_policy.compute_hedge(
                    gamma_net=net_gamma,
                    spot=spot,
                    strike=strike,
                    tau=time_to_expiry,
                    vol=implied_vol or 0.0,  # fallback path (no weights) doesn't use vol
                    prev_hedge=float(
                        self.hedge_band_state.get(position_id, {}).get('hedge_delta', 0.0)
                    ),
                    r=risk_free_rate,
                    cost_rate=cost_rate,
                    risk_aversion=risk_aversion,
                )
                band_info: Dict[str, Any] = {
                    'half_width': ntbn_result['half_width'],
                    'model_used': ntbn_result['model_used'],
                    'regime': self.market_regime,
                    'ww_half_width': ntbn_result['ww_prior'],
                    'zakamouline_half_width': None,
                    'ntbn_residual': ntbn_result['residual'],
                }
            else:
                # WW or Zakamouline — force the select_hedge_method decision
                regime_map_override = dict(self.config.get('hedge_band_regime_map', {}))
                regime_map_override[self.market_regime] = method_name
                band_info = compute_hedge_band(
                    gamma=net_gamma,
                    spot=spot,
                    cost_rate=cost_rate,
                    risk_aversion=risk_aversion,
                    regime=self.market_regime,
                    time_to_expiry=time_to_expiry,
                    implied_vol=implied_vol,
                    risk_free_rate=risk_free_rate,
                    regime_map=regime_map_override,
                )

            half_width = band_info['half_width']
            current_hedge_delta = float(
                self.hedge_band_state.get(position_id, {}).get('hedge_delta', 0.0)
            )
            net_residual_delta = net_delta + current_hedge_delta

            base = {
                'position_id': position_id,
                'net_residual_delta': net_residual_delta,
                'band_half_width': half_width,
                'model_used': band_info['model_used'],
                'current_hedge_delta': current_hedge_delta,
                'band_info': band_info,
                'evaluation_timestamp': datetime.now().isoformat(),
            }

            if abs(net_residual_delta) <= half_width:
                return {'should_hedge': False, **base}

            # Outside band — trade to the nearest edge, not to zero
            sign = 1.0 if net_residual_delta > 0 else -1.0
            target_hedge_delta = sign * half_width - net_delta
            hedge_trade_delta = target_hedge_delta - current_hedge_delta

            return {
                'should_hedge': True,
                'hedge_direction': 'buy' if hedge_trade_delta > 0 else 'sell',
                'hedge_trade_delta': abs(hedge_trade_delta),
                'target_hedge_delta': target_hedge_delta,
                **base,
            }

        except Exception as e:
            self.logger.error(f"Error evaluating delta hedge for {position_id}: {e}")
            return {
                'should_hedge': False,
                'position_id': position_id,
                'error': str(e),
                'evaluation_timestamp': datetime.now().isoformat(),
            }

    def _recommend_spread_type(self, market_data: Dict[str, Any]) -> str:
        """Recommend spread type based on market conditions."""
        vix = market_data.get('vix')
        trend = market_data.get('trend', 'neutral')

        if vix is None:
            return 'both'

        vix = float(vix)
        if trend == 'bullish' and vix < 25:
            return 'bull_call_spread'
        elif trend == 'bearish' or vix > 30:
            return 'bear_call_spread'
        return 'both'
    
    def _get_target_expiries(self, dte_range: Tuple[int, int]) -> List[datetime]:
        """Get target expiry dates within the specified range."""
        today = datetime.now()
        expiries = []
        
        # Generate weekly expiries (SPX has weekly options)
        for weeks_ahead in range(1, 8):  # Up to 8 weeks
            expiry = today + timedelta(weeks=weeks_ahead)
            # Adjust to Friday (typical expiry day)
            days_until_friday = (4 - expiry.weekday()) % 7
            expiry += timedelta(days=days_until_friday)
            
            days_to_expiry = (expiry - today).days
            if dte_range[0] <= days_to_expiry <= dte_range[1]:
                expiries.append(expiry)
        
        return expiries
    
    def _generate_bull_spread_opportunities(
        self,
        spx_price: float,
        time_to_expiry: float,
        delta_range: Tuple[float, float],
        max_width: int
    ) -> List[Dict[str, Any]]:
        """Generate bull call spread opportunities."""
        opportunities = []
        
        # Generate potential long strikes around target delta
        for target_delta in np.arange(delta_range[0], delta_range[1], 0.05):
            optimal_strikes = self.pricing_engine.find_optimal_spread_strikes(
                spx_price, time_to_expiry, 0.05, 0.2, 0.015,
                target_delta, max_width, 'bull'
            )
            
            if optimal_strikes.get('success', False):
                spread_data = optimal_strikes.get('spread_data', {})
                opportunities.append({
                    'spread_type': 'bull_call_spread',
                    'long_strike': optimal_strikes['optimal_strikes']['long'],
                    'short_strike': optimal_strikes['optimal_strikes']['short'],
                    'underlying_price': spx_price,
                    'target_delta': target_delta,
                    'spread_data': spread_data,
                })
        
        return opportunities
    
    def _generate_bear_spread_opportunities(
        self,
        spx_price: float,
        time_to_expiry: float,
        delta_range: Tuple[float, float],
        max_width: int
    ) -> List[Dict[str, Any]]:
        """Generate bear call spread opportunities."""
        opportunities = []
        
        # Generate bear spreads with different short deltas
        for target_delta in np.arange(delta_range[0], delta_range[1], 0.05):
            optimal_strikes = self.pricing_engine.find_optimal_spread_strikes(
                spx_price, time_to_expiry, 0.05, 0.2, 0.015,
                target_delta, max_width, 'bear'
            )
            
            if optimal_strikes.get('success', False):
                spread_data = optimal_strikes.get('spread_data', {})
                opportunities.append({
                    'spread_type': 'bear_call_spread',
                    'long_strike': optimal_strikes['optimal_strikes']['long'],
                    'short_strike': optimal_strikes['optimal_strikes']['short'],
                    'underlying_price': spx_price,
                    'target_delta': target_delta,
                    'spread_data': spread_data,
                })
        
        return opportunities
    
    def _score_opportunities(
        self,
        opportunities: List[Dict[str, Any]],
        market_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Score and rank spread opportunities."""
        for opp in opportunities:
            spread_data = opp.get('spread_data', {})
            
            # Base scoring factors
            profit_ratio = spread_data.get('profit_loss_ratio', 0)
            prob_profit = spread_data.get('probability_of_profit', 0)
            theta = abs(spread_data.get('greeks', {}).get('theta', 0))
            
            # Calculate composite score
            score = (
                profit_ratio * 0.3 +        # 30% weight on profit ratio
                prob_profit * 0.4 +         # 40% weight on probability
                theta * 0.2 +               # 20% weight on time decay
                (1 / (opp.get('days_to_expiry', 30) / 30)) * 0.1  # 10% on time preference
            )
            
            # Adjust score based on market regime
            regime = market_analysis.get('regime', 'normal')
            spread_type = opp.get('spread_type', '')
            
            if regime == 'high_volatility' and 'bear' in spread_type:
                score *= 1.2  # Prefer bear spreads in high vol
            elif regime == 'low_volatility' and 'bull' in spread_type:
                score *= 1.1  # Slight preference for bull spreads in low vol
            
            opp['score'] = score
        
        return opportunities
    
    def _calculate_current_gamma_exposure(self) -> float:
        """Calculate total gamma exposure from all positions."""
        total_gamma = 0
        for position in self.active_positions.values():
            gamma = position.get('greeks', {}).get('gamma', 0)
            size = position.get('size', 0)
            total_gamma += gamma * size
        return abs(total_gamma)
    
    def _calculate_position_size(self, spread_pricing: Dict[str, Any]) -> int:
        """Calculate recommended position size based on risk parameters."""
        max_loss_per_spread = spread_pricing.get('max_loss', 100)
        max_position_risk = min(self.max_daily_loss * 0.1, 1000)  # 10% of daily limit
        
        if max_loss_per_spread > 0:
            size = int(max_position_risk / max_loss_per_spread)
            return max(1, min(size, 5))  # Between 1 and 5 spreads
        return 1
    
    def _calculate_position_pnl(self, position: Dict[str, Any]) -> float:
        """Calculate current P&L for a position."""
        # Placeholder implementation
        # In practice, this would use current market prices to calculate P&L
        entry_price = position.get('entry_price', 0)
        current_price = position.get('current_price', entry_price)  # Would be updated from market
        size = position.get('size', 0)
        
        return (current_price - entry_price) * size * 100  # SPX multiplier
    
    def _evaluate_position_exit(self, position: Dict[str, Any], current_pnl: float) -> Dict[str, Any]:
        """Evaluate whether to exit a position."""
        entry_time = position.get('entry_time', datetime.now())
        days_in_position = (datetime.now() - entry_time).days
        
        # Exit criteria
        profit_target = position.get('max_profit', 0) * 0.5  # 50% of max profit
        loss_limit = position.get('max_loss', 0) * 0.8       # 80% of max loss
        
        should_exit = (
            current_pnl >= profit_target or      # Profit target hit
            current_pnl <= -loss_limit or       # Loss limit hit
            days_in_position >= 14 or           # Time-based exit
            position.get('days_to_expiry', 0) <= 7  # Close to expiry
        )
        
        return {
            'should_exit': should_exit,
            'exit_reason': self._get_exit_reason(current_pnl, profit_target, loss_limit, days_in_position),
            'current_pnl': current_pnl,
        }
    
    def _get_exit_reason(self, pnl: float, profit_target: float, loss_limit: float, days: int) -> str:
        """Determine the reason for exit."""
        if pnl >= profit_target:
            return 'profit_target'
        elif pnl <= -loss_limit:
            return 'loss_limit'
        elif days >= 14:
            return 'time_exit'
        else:
            return 'expiry_approach'
    
    def _execute_position_exit(self, position_id: str, exit_decision: Dict[str, Any], positions: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute position exit."""
        _positions = positions if positions is not None else self.active_positions
        position = _positions.pop(position_id, {})
        
        # Record trade history
        trade_record = {
            'position_id': position_id,
            'exit_time': datetime.now(),
            'exit_reason': exit_decision.get('exit_reason'),
            'final_pnl': exit_decision.get('current_pnl', 0),
            'position_data': position,
        }
        
        self.trade_history.append(trade_record)
        
        return {
            'position_id': position_id,
            'exit_executed': True,
            'final_pnl': exit_decision.get('current_pnl', 0),
            'exit_reason': exit_decision.get('exit_reason'),
        }