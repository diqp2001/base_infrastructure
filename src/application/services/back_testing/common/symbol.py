"""
Symbol and symbol-related classes for security identification.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any
from decimal import Decimal

from .enums import SecurityType, Market, OptionRight, OptionStyle


@dataclass(frozen=True)
class Symbol:
    """
    Immutable symbol identifier for securities.
    Represents a unique identifier for any tradeable security.
    """
    value: str
    id: str
    security_type: SecurityType = SecurityType.EQUITY
    market: Market = Market.USA
    
    def __str__(self) -> str:
        """String representation of the symbol."""
        return self.value
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"Symbol({self.value}, {self.security_type.value}, {self.market.value})"
    
    def __hash__(self) -> int:
        """Hash implementation for use in dictionaries and sets."""
        return hash((self.value, self.security_type, self.market))
    
    def __eq__(self, other) -> bool:
        """Equality comparison."""
        if not isinstance(other, Symbol):
            return False
        return (self.value == other.value and 
                self.security_type == other.security_type and 
                self.market == other.market)
    
    @classmethod
    def create_equity(cls, ticker: str, market: str = "USA") -> 'Symbol':
        """Create an equity symbol."""
        market_enum = Market(market.lower()) if isinstance(market, str) else market
        return cls(
            value=ticker.upper(),
            id=f"{ticker.upper()}-{market_enum.value.upper()}",
            security_type=SecurityType.EQUITY,
            market=market_enum
        )
    
    @classmethod
    def create_forex(cls, pair: str, market: str = "FXCM") -> 'Symbol':
        """Create a forex symbol."""
        market_enum = Market(market.lower()) if isinstance(market, str) else market
        return cls(
            value=pair.upper(),
            id=f"{pair.upper()}-{market_enum.value.upper()}",
            security_type=SecurityType.FOREX,
            market=market_enum
        )
    
    @classmethod
    def create_crypto(cls, pair: str, market: str = "Binance") -> 'Symbol':
        """Create a cryptocurrency symbol."""
        market_enum = Market(market.lower()) if isinstance(market, str) else market
        return cls(
            value=pair.upper(),
            id=f"{pair.upper()}-{market_enum.value.upper()}",
            security_type=SecurityType.CRYPTO,
            market=market_enum
        )
    
    @classmethod
    def create_option(cls, underlying: str, market: str, strike_price: Decimal,
                     option_right: OptionRight, expiry: datetime) -> 'Symbol':
        """Create an option symbol."""
        market_enum = Market(market.lower()) if isinstance(market, str) else market
        expiry_str = expiry.strftime("%Y%m%d")
        strike_str = f"{int(strike_price * 1000):08d}"
        right_str = "C" if option_right == OptionRight.CALL else "P"
        
        value = f"{underlying.upper()} {expiry_str}{right_str}{strike_str}"
        option_id = f"{underlying.upper()}-{expiry_str}-{right_str}-{strike_str}-{market_enum.value.upper()}"
        
        return cls(
            value=value,
            id=option_id,
            security_type=SecurityType.OPTION,
            market=market_enum
        )
    
    @classmethod
    def create_future(cls, symbol: str, market: str, expiry: datetime) -> 'Symbol':
        """Create a futures symbol."""
        market_enum = Market(market.lower()) if isinstance(market, str) else market
        expiry_str = expiry.strftime("%Y%m")
        
        value = f"{symbol.upper()}{expiry_str}"
        future_id = f"{symbol.upper()}-{expiry_str}-{market_enum.value.upper()}"
        
        return cls(
            value=value,
            id=future_id,
            security_type=SecurityType.FUTURE,
            market=market_enum
        )
    
    @property
    def is_canonical(self) -> bool:
        """Returns true if this is a canonical symbol (no mapping required)."""
        return True  # Simplified for now
    
    @property
    def has_underlying(self) -> bool:
        """Returns true if this symbol has an underlying symbol."""
        return self.security_type in [SecurityType.OPTION, SecurityType.FUTURE]


@dataclass
class SymbolProperties:
    """
    Properties and characteristics of a symbol.
    Contains metadata about a symbol's trading characteristics.
    """
    time_zone: str
    exchange_hours: Dict[str, Any]
    lot_size: Decimal = Decimal('1.0')
    tick_size: Decimal = Decimal('0.01')
    minimum_price_variation: Decimal = Decimal('0.01')
    contract_multiplier: Decimal = Decimal('1.0')
    pip_size: Decimal = Decimal('0.0001')
    strike_multiplier: Decimal = Decimal('100.0')
    minimum_order_size: Decimal = Decimal('1.0')
    maximum_order_size: Optional[Decimal] = None
    description: str = ""
    
    def __post_init__(self):
        """Post-initialization to ensure proper types."""
        fields_to_convert = [
            'lot_size', 'tick_size', 'minimum_price_variation', 
            'contract_multiplier', 'pip_size', 'strike_multiplier',
            'minimum_order_size'
        ]
        
        for field in fields_to_convert:
            value = getattr(self, field)
            if not isinstance(value, Decimal):
                setattr(self, field, Decimal(str(value)))
        
        if self.maximum_order_size is not None and not isinstance(self.maximum_order_size, Decimal):
            self.maximum_order_size = Decimal(str(self.maximum_order_size))
    
    @classmethod
    def get_default(cls, security_type: SecurityType, market: Market) -> 'SymbolProperties':
        """Get default symbol properties for a security type and market."""
        
        # Default exchange hours (simplified)
        default_hours = {
            "market_open": "09:30:00",
            "market_close": "16:00:00",
            "time_zone": "America/New_York"
        }
        
        if security_type == SecurityType.EQUITY:
            return cls(
                time_zone="America/New_York",
                exchange_hours=default_hours,
                lot_size=Decimal('1.0'),
                tick_size=Decimal('0.01'),
                minimum_price_variation=Decimal('0.01'),
                contract_multiplier=Decimal('1.0'),
                description="Equity security"
            )
        
        elif security_type == SecurityType.FOREX:
            return cls(
                time_zone="UTC",
                exchange_hours={"24_hour": True},
                lot_size=Decimal('100000.0'),  # Standard lot
                tick_size=Decimal('0.00001'),  # 0.1 pip
                minimum_price_variation=Decimal('0.00001'),
                contract_multiplier=Decimal('100000.0'),
                pip_size=Decimal('0.0001'),
                description="Forex pair"
            )
        
        elif security_type == SecurityType.CRYPTO:
            return cls(
                time_zone="UTC",
                exchange_hours={"24_hour": True},
                lot_size=Decimal('1.0'),
                tick_size=Decimal('0.00000001'),  # 1 satoshi for BTC pairs
                minimum_price_variation=Decimal('0.00000001'),
                contract_multiplier=Decimal('1.0'),
                description="Cryptocurrency"
            )
        
        elif security_type == SecurityType.OPTION:
            return cls(
                time_zone="America/New_York",
                exchange_hours=default_hours,
                lot_size=Decimal('1.0'),
                tick_size=Decimal('0.01'),
                minimum_price_variation=Decimal('0.01'),
                contract_multiplier=Decimal('100.0'),  # Options typically control 100 shares
                strike_multiplier=Decimal('100.0'),
                description="Options contract"
            )
        
        elif security_type == SecurityType.FUTURE:
            return cls(
                time_zone="America/Chicago",
                exchange_hours=default_hours,
                lot_size=Decimal('1.0'),
                tick_size=Decimal('0.25'),  # Common for many futures
                minimum_price_variation=Decimal('0.25'),
                contract_multiplier=Decimal('50.0'),  # Varies by contract
                description="Futures contract"
            )
        
        else:
            # Default fallback
            return cls(
                time_zone="UTC",
                exchange_hours=default_hours,
                lot_size=Decimal('1.0'),
                tick_size=Decimal('0.01'),
                minimum_price_variation=Decimal('0.01'),
                contract_multiplier=Decimal('1.0'),
                description="Generic security"
            )


class SymbolCache:
    """
    Cache for symbols to avoid recreating the same symbols repeatedly.
    Provides efficient symbol lookup and creation.
    """
    
    def __init__(self):
        self._cache: Dict[str, Symbol] = {}
        self._properties_cache: Dict[Symbol, SymbolProperties] = {}
    
    def get_symbol(self, value: str, security_type: SecurityType = SecurityType.EQUITY,
                  market: Market = Market.USA) -> Symbol:
        """Get or create a symbol with caching."""
        key = f"{value}_{security_type.value}_{market.value}"
        
        if key not in self._cache:
            self._cache[key] = Symbol(
                value=value,
                id=f"{value}-{market.value.upper()}",
                security_type=security_type,
                market=market
            )
        
        return self._cache[key]
    
    def get_properties(self, symbol: Symbol) -> SymbolProperties:
        """Get symbol properties with caching."""
        if symbol not in self._properties_cache:
            self._properties_cache[symbol] = SymbolProperties.get_default(
                symbol.security_type, symbol.market
            )
        
        return self._properties_cache[symbol]
    
    def clear(self) -> None:
        """Clear the symbol cache."""
        self._cache.clear()
        self._properties_cache.clear()
    
    def size(self) -> int:
        """Get the number of cached symbols."""
        return len(self._cache)


# Global symbol cache instance
_symbol_cache = SymbolCache()


def get_symbol_cache() -> SymbolCache:
    """Get the global symbol cache instance."""
    return _symbol_cache