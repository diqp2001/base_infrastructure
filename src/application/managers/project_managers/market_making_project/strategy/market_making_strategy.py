"""
Market Making Strategy for Derivatives Trading

Implements sophisticated market making strategies with:
- Dynamic spread management
- Inventory-aware pricing
- Risk management integration
- Multi-asset class support
"""

import logging
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
import math


class MarketMakingStrategy:
    """
    Advanced market making strategy that manages:
    - Bid-ask spread optimization
    - Inventory risk management
    - Position sizing and limits
    - Cross-asset hedging
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize the market making strategy.
        
        Args:
            config: Strategy configuration parameters
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Strategy parameters
        self.base_spread_bps = self.config.get('base_spread_bps', 15)
        self.min_spread_bps = self.config.get('min_spread_bps', 5)
        self.max_spread_bps = self.config.get('max_spread_bps', 50)
        
        # Inventory management
        self.max_inventory_per_symbol = self.config.get('max_inventory', Decimal('10000'))
        self.inventory_penalty_factor = self.config.get('inventory_penalty', Decimal('0.1'))
        self.target_inventory = self.config.get('target_inventory', Decimal('0'))
        
        # Risk management
        self.max_portfolio_var = self.config.get('max_portfolio_var', Decimal('0.05'))
        self.var_lookback_days = self.config.get('var_lookback_days', 20)
        
        # Position sizing
        self.default_quote_size = self.config.get('default_quote_size', 100)
        self.size_scaling_factor = self.config.get('size_scaling_factor', Decimal('1.0'))
        
        # Current state
        self.current_inventory = {}
        self.current_positions = {}
        self.risk_metrics = {}
        
        self.logger.info("MarketMakingStrategy initialized")
    
    def calculate_optimal_spreads(self, symbol: str, market_data: Dict[str, Any],
                                 current_inventory: Decimal) -> Dict[str, Any]:
        """
        Calculate optimal bid-ask spreads based on market conditions and inventory.
        
        Args:
            symbol: Instrument symbol
            market_data: Current market data
            current_inventory: Current inventory position
            
        Returns:
            Optimal spread parameters
        """
        try:
            # Base spread calculation
            base_spread = self._calculate_base_spread(symbol, market_data)
            
            # Volatility adjustment
            volatility_adj = self._calculate_volatility_adjustment(market_data)
            
            # Inventory adjustment
            inventory_adj = self._calculate_inventory_adjustment(symbol, current_inventory)
            
            # Liquidity adjustment
            liquidity_adj = self._calculate_liquidity_adjustment(market_data)
            
            # Market regime adjustment
            regime_adj = self._calculate_regime_adjustment(market_data)
            
            # Combine all adjustments
            total_spread = base_spread + volatility_adj + inventory_adj + liquidity_adj + regime_adj
            
            # Apply bounds
            final_spread = max(
                Decimal(str(self.min_spread_bps)) / Decimal('10000'),
                min(
                    Decimal(str(self.max_spread_bps)) / Decimal('10000'),
                    total_spread
                )
            )
            
            return {
                'total_spread': final_spread,
                'components': {
                    'base_spread': base_spread,
                    'volatility_adjustment': volatility_adj,
                    'inventory_adjustment': inventory_adj,
                    'liquidity_adjustment': liquidity_adj,
                    'regime_adjustment': regime_adj
                },
                'spread_bps': float(final_spread * Decimal('10000')),
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Error calculating optimal spreads for {symbol}: {str(e)}")
            # Return default spread on error
            default_spread = Decimal(str(self.base_spread_bps)) / Decimal('10000')
            return {
                'total_spread': default_spread,
                'spread_bps': float(default_spread * Decimal('10000')),
                'error': str(e)
            }
    
    def _calculate_base_spread(self, symbol: str, market_data: Dict[str, Any]) -> Decimal:
        """Calculate base spread based on instrument characteristics."""
        base_spread = Decimal(str(self.base_spread_bps)) / Decimal('10000')
        
        # Adjust based on asset class
        asset_class = market_data.get('asset_class', 'equity')
        
        if asset_class == 'equity':
            # Adjust based on market cap for equities
            market_cap = market_data.get('market_cap', Decimal('100000000000'))
            if market_cap < Decimal('1000000000'):  # < $1B (small cap)
                base_spread *= Decimal('2.0')
            elif market_cap < Decimal('10000000000'):  # < $10B (mid cap)
                base_spread *= Decimal('1.5')
            
        elif asset_class == 'fixed_income':
            # Tighter spreads for bonds
            base_spread *= Decimal('0.5')
            
        elif asset_class == 'commodity':
            # Wider spreads for commodities
            base_spread *= Decimal('1.5')
        
        return base_spread
    
    def _calculate_volatility_adjustment(self, market_data: Dict[str, Any]) -> Decimal:
        """Calculate spread adjustment based on volatility."""
        volatility = market_data.get('volatility', Decimal('0.20'))
        
        # Linear scaling: higher volatility = wider spreads
        # Base assumption: 20% vol = no adjustment
        vol_adjustment = (volatility - Decimal('0.20')) * Decimal('0.5')
        
        return max(Decimal('0'), vol_adjustment)
    
    def _calculate_inventory_adjustment(self, symbol: str, inventory: Decimal) -> Decimal:
        """Calculate spread adjustment based on current inventory."""
        if abs(inventory) < Decimal('100'):  # Small inventory
            return Decimal('0')
        
        # Skew spreads to encourage inventory reduction
        inventory_ratio = abs(inventory) / self.max_inventory_per_symbol
        adjustment = inventory_ratio * self.inventory_penalty_factor * Decimal('0.01')
        
        return adjustment
    
    def _calculate_liquidity_adjustment(self, market_data: Dict[str, Any]) -> Decimal:
        """Calculate spread adjustment based on market liquidity."""
        volume = market_data.get('volume', 1000000)
        
        # Assume lower volume = wider spreads needed
        if volume < 100000:  # Low volume
            return Decimal('0.002')  # +20 bps
        elif volume < 500000:  # Medium volume
            return Decimal('0.001')  # +10 bps
        else:  # High volume
            return Decimal('0')
    
    def _calculate_regime_adjustment(self, market_data: Dict[str, Any]) -> Decimal:
        """Calculate spread adjustment based on market regime."""
        # Simple regime detection based on recent price action
        # In practice, this would use more sophisticated models
        
        current_price = market_data.get('price', Decimal('100'))
        bid_price = market_data.get('bid_price', current_price * Decimal('0.999'))
        ask_price = market_data.get('ask_price', current_price * Decimal('1.001'))
        
        current_spread = (ask_price - bid_price) / current_price
        
        # If market spreads are already wide, increase our spreads too
        if current_spread > Decimal('0.01'):  # > 1%
            return Decimal('0.005')  # +50 bps
        elif current_spread > Decimal('0.005'):  # > 0.5%
            return Decimal('0.002')  # +20 bps
        
        return Decimal('0')
    
    def generate_quotes(self, symbol: str, theoretical_price: Decimal,
                       spread: Decimal, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate bid-ask quotes for market making.
        
        Args:
            symbol: Instrument symbol
            theoretical_price: Fair value price
            spread: Total spread to apply
            market_data: Current market data
            
        Returns:
            Bid-ask quotes with sizes
        """
        try:
            half_spread = spread / 2
            
            # Basic bid-ask calculation
            bid_price = theoretical_price - half_spread
            ask_price = theoretical_price + half_spread
            
            # Inventory skewing
            inventory = self.current_inventory.get(symbol, Decimal('0'))
            if inventory != 0:
                bid_price, ask_price = self._apply_inventory_skew(
                    bid_price, ask_price, inventory, half_spread
                )
            
            # Calculate optimal sizes
            bid_size, ask_size = self._calculate_quote_sizes(symbol, market_data, inventory)
            
            return {
                'symbol': symbol,
                'bid_price': bid_price,
                'ask_price': ask_price,
                'bid_size': bid_size,
                'ask_size': ask_size,
                'mid_price': theoretical_price,
                'spread': spread,
                'spread_bps': float(spread * Decimal('10000')),
                'inventory_skew_applied': inventory != 0,
                'timestamp': datetime.now()
            }
            
        except Exception as e:
            self.logger.error(f"Error generating quotes for {symbol}: {str(e)}")
            return {
                'error': str(e),
                'symbol': symbol
            }
    
    def _apply_inventory_skew(self, bid_price: Decimal, ask_price: Decimal,
                            inventory: Decimal, half_spread: Decimal) -> Tuple[Decimal, Decimal]:
        """Apply inventory skewing to encourage position reduction."""
        skew_factor = Decimal('0.3')  # 30% of half-spread for maximum skew
        
        # Calculate skew based on inventory ratio
        inventory_ratio = inventory / self.max_inventory_per_symbol
        skew_amount = inventory_ratio * skew_factor * half_spread
        
        if inventory > 0:  # Long position - make offer more attractive
            ask_price -= abs(skew_amount)
        elif inventory < 0:  # Short position - make bid more attractive
            bid_price += abs(skew_amount)
        
        return bid_price, ask_price
    
    def _calculate_quote_sizes(self, symbol: str, market_data: Dict[str, Any],
                             inventory: Decimal) -> Tuple[int, int]:
        """Calculate optimal quote sizes based on market conditions and risk."""
        base_size = self.default_quote_size
        
        # Scale based on volatility (lower vol = larger size)
        volatility = market_data.get('volatility', Decimal('0.20'))
        vol_scaling = 1 / (1 + float(volatility))
        
        # Scale based on inventory (larger inventory = smaller quotes in same direction)
        inventory_scaling = 1.0
        if abs(inventory) > self.max_inventory_per_symbol * Decimal('0.5'):
            inventory_scaling = 0.5  # Reduce size if inventory is large
        
        # Apply scaling
        adjusted_size = int(base_size * vol_scaling * inventory_scaling * float(self.size_scaling_factor))
        adjusted_size = max(10, adjusted_size)  # Minimum size of 10
        
        # Inventory-aware sizing
        if inventory > self.max_inventory_per_symbol * Decimal('0.8'):
            # Large long position - reduce bid size, maintain ask size
            bid_size = max(10, adjusted_size // 2)
            ask_size = adjusted_size
        elif inventory < -self.max_inventory_per_symbol * Decimal('0.8'):
            # Large short position - reduce ask size, maintain bid size
            bid_size = adjusted_size
            ask_size = max(10, adjusted_size // 2)
        else:
            bid_size = ask_size = adjusted_size
        
        return bid_size, ask_size
    
    def assess_market_making_opportunity(self, symbol: str, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess the quality of market making opportunity for an instrument.
        
        Args:
            symbol: Instrument symbol
            market_data: Current market data
            
        Returns:
            Opportunity assessment
        """
        try:
            assessment = {
                'symbol': symbol,
                'attractive': False,
                'score': 0.0,
                'factors': {},
                'timestamp': datetime.now()
            }
            
            # Volume factor (higher is better)
            volume = market_data.get('volume', 0)
            volume_score = min(1.0, volume / 1000000)  # Normalize to 1M shares
            assessment['factors']['volume_score'] = volume_score
            
            # Volatility factor (moderate is better)
            volatility = float(market_data.get('volatility', Decimal('0.20')))
            optimal_vol = 0.25  # 25% volatility is optimal for market making
            vol_score = 1.0 - min(1.0, abs(volatility - optimal_vol) / optimal_vol)
            assessment['factors']['volatility_score'] = vol_score
            
            # Spread factor (current spread indicates profitability)
            current_price = market_data.get('price', Decimal('100'))
            bid_price = market_data.get('bid_price', current_price * Decimal('0.999'))
            ask_price = market_data.get('ask_price', current_price * Decimal('1.001'))
            
            current_spread_bps = float((ask_price - bid_price) / current_price * Decimal('10000'))
            spread_score = min(1.0, max(0.0, (current_spread_bps - 5) / 20))  # 5-25 bps range
            assessment['factors']['spread_score'] = spread_score
            
            # Market cap factor (mid-cap is optimal)
            market_cap = market_data.get('market_cap', Decimal('50000000000'))  # $50B default
            if market_cap > Decimal('100000000000'):  # > $100B
                cap_score = 0.7  # Large cap - lower volatility but good liquidity
            elif market_cap > Decimal('10000000000'):  # > $10B
                cap_score = 1.0  # Mid cap - optimal
            elif market_cap > Decimal('1000000000'):  # > $1B
                cap_score = 0.8  # Small cap - higher volatility
            else:
                cap_score = 0.4  # Micro cap - too risky
            
            assessment['factors']['market_cap_score'] = cap_score
            
            # Calculate overall score
            weights = {
                'volume_score': 0.3,
                'volatility_score': 0.25,
                'spread_score': 0.25,
                'market_cap_score': 0.2
            }
            
            total_score = sum(assessment['factors'][factor] * weight 
                            for factor, weight in weights.items())
            
            assessment['score'] = total_score
            assessment['attractive'] = total_score > 0.6  # 60% threshold
            
            return assessment
            
        except Exception as e:
            self.logger.error(f"Error assessing opportunity for {symbol}: {str(e)}")
            return {
                'symbol': symbol,
                'error': str(e),
                'attractive': False,
                'score': 0.0
            }
    
    def update_inventory(self, symbol: str, quantity: Decimal, price: Decimal):
        """Update inventory tracking after a fill."""
        if symbol not in self.current_inventory:
            self.current_inventory[symbol] = Decimal('0')
        
        self.current_inventory[symbol] += quantity
        
        self.logger.debug(f"Inventory update: {symbol} {quantity} @ {price}, "
                         f"new inventory: {self.current_inventory[symbol]}")
    
    def get_inventory_summary(self) -> Dict[str, Any]:
        """Get current inventory summary."""
        total_absolute_inventory = sum(abs(inv) for inv in self.current_inventory.values())
        
        return {
            'positions': {k: float(v) for k, v in self.current_inventory.items()},
            'total_absolute_inventory': float(total_absolute_inventory),
            'max_inventory_per_symbol': float(self.max_inventory_per_symbol),
            'utilization': float(total_absolute_inventory / 
                               (len(self.current_inventory) * self.max_inventory_per_symbol)
                               if self.current_inventory else 0),
            'timestamp': datetime.now().isoformat()
        }
    
    def should_quote(self, symbol: str, market_data: Dict[str, Any]) -> bool:
        """Determine if we should provide quotes for a symbol."""
        # Check inventory limits
        current_inv = self.current_inventory.get(symbol, Decimal('0'))
        if abs(current_inv) > self.max_inventory_per_symbol:
            self.logger.info(f"Skipping quotes for {symbol}: inventory limit exceeded")
            return False
        
        # Check opportunity assessment
        assessment = self.assess_market_making_opportunity(symbol, market_data)
        if not assessment['attractive']:
            self.logger.debug(f"Skipping quotes for {symbol}: opportunity score {assessment['score']:.2f} too low")
            return False
        
        # Check portfolio risk
        if self._calculate_portfolio_risk() > self.max_portfolio_var:
            self.logger.info(f"Skipping quotes for {symbol}: portfolio risk limit exceeded")
            return False
        
        return True
    
    def _calculate_portfolio_risk(self) -> Decimal:
        """Calculate current portfolio risk (simplified VaR)."""
        # Simplified portfolio risk calculation
        total_exposure = sum(abs(inv) for inv in self.current_inventory.values())
        
        # Assume each position has some base risk contribution
        if total_exposure > 0:
            # This is a very simplified risk calculation
            # Real implementation would use proper VaR models
            return total_exposure / (len(self.current_inventory) * self.max_inventory_per_symbol) if self.current_inventory else Decimal('0')
        
        return Decimal('0')
    
    def get_strategy_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for the strategy."""
        return {
            'inventory_summary': self.get_inventory_summary(),
            'portfolio_risk': float(self._calculate_portfolio_risk()),
            'max_portfolio_risk': float(self.max_portfolio_var),
            'active_symbols': len(self.current_inventory),
            'strategy_parameters': {
                'base_spread_bps': self.base_spread_bps,
                'min_spread_bps': self.min_spread_bps,
                'max_spread_bps': self.max_spread_bps,
                'max_inventory_per_symbol': float(self.max_inventory_per_symbol),
                'default_quote_size': self.default_quote_size
            },
            'timestamp': datetime.now().isoformat()
        }