from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from .enums import SecurityType, OptionRight, OptionStyle


@dataclass(frozen=True)
class Symbol:
    """
    Represents a unique identifier for a security in the algorithm framework.
    Symbols are immutable value objects that uniquely identify financial instruments.
    """
    value: str
    id: str = field(default="")
    security_type: SecurityType = SecurityType.EQUITY
    market: str = field(default="")
    
    # Option-specific fields
    option_right: Optional[OptionRight] = None
    option_style: Optional[OptionStyle] = None
    strike_price: Optional[float] = None
    expiry: Optional[datetime] = None
    
    # Additional properties
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # If ID is not provided, use the value as ID
        if not self.id:
            object.__setattr__(self, 'id', self.value)
    
    @classmethod
    def create(cls, ticker: str, security_type: SecurityType = SecurityType.EQUITY, 
               market: str = "", **kwargs) -> 'Symbol':
        """Factory method to create a Symbol"""
        return cls(
            value=ticker,
            id=ticker,
            security_type=security_type,
            market=market,
            **kwargs
        )
    
    @classmethod
    def create_equity(cls, ticker: str, market: str = "USA") -> 'Symbol':
        """Factory method to create an equity symbol"""
        return cls.create(ticker, SecurityType.EQUITY, market)
    
    @classmethod
    def create_forex(cls, ticker: str, market: str = "FXCM") -> 'Symbol':
        """Factory method to create a forex symbol"""
        return cls.create(ticker, SecurityType.FOREX, market)
    
    @classmethod
    def create_crypto(cls, ticker: str, market: str = "Bitfinex") -> 'Symbol':
        """Factory method to create a crypto symbol"""
        return cls.create(ticker, SecurityType.CRYPTO, market)
    
    @classmethod
    def create_option(cls, underlying: str, expiry: datetime, strike: float, 
                     right: OptionRight, style: OptionStyle = OptionStyle.AMERICAN,
                     market: str = "USA") -> 'Symbol':
        """Factory method to create an option symbol"""
        option_id = f"{underlying}_{expiry.strftime('%Y%m%d')}_{right.value}_{strike}"
        return cls.create(
            option_id,
            SecurityType.OPTION,
            market,
            option_right=right,
            option_style=style,
            strike_price=strike,
            expiry=expiry
        )
    
    @property
    def ticker(self) -> str:
        """Returns the ticker symbol"""
        return self.value
    
    @property
    def is_option(self) -> bool:
        """Returns True if this is an option symbol"""
        return self.security_type == SecurityType.OPTION
    
    @property
    def is_equity(self) -> bool:
        """Returns True if this is an equity symbol"""
        return self.security_type == SecurityType.EQUITY
    
    @property
    def is_forex(self) -> bool:
        """Returns True if this is a forex symbol"""
        return self.security_type == SecurityType.FOREX
    
    @property
    def is_crypto(self) -> bool:
        """Returns True if this is a crypto symbol"""
        return self.security_type == SecurityType.CRYPTO
    
    def __str__(self) -> str:
        return self.value
    
    def __repr__(self) -> str:
        return f"Symbol({self.value}, {self.security_type.value})"
    
    def __hash__(self) -> int:
        return hash((self.id, self.security_type))


@dataclass(frozen=True)
class SymbolProperties:
    """
    Contains properties specific to a symbol that affect how it trades.
    """
    symbol: Symbol
    lot_size: int = 1
    tick_size: float = 0.01
    minimum_price_variation: float = 0.01
    contract_multiplier: int = 1
    pip_size: float = 0.0001
    market_ticker: str = ""
    description: str = ""
    
    # Trading hours and market properties
    time_zone: str = "America/New_York"
    exchange_hours: Dict[str, Any] = field(default_factory=dict)
    
    # Fee and margin properties
    fee_model: Optional[str] = None
    margin_model: Optional[str] = None
    
    @property
    def is_tradable(self) -> bool:
        """Returns True if the security can be traded"""
        return self.lot_size > 0
    
    def get_minimum_order_size(self) -> int:
        """Returns the minimum order size"""
        return self.lot_size
    
    def round_price_to_tick_size(self, price: float) -> float:
        """Rounds a price to the nearest tick size"""
        if self.tick_size <= 0:
            return price
        return round(price / self.tick_size) * self.tick_size