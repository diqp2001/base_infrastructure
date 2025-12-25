"""
Market Making Algorithm for Misbuffet Framework

QCAlgorithm implementation for derivatives market making across
multiple asset classes (equity, fixed income, commodity).
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal

try:
    # Misbuffet/QuantConnect framework imports
    from src.application.services.misbuffet.common.interfaces import IAlgorithm
    from src.application.services.misbuffet.common.enums import Resolution
    from src.application.services.misbuffet.backtesting.algorithm import QCAlgorithm
    from src.application.services.misbuffet.tools.optimization.portfolio.blacklitterman import BlackLittermanOptimizer
except ImportError as e:
    logging.warning(f"Misbuffet framework imports not available: {e}")
    # Define placeholder base class
    class QCAlgorithm:
        def __init__(self):
            pass
        def initialize(self):
            pass
        def on_data(self, data):
            pass


class MarketMakingAlgorithm(QCAlgorithm):
    """
    Market making algorithm that implements:
    - Multi-asset derivatives pricing
    - Dynamic bid-ask spread management
    - Inventory-aware quote generation
    - Risk management and position limits
    """
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)
        
        # Dependencies (injected externally)
        self.data_loader = None
        self.pricing_engine = None
        self.market_making_strategy = None
        
        # Configuration
        self.universe = []
        self.asset_classes = ['equity']
        self.initial_capital = Decimal('1000000')
        
        # Runtime state
        self.current_prices = {}
        self.active_quotes = {}
        self.inventory = {}
        self.pnl_tracker = {}
        
        # Performance tracking
        self.trades_made = 0
        self.total_spread_captured = Decimal('0')
        self.inventory_turnover = Decimal('0')
        
        self.logger.info("MarketMakingAlgorithm initialized")
    
    def set_data_loader(self, data_loader):
        """Inject data loader dependency."""
        self.data_loader = data_loader
        self.logger.info("Data loader set")
    
    def set_pricing_engine(self, pricing_engine):
        """Inject pricing engine dependency."""
        self.pricing_engine = pricing_engine
        self.logger.info("Pricing engine set")
    
    def set_market_making_strategy(self, strategy):
        """Inject market making strategy dependency."""
        self.market_making_strategy = strategy
        self.logger.info("Market making strategy set")
    
    def set_universe(self, universe: List[str]):
        """Set the trading universe."""
        self.universe = universe
        # Initialize inventory tracking
        for symbol in universe:
            self.inventory[symbol] = Decimal('0')
            self.pnl_tracker[symbol] = Decimal('0')
        self.logger.info(f"Universe set: {len(universe)} instruments")
    
    def initialize(self):
        """
        Initialize the algorithm - called by Misbuffet framework.
        """
        try:
            self.logger.info("🚀 Initializing MarketMakingAlgorithm...")
            
            # Set initial capital
            if hasattr(self, 'set_cash'):
                self.set_cash(float(self.initial_capital))
            
            # Add securities to universe
            for symbol in self.universe:
                if hasattr(self, 'add_equity'):
                    self.add_equity(symbol, Resolution.MINUTE)
                self.logger.info(f"Added {symbol} to universe")
            
            # Set algorithm parameters
            if hasattr(self, 'set_benchmark'):
                self.set_benchmark('SPY')
            
            # Initialize market making parameters
            self.initialize_market_making_parameters()
            
            self.logger.info("✅ MarketMakingAlgorithm initialization complete")
            
        except Exception as e:
            self.logger.error(f"❌ Error during initialization: {str(e)}")
            raise
    
    def initialize_market_making_parameters(self):
        """Initialize market making specific parameters."""
        # Spread parameters
        self.min_spread_bps = 5
        self.max_spread_bps = 50
        self.target_spread_bps = 15
        
        # Inventory parameters
        self.max_inventory_per_symbol = Decimal('10000')  # Max position size
        self.inventory_penalty_factor = Decimal('0.1')
        
        # Risk parameters
        self.max_portfolio_var = Decimal('0.05')  # 5% portfolio VaR limit
        self.stop_loss_threshold = Decimal('0.02')  # 2% stop loss
        
        # Quote parameters
        self.default_quote_size = 100
        self.quote_update_frequency = 60  # seconds
        
        self.logger.info("Market making parameters initialized")
    
    def on_data(self, data):
        """
        Main algorithm logic - called on each data update.
        
        Args:
            data: Market data from Misbuffet framework
        """
        try:
            if not data:
                return
            
            # Update current market data
            self.update_market_data(data)
            
            # Generate pricing for all instruments
            self.update_pricing()
            
            # Generate quotes based on current prices and inventory
            self.generate_quotes()
            
            # Execute market making strategy
            self.execute_market_making_logic()
            
            # Update performance tracking
            self.update_performance_metrics()
            
        except Exception as e:
            self.logger.error(f"❌ Error in on_data: {str(e)}")
    
    def update_market_data(self, data):
        """Update internal market data structures."""
        try:
            for symbol in self.universe:
                if hasattr(data, 'get') and symbol in data:
                    market_price = data[symbol]
                    self.current_prices[symbol] = {
                        'price': market_price,
                        'timestamp': datetime.now(),
                        'bid': getattr(market_price, 'bid_price', market_price * 0.999),
                        'ask': getattr(market_price, 'ask_price', market_price * 1.001),
                        'volume': getattr(market_price, 'volume', 1000)
                    }
        except Exception as e:
            self.logger.error(f"Error updating market data: {str(e)}")
    
    def update_pricing(self):
        """Update pricing using derivatives pricing engine."""
        if not self.pricing_engine:
            return
        
        try:
            for symbol in self.universe:
                if symbol in self.current_prices:
                    market_data = self.current_prices[symbol]
                    
                    # Price using appropriate model
                    pricing_result = self.pricing_engine.price_instrument(symbol, market_data)
                    
                    if pricing_result.get('success'):
                        # Update pricing information
                        self.current_prices[symbol].update({
                            'theoretical_price': pricing_result.get('mid_price'),
                            'volatility': pricing_result.get('volatility'),
                            'greeks': pricing_result.get('greeks', {}),
                            'model_used': pricing_result.get('model_used')
                        })
        except Exception as e:
            self.logger.error(f"Error updating pricing: {str(e)}")
    
    def generate_quotes(self):
        """Generate bid-ask quotes for market making."""
        try:
            for symbol in self.universe:
                if symbol in self.current_prices:
                    price_data = self.current_prices[symbol]
                    
                    # Calculate theoretical mid price
                    theoretical_mid = price_data.get('theoretical_price', price_data['price'])
                    
                    # Calculate spread based on volatility and inventory
                    spread = self.calculate_dynamic_spread(symbol, price_data)
                    
                    # Generate quotes with inventory adjustment
                    quotes = self.calculate_inventory_adjusted_quotes(symbol, theoretical_mid, spread)
                    
                    self.active_quotes[symbol] = quotes
                    
        except Exception as e:
            self.logger.error(f"Error generating quotes: {str(e)}")
    
    def calculate_dynamic_spread(self, symbol: str, price_data: Dict) -> Decimal:
        """Calculate dynamic spread based on volatility and market conditions."""
        base_spread = Decimal(str(self.target_spread_bps)) / Decimal('10000')
        
        # Adjust for volatility
        volatility = price_data.get('volatility', Decimal('0.20'))
        volatility_adjustment = volatility * Decimal('0.5')
        
        # Adjust for inventory
        current_inventory = self.inventory.get(symbol, Decimal('0'))
        inventory_adjustment = abs(current_inventory) * self.inventory_penalty_factor / self.max_inventory_per_symbol
        
        # Calculate final spread
        dynamic_spread = base_spread + volatility_adjustment + inventory_adjustment
        
        # Apply min/max bounds
        min_spread = Decimal(str(self.min_spread_bps)) / Decimal('10000')
        max_spread = Decimal(str(self.max_spread_bps)) / Decimal('10000')
        
        return max(min_spread, min(max_spread, dynamic_spread))
    
    def calculate_inventory_adjusted_quotes(self, symbol: str, mid_price: Decimal, spread: Decimal) -> Dict[str, Any]:
        """Calculate quotes adjusted for current inventory position."""
        half_spread = spread / 2
        
        # Base bid/ask
        bid_price = mid_price - half_spread
        ask_price = mid_price + half_spread
        
        # Inventory adjustment - skew quotes to reduce inventory
        current_inventory = self.inventory.get(symbol, Decimal('0'))
        
        if current_inventory > 0:  # Long inventory - make offer more attractive
            ask_price -= half_spread * Decimal('0.2')
            bid_price -= half_spread * Decimal('0.1')
        elif current_inventory < 0:  # Short inventory - make bid more attractive
            bid_price += half_spread * Decimal('0.2')
            ask_price += half_spread * Decimal('0.1')
        
        return {
            'bid_price': bid_price,
            'ask_price': ask_price,
            'bid_size': self.default_quote_size,
            'ask_size': self.default_quote_size,
            'mid_price': mid_price,
            'spread': spread,
            'timestamp': datetime.now()
        }
    
    def execute_market_making_logic(self):
        """Execute core market making logic - place and manage orders."""
        try:
            for symbol in self.universe:
                if symbol in self.active_quotes:
                    quotes = self.active_quotes[symbol]
                    
                    # Check if we should place new quotes
                    if self.should_place_quotes(symbol):
                        self.place_market_making_orders(symbol, quotes)
                    
                    # Manage existing positions
                    self.manage_inventory(symbol)
                    
        except Exception as e:
            self.logger.error(f"Error in market making logic: {str(e)}")
    
    def should_place_quotes(self, symbol: str) -> bool:
        """Determine if we should place new quotes for a symbol."""
        # Check risk limits
        if abs(self.inventory.get(symbol, Decimal('0'))) > self.max_inventory_per_symbol:
            return False
        
        # Check portfolio VaR
        if self.calculate_portfolio_var() > self.max_portfolio_var:
            return False
        
        return True
    
    def place_market_making_orders(self, symbol: str, quotes: Dict[str, Any]):
        """Place market making orders."""
        try:
            # In a real implementation, this would place actual orders
            # For simulation, we'll track theoretical trades
            
            bid_price = float(quotes['bid_price'])
            ask_price = float(quotes['ask_price'])
            size = quotes['bid_size']
            
            # Simulate order placement
            if hasattr(self, 'limit_order'):
                # Place bid order
                self.limit_order(symbol, -size, bid_price)  # Negative for buy
                # Place ask order  
                self.limit_order(symbol, size, ask_price)   # Positive for sell
            
            self.logger.debug(f"Placed quotes for {symbol}: Bid {bid_price:.4f} Ask {ask_price:.4f}")
            
        except Exception as e:
            self.logger.error(f"Error placing orders for {symbol}: {str(e)}")
    
    def manage_inventory(self, symbol: str):
        """Manage inventory positions to stay within limits."""
        current_inventory = self.inventory.get(symbol, Decimal('0'))
        
        # If inventory is too large, place aggressive orders to reduce it
        if abs(current_inventory) > self.max_inventory_per_symbol * Decimal('0.8'):
            self.place_inventory_reduction_orders(symbol, current_inventory)
    
    def place_inventory_reduction_orders(self, symbol: str, inventory: Decimal):
        """Place orders to reduce inventory exposure."""
        if symbol not in self.current_prices:
            return
        
        current_price = self.current_prices[symbol]['price']
        
        # Determine order direction and size
        if inventory > 0:  # Long position - need to sell
            order_size = min(inventory, Decimal(str(self.default_quote_size * 2)))
            order_price = current_price * Decimal('0.999')  # Slightly below market
            
            if hasattr(self, 'limit_order'):
                self.limit_order(symbol, float(order_size), float(order_price))
        
        elif inventory < 0:  # Short position - need to buy
            order_size = min(abs(inventory), Decimal(str(self.default_quote_size * 2)))
            order_price = current_price * Decimal('1.001')  # Slightly above market
            
            if hasattr(self, 'limit_order'):
                self.limit_order(symbol, -float(order_size), float(order_price))
    
    def calculate_portfolio_var(self) -> Decimal:
        """Calculate portfolio Value at Risk."""
        # Simplified VaR calculation
        total_exposure = sum(abs(pos) for pos in self.inventory.values())
        portfolio_value = self.initial_capital  # Simplified
        
        if portfolio_value > 0:
            return total_exposure / portfolio_value
        return Decimal('0')
    
    def update_performance_metrics(self):
        """Update performance tracking metrics."""
        # Track spreads captured
        total_inventory = sum(abs(pos) for pos in self.inventory.values())
        if total_inventory > 0:
            self.inventory_turnover = self.trades_made / float(total_inventory)
        
        # Update PnL tracking would go here in a real implementation
    
    def on_order_event(self, order_event):
        """Handle order fill events."""
        try:
            if hasattr(order_event, 'fill_quantity') and order_event.fill_quantity != 0:
                symbol = order_event.symbol
                fill_quantity = Decimal(str(order_event.fill_quantity))
                fill_price = Decimal(str(order_event.fill_price))
                
                # Update inventory
                if symbol in self.inventory:
                    self.inventory[symbol] += fill_quantity
                else:
                    self.inventory[symbol] = fill_quantity
                
                # Update trade count
                self.trades_made += 1
                
                # Calculate spread captured (simplified)
                if symbol in self.active_quotes:
                    quotes = self.active_quotes[symbol]
                    mid_price = quotes.get('mid_price', fill_price)
                    spread_captured = abs(fill_price - mid_price)
                    self.total_spread_captured += spread_captured
                
                self.logger.info(f"Fill: {symbol} {fill_quantity} @ {fill_price}")
                
        except Exception as e:
            self.logger.error(f"Error handling order event: {str(e)}")
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary for reporting."""
        return {
            'trades_made': self.trades_made,
            'total_spread_captured': float(self.total_spread_captured),
            'inventory_turnover': float(self.inventory_turnover),
            'current_inventory': {k: float(v) for k, v in self.inventory.items()},
            'portfolio_var': float(self.calculate_portfolio_var()),
            'active_quotes_count': len(self.active_quotes)
        }