"""
Security class representing a tradeable security.
"""

from datetime import datetime
from typing import Optional
from decimal import Decimal
from dataclasses import dataclass, field

from ..symbol import Symbol, SymbolProperties
from ..enums import SecurityType, Resolution
from ..data_types import BaseData, TradeBar, QuoteBar


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