"""
Symbol system for the backtesting framework.
Based on QuantConnect's symbol architecture.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, Optional, Any
from .enums import SecurityType, Market


@dataclass(frozen=True)
class Symbol:
    """Immutable symbol representation."""
    value: str
    id: str = field(default_factory=lambda: "")
    security_type: SecurityType = SecurityType.BASE
    market: Market = Market.USA
    
    def __post_init__(self):
        """Validate symbol data."""
        if not self.value:
            raise ValueError("Symbol value cannot be empty")
        
        # Set default ID if not provided
        if not self.id:
            object.__setattr__(self, 'id', f"{self.value}_{self.security_type.value}_{self.market.value}")
    
    @classmethod
    def create_equity(cls, ticker: str, market: Market = Market.USA) -> 'Symbol':
        """Create an equity symbol."""
        return cls(
            value=ticker.upper(),
            security_type=SecurityType.EQUITY,
            market=market
        )
    
    @classmethod
    def create_forex(cls, base_currency: str, quote_currency: str) -> 'Symbol':
        """Create a forex symbol."""
        value = f"{base_currency.upper()}{quote_currency.upper()}"
        return cls(
            value=value,
            security_type=SecurityType.FOREX,
            market=Market.FXCM
        )
    
    @classmethod
    def create_crypto(cls, base_currency: str, quote_currency: str, market: Market = Market.BINANCE) -> 'Symbol':
        """Create a cryptocurrency symbol."""
        value = f"{base_currency.upper()}{quote_currency.upper()}"
        return cls(
            value=value,
            security_type=SecurityType.CRYPTO,
            market=market
        )
    
    @classmethod
    def create_option(cls, underlying: str, expiry: datetime, strike: Decimal, 
                     option_right: str, market: Market = Market.USA) -> 'Symbol':
        """Create an option symbol."""
        expiry_str = expiry.strftime("%Y%m%d")
        strike_str = str(int(strike * 1000)).zfill(8)  # Strike in thousandths
        value = f"{underlying.upper()} {expiry_str}{option_right[0]}{strike_str}"
        return cls(
            value=value,
            security_type=SecurityType.OPTION,
            market=market
        )
    
    @classmethod
    def create_future(cls, root: str, expiry: datetime, market: Market = Market.USA) -> 'Symbol':
        """Create a future symbol."""
        # Common future month codes
        month_codes = {1: 'F', 2: 'G', 3: 'H', 4: 'J', 5: 'K', 6: 'M',
                      7: 'N', 8: 'Q', 9: 'U', 10: 'V', 11: 'X', 12: 'Z'}
        month_code = month_codes.get(expiry.month, 'F')
        year_code = str(expiry.year)[-1]
        value = f"{root.upper()}{month_code}{year_code}"
        return cls(
            value=value,
            security_type=SecurityType.FUTURE,
            market=market
        )
    
    def __str__(self) -> str:
        return self.value
    
    def __repr__(self) -> str:
        return f"Symbol('{self.value}', {self.security_type.value}, {self.market.value})"


@dataclass
class SymbolProperties:
    """Properties associated with a symbol."""
    time_zone: str = "America/New_York"
    exchange_hours: Optional[Dict[str, Any]] = None
    lot_size: int = 1
    tick_size: Decimal = field(default_factory=lambda: Decimal('0.01'))
    minimum_price_variation: Decimal = field(default_factory=lambda: Decimal('0.01'))
    contract_multiplier: int = 1
    minimum_order_size: int = 1
    maximum_order_size: Optional[int] = None
    price_scaling: Decimal = field(default_factory=lambda: Decimal('1'))
    margin_requirement: Decimal = field(default_factory=lambda: Decimal('0.25'))
    short_able: bool = True
    
    def __post_init__(self):
        """Ensure decimal precision for financial fields."""
        self.tick_size = Decimal(str(self.tick_size))
        self.minimum_price_variation = Decimal(str(self.minimum_price_variation))
        self.price_scaling = Decimal(str(self.price_scaling))
        self.margin_requirement = Decimal(str(self.margin_requirement))
    
    @classmethod
    def get_default(cls, security_type: SecurityType) -> 'SymbolProperties':
        """Get default properties for a security type."""
        if security_type == SecurityType.EQUITY:
            return cls(
                lot_size=100,
                tick_size=Decimal('0.01'),
                margin_requirement=Decimal('0.25'),
                short_able=True
            )
        elif security_type == SecurityType.FOREX:
            return cls(
                lot_size=100000,  # Standard forex lot
                tick_size=Decimal('0.00001'),  # 1 pip for most pairs
                contract_multiplier=100000,
                margin_requirement=Decimal('0.02'),  # 2% for forex
                time_zone="UTC"
            )
        elif security_type == SecurityType.CRYPTO:
            return cls(
                lot_size=1,
                tick_size=Decimal('0.01'),
                contract_multiplier=1,
                margin_requirement=Decimal('1.0'),  # No leverage by default
                time_zone="UTC",
                short_able=False  # Many crypto exchanges don't allow shorting
            )
        elif security_type == SecurityType.FUTURE:
            return cls(
                lot_size=1,
                tick_size=Decimal('0.25'),  # Common for index futures
                contract_multiplier=50,  # E.g., ES contract
                margin_requirement=Decimal('0.05'),  # 5% for futures
                short_able=True
            )
        elif security_type == SecurityType.OPTION:
            return cls(
                lot_size=100,  # Options typically represent 100 shares
                tick_size=Decimal('0.01'),
                contract_multiplier=100,
                margin_requirement=Decimal('0.20'),  # 20% for covered options
                short_able=True
            )
        else:
            return cls()  # Default properties