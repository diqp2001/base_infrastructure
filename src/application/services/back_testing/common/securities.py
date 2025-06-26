"""
Securities, portfolio, and holdings management classes.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any, Iterator
from decimal import Decimal
from dataclasses import dataclass, field

from .symbol import Symbol, SymbolProperties
from .enums import SecurityType, Resolution, OrderDirection
from .data_types import BaseData, TradeBar, QuoteBar


@dataclass
class Security:
    """
    Represents a tradeable security with its properties and current market data.
    """
    symbol: Symbol
    symbol_properties: SymbolProperties
    resolution: Resolution = Resolution.MINUTE
    leverage: Decimal = Decimal('1.0')
    fill_data_forward: bool = True
    extended_market_hours: bool = False
    
    # Market data
    _market_price: Decimal = field(default=Decimal('0.0'), init=False)
    _bid_price: Decimal = field(default=Decimal('0.0'), init=False)
    _ask_price: Decimal = field(default=Decimal('0.0'), init=False)
    _last_data: Optional[BaseData] = field(default=None, init=False)
    _volume: int = field(default=0, init=False)
    
    def __post_init__(self):
        """Post-initialization to ensure proper types."""
        if not isinstance(self.leverage, Decimal):
            self.leverage = Decimal(str(self.leverage))
    
    @property
    def market_price(self) -> Decimal:
        """Current market price of the security."""
        return self._market_price
    
    @property
    def bid_price(self) -> Decimal:
        """Current bid price."""
        return self._bid_price
    
    @property
    def ask_price(self) -> Decimal:
        """Current ask price."""
        return self._ask_price
    
    @property
    def price(self) -> Decimal:
        """Alias for market price."""
        return self.market_price
    
    @property
    def volume(self) -> int:
        """Current volume."""
        return self._volume
    
    @property
    def has_data(self) -> bool:
        """Returns true if the security has received data."""
        return self._market_price > 0
    
    def update_market_price(self, price: Decimal):
        """Update the market price."""
        if not isinstance(price, Decimal):
            price = Decimal(str(price))
        self._market_price = price
    
    def update_data(self, data: BaseData):
        """Update security with new market data."""
        self._last_data = data
        self._market_price = data.price
        
        if isinstance(data, TradeBar):
            self._volume = data.volume
        elif isinstance(data, QuoteBar):
            if data.bid and data.ask:
                self._bid_price = data.bid.close
                self._ask_price = data.ask.close
                self._market_price = (self._bid_price + self._ask_price) / 2
    
    def get_last_data(self) -> Optional[BaseData]:
        """Get the last received data point."""
        return self._last_data
    
    def __str__(self) -> str:
        """String representation of the security."""
        return f"Security({self.symbol}, ${self.market_price})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"Security(symbol={self.symbol}, price=${self.market_price}, "
                f"type={self.symbol.security_type.value})")


class Securities:
    """
    Collection of securities with dictionary-like access.
    Manages all securities in the algorithm.
    """
    
    def __init__(self):
        self._securities: Dict[Symbol, Security] = {}
    
    def add(self, symbol: Symbol, resolution: Resolution = Resolution.MINUTE,
           leverage: Decimal = Decimal('1.0'), fill_data_forward: bool = True,
           extended_market_hours: bool = False) -> Security:
        """Add a security to the collection."""
        from .symbol import get_symbol_cache
        
        # Get symbol properties
        symbol_properties = get_symbol_cache().get_properties(symbol)
        
        # Create security
        security = Security(
            symbol=symbol,
            symbol_properties=symbol_properties,
            resolution=resolution,
            leverage=leverage,
            fill_data_forward=fill_data_forward,
            extended_market_hours=extended_market_hours
        )
        
        self._securities[symbol] = security
        return security
    
    def remove(self, symbol: Symbol) -> bool:
        """Remove a security from the collection."""
        if symbol in self._securities:
            del self._securities[symbol]
            return True
        return False
    
    def contains_key(self, symbol: Symbol) -> bool:
        """Check if the collection contains the specified symbol."""
        return symbol in self._securities
    
    def update_prices(self, data: Dict[Symbol, BaseData]):
        """Update prices for multiple securities."""
        for symbol, market_data in data.items():
            if symbol in self._securities:
                self._securities[symbol].update_data(market_data)
    
    def keys(self) -> List[Symbol]:
        """Get all symbols."""
        return list(self._securities.keys())
    
    def values(self) -> List[Security]:
        """Get all securities."""
        return list(self._securities.values())
    
    def items(self):
        """Get all symbol-security pairs."""
        return self._securities.items()
    
    def __getitem__(self, symbol: Symbol) -> Security:
        """Get security by symbol."""
        return self._securities[symbol]
    
    def __setitem__(self, symbol: Symbol, security: Security):
        """Set security for symbol."""
        self._securities[symbol] = security
    
    def __delitem__(self, symbol: Symbol):
        """Delete security by symbol."""
        del self._securities[symbol]
    
    def __contains__(self, symbol: Symbol) -> bool:
        """Check if symbol is in collection."""
        return symbol in self._securities
    
    def __len__(self) -> int:
        """Get number of securities."""
        return len(self._securities)
    
    def __iter__(self) -> Iterator[Symbol]:
        """Iterate over symbols."""
        return iter(self._securities)


@dataclass
class SecurityHolding:
    """
    Represents a holding of a specific security in the portfolio.
    """
    symbol: Symbol
    quantity: int = 0
    average_price: Decimal = Decimal('0.0')
    market_price: Decimal = Decimal('0.0')
    
    def __post_init__(self):
        """Post-initialization to ensure proper types."""
        if not isinstance(self.average_price, Decimal):
            self.average_price = Decimal(str(self.average_price))
        if not isinstance(self.market_price, Decimal):
            self.market_price = Decimal(str(self.market_price))
    
    @property
    def market_value(self) -> Decimal:
        """Current market value of the holding."""
        return self.market_price * self.quantity
    
    @property
    def cost_basis(self) -> Decimal:
        """Total cost basis of the holding."""
        return self.average_price * abs(self.quantity)
    
    @property
    def unrealized_pnl(self) -> Decimal:
        """Unrealized profit/loss."""
        if self.quantity == 0:
            return Decimal('0.0')
        return (self.market_price - self.average_price) * self.quantity
    
    @property
    def unrealized_pnl_percent(self) -> Decimal:
        """Unrealized profit/loss as percentage."""
        if self.average_price == 0:
            return Decimal('0.0')
        return (self.unrealized_pnl / self.cost_basis) * 100
    
    @property
    def is_long(self) -> bool:
        """Returns true if position is long."""
        return self.quantity > 0
    
    @property
    def is_short(self) -> bool:
        """Returns true if position is short."""
        return self.quantity < 0
    
    @property
    def is_invested(self) -> bool:
        """Returns true if there is a position."""
        return self.quantity != 0
    
    def update_market_price(self, price: Decimal):
        """Update the market price."""
        if not isinstance(price, Decimal):
            price = Decimal(str(price))
        self.market_price = price
    
    def add_shares(self, quantity: int, price: Decimal):
        """Add shares to the holding (for buys) or reduce for sells."""
        if not isinstance(price, Decimal):
            price = Decimal(str(price))
        
        if quantity == 0:
            return
        
        if self.quantity == 0:
            # New position
            self.quantity = quantity
            self.average_price = price
        else:
            # Existing position
            if (self.quantity > 0 and quantity > 0) or (self.quantity < 0 and quantity < 0):
                # Adding to existing position (same direction)
                total_cost = (self.average_price * abs(self.quantity)) + (price * abs(quantity))
                self.quantity += quantity
                if self.quantity != 0:
                    self.average_price = total_cost / abs(self.quantity)
            else:
                # Reducing position or flipping direction
                if abs(quantity) <= abs(self.quantity):
                    # Reducing position
                    self.quantity += quantity
                    if self.quantity == 0:
                        self.average_price = Decimal('0.0')
                else:
                    # Flipping position
                    remaining_quantity = quantity + self.quantity
                    self.quantity = remaining_quantity
                    self.average_price = price
    
    def __str__(self) -> str:
        """String representation of the holding."""
        return f"Holding({self.symbol}, {self.quantity} @ ${self.average_price})"


class SecurityPortfolioManager:
    """
    Manages the portfolio of securities and cash positions.
    """
    
    def __init__(self, cash: Decimal = Decimal('100000.0')):
        if not isinstance(cash, Decimal):
            cash = Decimal(str(cash))
        
        self.cash = cash
        self.total_portfolio_value = cash
        self._holdings: Dict[Symbol, SecurityHolding] = {}
        self._total_fees = Decimal('0.0')
        self._total_trades = 0
        self._winning_trades = 0
        self._losing_trades = 0
    
    def get_holding(self, symbol: Symbol) -> Optional[SecurityHolding]:
        """Get holding for a specific symbol."""
        return self._holdings.get(symbol)
    
    def get_positions(self) -> Dict[Symbol, SecurityHolding]:
        """Get all positions."""
        return {symbol: holding for symbol, holding in self._holdings.items() 
                if holding.is_invested}
    
    def get_all_holdings(self) -> Dict[Symbol, SecurityHolding]:
        """Get all holdings (including zero positions)."""
        return self._holdings.copy()
    
    def update_market_values(self, securities: Securities):
        """Update market values based on current security prices."""
        total_market_value = self.cash
        
        for symbol, holding in self._holdings.items():
            if symbol in securities:
                security = securities[symbol]
                holding.update_market_price(security.market_price)
                total_market_value += holding.market_value
        
        self.total_portfolio_value = total_market_value
    
    def process_fill(self, symbol: Symbol, quantity: int, fill_price: Decimal, 
                    order_fee: Decimal = Decimal('0.0')):
        """Process an order fill and update holdings."""
        if not isinstance(fill_price, Decimal):
            fill_price = Decimal(str(fill_price))
        if not isinstance(order_fee, Decimal):
            order_fee = Decimal(str(order_fee))
        
        # Create holding if it doesn't exist
        if symbol not in self._holdings:
            self._holdings[symbol] = SecurityHolding(symbol=symbol)
        
        # Update holding
        holding = self._holdings[symbol]
        previous_quantity = holding.quantity
        
        holding.add_shares(quantity, fill_price)
        
        # Update cash (subtract cost of purchase plus fees)
        transaction_value = fill_price * quantity  # Positive for buy, negative for sell
        self.cash -= transaction_value + order_fee
        self._total_fees += order_fee
        
        # Track trade statistics
        self._total_trades += 1
        
        # Determine if this was a winning or losing trade (simplified)
        if previous_quantity != 0 and holding.quantity == 0:
            # Position was closed
            if holding.unrealized_pnl > 0:
                self._winning_trades += 1
            else:
                self._losing_trades += 1
    
    def liquidate_position(self, symbol: Symbol, market_price: Decimal) -> int:
        """Liquidate a position and return the quantity that was liquidated."""
        if symbol not in self._holdings:
            return 0
        
        holding = self._holdings[symbol]
        if not holding.is_invested:
            return 0
        
        quantity_to_liquidate = -holding.quantity  # Opposite sign to close position
        self.process_fill(symbol, quantity_to_liquidate, market_price)
        
        return abs(quantity_to_liquidate)
    
    def get_buying_power(self, security: Security) -> Decimal:
        """Get available buying power for a security considering leverage."""
        return self.cash * security.leverage
    
    def get_margin_remaining(self) -> Decimal:
        """Get remaining margin (simplified calculation)."""
        return self.cash  # Simplified - in reality this would consider margin requirements
    
    @property
    def invested_capital(self) -> Decimal:
        """Total capital invested in positions."""
        return sum(abs(holding.cost_basis) for holding in self._holdings.values() 
                  if holding.is_invested)
    
    @property
    def total_unrealized_profit(self) -> Decimal:
        """Total unrealized profit/loss."""
        return sum(holding.unrealized_pnl for holding in self._holdings.values())
    
    @property
    def total_portfolio_margin_used(self) -> Decimal:
        """Total margin used (simplified)."""
        return self.invested_capital  # Simplified calculation
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get portfolio performance statistics."""
        win_rate = (self._winning_trades / max(self._total_trades, 1)) * 100
        
        return {
            'total_portfolio_value': self.total_portfolio_value,
            'cash': self.cash,
            'invested_capital': self.invested_capital,
            'total_unrealized_profit': self.total_unrealized_profit,
            'total_fees': self._total_fees,
            'total_trades': self._total_trades,
            'winning_trades': self._winning_trades,
            'losing_trades': self._losing_trades,
            'win_rate': win_rate,
            'total_return': ((self.total_portfolio_value - Decimal('100000.0')) / Decimal('100000.0')) * 100
        }
    
    def __str__(self) -> str:
        """String representation of the portfolio."""
        num_positions = len(self.get_positions())
        return (f"Portfolio(Value: ${self.total_portfolio_value:,.2f}, "
                f"Cash: ${self.cash:,.2f}, Positions: {num_positions})")


# Alias for backward compatibility
Portfolio = SecurityPortfolioManager