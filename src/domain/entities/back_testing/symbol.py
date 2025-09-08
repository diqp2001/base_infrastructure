"""
Domain entities for symbol system.
Pure domain entities following DDD principles.
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


class SymbolCache:
    """Caches symbols to avoid recreation and improve performance."""
    
    def __init__(self):
        self._symbol_cache: Dict[str, Symbol] = {}
        self._properties_cache: Dict[Symbol, SymbolProperties] = {}
    
    def get_symbol(self, value: str, security_type: SecurityType = SecurityType.EQUITY, 
                   market: Market = Market.USA) -> Symbol:
        """Get or create a symbol from cache."""
        cache_key = f"{value}_{security_type.value}_{market.value}"
        
        if cache_key not in self._symbol_cache:
            self._symbol_cache[cache_key] = Symbol(
                value=value,
                security_type=security_type,
                market=market
            )
        
        return self._symbol_cache[cache_key]
    
    def get_properties(self, symbol: Symbol) -> SymbolProperties:
        """Get or create symbol properties from cache."""
        if symbol not in self._properties_cache:
            self._properties_cache[symbol] = SymbolProperties.get_default(symbol.security_type)
        
        return self._properties_cache[symbol]
    
    def set_properties(self, symbol: Symbol, properties: SymbolProperties):
        """Set custom properties for a symbol."""
        self._properties_cache[symbol] = properties
    
    def clear(self):
        """Clear all cached data."""
        self._symbol_cache.clear()
        self._properties_cache.clear()
    
    def size(self) -> int:
        """Get the number of cached symbols."""
        return len(self._symbol_cache)


@dataclass
class SymbolMapping:
    """Maps symbols between different data providers."""
    original_symbol: Symbol
    mapped_symbol: Symbol
    data_provider: str
    mapping_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def is_active(self, current_time: datetime = None) -> bool:
        """Check if this mapping is currently active."""
        current_time = current_time or datetime.now(timezone.utc)
        return current_time >= self.mapping_date


@dataclass
class SymbolSecurityDatabase:
    """Database of symbol security information."""
    symbols: Dict[str, Symbol] = field(default_factory=dict)
    properties: Dict[Symbol, SymbolProperties] = field(default_factory=dict)
    mappings: Dict[str, List[SymbolMapping]] = field(default_factory=dict)
    
    def add_symbol(self, symbol: Symbol, properties: SymbolProperties = None):
        """Add a symbol to the database."""
        self.symbols[symbol.value] = symbol
        if properties:
            self.properties[symbol] = properties
        else:
            self.properties[symbol] = SymbolProperties.get_default(symbol.security_type)
    
    def get_symbol(self, value: str) -> Optional[Symbol]:
        """Get a symbol by its value."""
        return self.symbols.get(value)
    
    def get_properties(self, symbol: Symbol) -> Optional[SymbolProperties]:
        """Get properties for a symbol."""
        return self.properties.get(symbol)
    
    def add_mapping(self, mapping: SymbolMapping):
        """Add a symbol mapping."""
        original_value = mapping.original_symbol.value
        if original_value not in self.mappings:
            self.mappings[original_value] = []
        self.mappings[original_value].append(mapping)
    
    def get_mappings(self, symbol_value: str) -> List[SymbolMapping]:
        """Get all mappings for a symbol."""
        return self.mappings.get(symbol_value, [])