"""
Call Spread Market Making Strategy for SPX Options

This module implements the core market making strategy for SPX call spreads,
including signal generation, position management, and execution logic.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple

from ..models.pricing_engine import CallSpreadPricingEngine
from ..models.volatility_model import VolatilityModel

logger = logging.getLogger(__name__)


class CallSpreadMarketMakingStrategy:
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
        self.pricing_engine = CallSpreadPricingEngine()
        self.volatility_model = VolatilityModel()
        
        # Strategy state
        self.active_positions = {}
        self.target_spreads = []
        self.market_regime = 'normal'
        
        # Performance tracking
        self.pnl_history = []
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
            vix = market_data.get('vix', 20)
            
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
            
            # Calculate market indicators
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
    
    def manage_existing_positions(self) -> Dict[str, Any]:
        """
        Manage existing spread positions (profit taking, loss cutting, etc.).
        
        Returns:
            Dict containing position management results
        """
        try:
            management_results = []
            
            for position_id, position in self.active_positions.items():
                # Calculate current P&L
                current_pnl = self._calculate_position_pnl(position)
                
                # Check exit criteria
                exit_decision = self._evaluate_position_exit(position, current_pnl)
                
                if exit_decision.get('should_exit', False):
                    # Execute exit
                    exit_result = self._execute_position_exit(position_id, exit_decision)
                    management_results.append(exit_result)
                else:
                    # Update position tracking
                    position['last_update'] = datetime.now()
                    position['current_pnl'] = current_pnl
            
            return {
                'positions_managed': len(self.active_positions),
                'exits_executed': len(management_results),
                'management_results': management_results,
                'total_pnl': sum(pos.get('current_pnl', 0) for pos in self.active_positions.values()),
                'management_timestamp': datetime.now().isoformat(),
            }
            
        except Exception as e:
            self.logger.error(f"Error managing existing positions: {e}")
            return {
                'error': str(e),
                'positions_managed': 0,
                'management_timestamp': datetime.now().isoformat(),
            }
    
    def _recommend_spread_type(self, market_data: Dict[str, Any]) -> str:
        """Recommend spread type based on market conditions."""
        vix = market_data.get('vix', 20)
        trend = market_data.get('trend', 'neutral')  # bullish, bearish, neutral
        
        if trend == 'bullish' and vix < 25:
            return 'bull_call_spread'
        elif trend == 'bearish' or vix > 30:
            return 'bear_call_spread'
        else:
            return 'both'  # Consider both types
    
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
        
        # Strike spacing for SPX (typically 5 or 10 points)
        strike_spacing = 5 if spx_price < 3000 else 10
        
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
    
    def _execute_position_exit(self, position_id: str, exit_decision: Dict[str, Any]) -> Dict[str, Any]:
        """Execute position exit."""
        position = self.active_positions.pop(position_id, {})
        
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