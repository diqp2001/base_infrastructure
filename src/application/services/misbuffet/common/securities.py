"""
Securities and portfolio management classes.
Based on QuantConnect's security architecture.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
from collections import defaultdict

from .symbol import Symbol, SymbolProperties
from .enums import SecurityType, Resolution, OrderDirection
from .data_types import BaseData, TradeBar, QuoteBar


@dataclass
class SecurityHolding:
    """
    Represents a holding of a security in the portfolio.
    """
    symbol: Symbol
    quantity: int = 0
    average_price: float = 0.0
    market_price: float = 0.0
    last_price: float = 0.0
    
    def __post_init__(self):
        if self.market_price == 0.0:
            self.market_price = self.average_price
        if self.last_price == 0.0:
            self.last_price = self.market_price
    
    @property
    def is_long(self) -> bool:
        """Returns True if this is a long position."""
        return self.quantity > 0
    
    @property
    def is_short(self) -> bool:
        """Returns True if this is a short position."""
        return self.quantity < 0
    
    @property
    def is_invested(self) -> bool:
        """Returns True if we have any position in this security."""
        return self.quantity != 0
    
    @property
    def market_value(self) -> float:
        """Returns the market value of this holding."""
        return self.quantity * self.market_price
    
    @property
    def absolute_quantity(self) -> int:
        """Returns the absolute quantity held."""
        return abs(self.quantity)
    
    @property
    def unrealized_profit(self) -> float:
        """Returns the unrealized profit/loss."""
        return self.quantity * (self.market_price - self.average_price)
    
    @property
    def unrealized_profit_percent(self) -> float:
        """Returns the unrealized profit/loss as a percentage."""
        if self.average_price == 0:
            return 0.0
        return (self.market_price - self.average_price) / self.average_price
    
    def update_market_price(self, price: float):
        """Update the market price of this holding."""
        self.last_price = self.market_price
        self.market_price = price
    
    def add_position(self, quantity: int, price: float):
        """Add to the position with the given quantity and price."""
        if self.quantity == 0:
            # New position
            self.quantity = quantity
            self.average_price = price
        else:
            # Adding to existing position
            total_cost = (self.quantity * self.average_price) + (quantity * price)
            total_quantity = self.quantity + quantity
            
            if total_quantity != 0:
                self.average_price = total_cost / total_quantity
                self.quantity = total_quantity
            else:
                # Position closed
                self.quantity = 0
                self.average_price = 0.0


@dataclass 
class Security:
    """
    Represents a tradeable security with market data and properties.
    """
    symbol: Symbol
    properties: SymbolProperties = None
    resolution: Resolution = Resolution.MINUTE
    leverage: float = 1.0
    fill_data_forward: bool = True
    extended_market_hours: bool = False
    
    # Market data
    last_data: Optional[BaseData] = None
    market_price: float = 0.0
    bid_price: float = 0.0
    ask_price: float = 0.0
    volume: int = 0
    
    # Historical tracking
    _price_history: List[float] = field(default_factory=list, init=False)
    _volume_history: List[int] = field(default_factory=list, init=False)
    _last_update: Optional[datetime] = field(default=None, init=False)
    
    def __post_init__(self):
        if self.properties is None:
            self.properties = SymbolProperties.get_default(self.symbol.security_type)
    
    @property
    def price(self) -> float:
        """Returns the current market price."""
        return self.market_price
    
    @property
    def open(self) -> float:
        """Returns the open price if available."""
        if isinstance(self.last_data, TradeBar):
            return self.last_data.open
        return self.market_price
    
    @property
    def high(self) -> float:
        """Returns the high price if available."""
        if isinstance(self.last_data, TradeBar):
            return self.last_data.high
        return self.market_price
    
    @property
    def low(self) -> float:
        """Returns the low price if available."""
        if isinstance(self.last_data, TradeBar):
            return self.last_data.low
        return self.market_price
    
    @property
    def close(self) -> float:
        """Returns the close price if available."""
        if isinstance(self.last_data, TradeBar):
            return self.last_data.close
        return self.market_price
    
    @property
    def has_data(self) -> bool:
        """Returns True if this security has received data."""
        return self.last_data is not None
    
    def update(self, data: BaseData):
        """Update the security with new market data."""
        self.last_data = data
        
        if isinstance(data, TradeBar):
            self.market_price = data.close
            self.volume = data.volume
            self._price_history.append(data.close)
            self._volume_history.append(data.volume)
        elif isinstance(data, QuoteBar):
            self.bid_price = data.bid_close
            self.ask_price = data.ask_close
            self.market_price = data.price  # Mid price
        else:
            self.market_price = data.price
        
        self._last_update = data.time
        
        # Keep history limited to prevent memory issues
        if len(self._price_history) > 1000:
            self._price_history = self._price_history[-500:]
            self._volume_history = self._volume_history[-500:]
    
    def get_last_price(self, lookback: int = 1) -> Optional[float]:
        """Get the price from lookback periods ago."""
        if len(self._price_history) >= lookback:
            return self._price_history[-lookback]
        return None
    
    def get_price_change(self, lookback: int = 1) -> Optional[float]:
        """Get the price change over lookback periods."""
        current = self.market_price
        past = self.get_last_price(lookback + 1)
        if past and current:
            return current - past
        return None
    
    def get_price_change_percent(self, lookback: int = 1) -> Optional[float]:
        """Get the percentage price change over lookback periods."""
        current = self.market_price
        past = self.get_last_price(lookback + 1)
        if past and current and past != 0:
            return (current - past) / past
        return None


class Securities(Dict[Symbol, Security]):
    """
    Collection of securities keyed by symbol.
    """
    
    def __init__(self):
        super().__init__()
        self._symbol_cache: Dict[str, Symbol] = {}
    
    def add(self, symbol: Symbol, resolution: Resolution = Resolution.MINUTE, 
            leverage: float = 1.0, fill_data_forward: bool = True, 
            extended_market_hours: bool = False) -> Security:
        """Add a new security to the collection."""
        security = Security(
            symbol=symbol,
            resolution=resolution,
            leverage=leverage,
            fill_data_forward=fill_data_forward,
            extended_market_hours=extended_market_hours
        )
        
        self[symbol] = security
        self._symbol_cache[symbol.value] = symbol
        
        return security
    
    def remove(self, symbol: Symbol):
        """Remove a security from the collection."""
        if symbol in self:
            del self[symbol]
        if symbol.value in self._symbol_cache:
            del self._symbol_cache[symbol.value]
    
    def get_by_ticker(self, ticker: str) -> Optional[Security]:
        """Get a security by its ticker string."""
        symbol = self._symbol_cache.get(ticker)
        return self.get(symbol) if symbol else None
    
    def update_prices(self, data_dict: Union[Dict[Symbol, BaseData], Dict[str, BaseData]]):
        """Update securities with new price data."""
        for key, data in data_dict.items():
            if isinstance(key, str):
                # Look up symbol by string
                security = self.get_by_ticker(key)
            else:
                security = self.get(key)
            
            if security:
                security.update(data)
    
    def get_symbols(self, security_type: SecurityType = None) -> List[Symbol]:
        """Get all symbols, optionally filtered by security type."""
        if security_type is None:
            return list(self.keys())
        return [symbol for symbol in self.keys() if symbol.security_type == security_type]


class Portfolio:
    """
    Simple portfolio management class.
    """
    
    def __init__(self, cash: float = 100000.0):
        self.cash = Decimal(str(cash))
        self.total_portfolio_value = self.cash
        self._holdings: Dict[Symbol, SecurityHolding] = {}
        self._trades: List[Dict[str, Any]] = []
        
        # Performance tracking
        self._portfolio_value_history: List[float] = []
        self._cash_history: List[float] = []
        self._total_fees: Decimal = Decimal('0')
        self._total_trades: int = 0
    
    def get_holding(self, symbol: Symbol) -> Optional[SecurityHolding]:
        """Get the holding for a symbol."""
        return self._holdings.get(symbol)
    
    def get_positions(self) -> Dict[Symbol, SecurityHolding]:
        """Get all positions."""
        return {symbol: holding for symbol, holding in self._holdings.items() 
                if holding.is_invested}
    
    def add_trade(self, symbol: Symbol, quantity: int, price: float, 
                  commission: float = 0.0, time: datetime = None):
        """Add a trade to the portfolio."""
        time = time or datetime.now()
        
        # Get or create holding
        if symbol not in self._holdings:
            self._holdings[symbol] = SecurityHolding(symbol=symbol)
        
        holding = self._holdings[symbol]
        
        # Calculate trade value
        trade_value = Decimal(str(abs(quantity) * price))
        commission_decimal = Decimal(str(commission))
        
        # Update holding
        holding.add_position(quantity, price)
        
        # Update cash (subtract for buys, add for sells, subtract commission)
        if quantity > 0:  # Buy
            self.cash -= trade_value + commission_decimal
        else:  # Sell
            self.cash += trade_value - commission_decimal
        
        # Track trade
        trade_record = {
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'value': float(trade_value),
            'commission': commission,
            'time': time,
            'direction': 'BUY' if quantity > 0 else 'SELL'
        }
        self._trades.append(trade_record)
        
        # Update statistics
        self._total_fees += commission_decimal
        self._total_trades += 1
    
    def update_market_values(self, securities: Securities):
        """Update market values of holdings based on current security prices."""
        total_holdings_value = Decimal('0')
        
        for symbol, holding in self._holdings.items():
            security = securities.get(symbol)
            if security and security.has_data:
                holding.update_market_price(security.market_price)
                total_holdings_value += Decimal(str(holding.market_value))
        
        self.total_portfolio_value = self.cash + total_holdings_value
        
        # Track history
        self._portfolio_value_history.append(float(self.total_portfolio_value))
        self._cash_history.append(float(self.cash))
    
    @property
    def total_unrealized_profit(self) -> float:
        """Get total unrealized profit across all holdings."""
        return sum(holding.unrealized_profit for holding in self._holdings.values()
                  if holding.is_invested)
    
    @property
    def total_holdings_value(self) -> float:
        """Get total market value of all holdings."""
        return sum(holding.market_value for holding in self._holdings.values()
                  if holding.is_invested)
    
    @property
    def invested_capital(self) -> float:
        """Get the amount of capital currently invested."""
        return sum(abs(holding.quantity * holding.average_price) 
                  for holding in self._holdings.values() if holding.is_invested)
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get portfolio performance statistics."""
        if not self._trades:
            return {
                'total_portfolio_value': float(self.total_portfolio_value),
                'total_trades': 0,
                'win_rate': 0.0,
                'total_fees': float(self._total_fees)
            }
        
        # Calculate win rate (simplified - based on profitable vs unprofitable positions)
        profitable_positions = sum(1 for holding in self._holdings.values() 
                                 if holding.is_invested and holding.unrealized_profit > 0)
        total_positions = sum(1 for holding in self._holdings.values() if holding.is_invested)
        win_rate = profitable_positions / max(total_positions, 1)
        
        return {
            'total_portfolio_value': float(self.total_portfolio_value),
            'cash': float(self.cash),
            'total_holdings_value': self.total_holdings_value,
            'total_unrealized_profit': self.total_unrealized_profit,
            'invested_capital': self.invested_capital,
            'total_trades': self._total_trades,
            'win_rate': win_rate,
            'total_fees': float(self._total_fees),
            'total_positions': total_positions,
            'profitable_positions': profitable_positions
        }