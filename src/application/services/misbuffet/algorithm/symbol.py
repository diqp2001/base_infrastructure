from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from .enums import SecurityType, OptionRight, OptionStyle

# Import domain entities for proper inheritance
from src.domain.entities.finance.back_testing.financial_assets.symbol import Symbol as DomainSymbol
from src.domain.entities.finance.back_testing.financial_assets.symbol import SymbolProperties as DomainSymbolProperties
from src.domain.entities.finance.back_testing.enums import SecurityType as DomainSecurityType, Market


@dataclass(frozen=True)
class Symbol(DomainSymbol):
    """
    Algorithm framework symbol extending domain Symbol with algorithm-specific features.
    Inherits immutable value object properties and adds QuantConnect-style convenience methods.
    """
    # Algorithm-specific fields (in addition to domain fields)
    option_right: Optional[OptionRight] = field(default=None)
    option_style: Optional[OptionStyle] = field(default=None)
    strike_price: Optional[float] = field(default=None)
    expiry: Optional[datetime] = field(default=None)
    properties: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize domain Symbol and validate algorithm-specific fields."""
        # Call parent post_init first
        super().__post_init__()
        
        # Validate algorithm-specific fields
        if self.security_type == SecurityType.OPTION:
            if self.option_right is None:
                raise ValueError("Option symbols must have option_right specified")
            if self.strike_price is None or self.strike_price <= 0:
                raise ValueError("Option symbols must have valid strike_price")
            if self.expiry is None:
                raise ValueError("Option symbols must have expiry date")
    
    @staticmethod
    def _map_security_type(algo_type: SecurityType) -> DomainSecurityType:
        """Map algorithm SecurityType to domain SecurityType."""
        mapping = {
            SecurityType.EQUITY: DomainSecurityType.EQUITY,
            SecurityType.FOREX: DomainSecurityType.FOREX,
            SecurityType.CRYPTO: DomainSecurityType.CRYPTO,
            SecurityType.OPTION: DomainSecurityType.OPTION,
            SecurityType.FUTURE: DomainSecurityType.FUTURE,
        }
        return mapping.get(algo_type, DomainSecurityType.EQUITY)
    
    @staticmethod
    def _map_market(market_str: str) -> Market:
        """Map market string to domain Market enum."""
        market_mapping = {
            "USA": Market.USA,
            "FXCM": Market.FXCM,
            "Binance": Market.BINANCE,
            "Bitfinex": Market.BITFINEX,
        }
        return market_mapping.get(market_str, Market.USA)
    
    @classmethod
    def create(cls, ticker: str, security_type: SecurityType = SecurityType.EQUITY, 
               market: str = "USA", **kwargs) -> 'Symbol':
        """Factory method to create a Symbol"""
        # Map algorithm types to domain types
        domain_security_type = cls._map_security_type(security_type)
        domain_market = cls._map_market(market)
        
        return cls(
            value=ticker.upper(),
            id=kwargs.get('id', ticker),
            security_type=domain_security_type,
            market=domain_market,
            option_right=kwargs.get('option_right'),
            option_style=kwargs.get('option_style'),
            strike_price=kwargs.get('strike_price'),
            expiry=kwargs.get('expiry'),
            properties=kwargs.get('properties', {})
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


@dataclass
class SymbolProperties(DomainSymbolProperties):
    """
    Algorithm framework symbol properties extending domain SymbolProperties.
    Adds algorithm-specific convenience methods and QuantConnect compatibility.
    """
    # Algorithm-specific fields (extending domain properties)
    pip_size: float = field(default=0.0001)
    market_ticker: str = field(default="") 
    description: str = field(default="")
    fee_model: Optional[str] = field(default=None)
    margin_model: Optional[str] = field(default=None)
    
    @classmethod
    def create_for_symbol(cls, symbol: 'Symbol', **kwargs) -> 'SymbolProperties':
        """Create SymbolProperties with domain defaults for a given symbol."""
        # Get domain defaults based on security type
        domain_props = DomainSymbolProperties.get_default(symbol.security_type)
        
        return cls(
            time_zone=kwargs.get('time_zone', domain_props.time_zone),
            exchange_hours=kwargs.get('exchange_hours', domain_props.exchange_hours),
            lot_size=kwargs.get('lot_size', domain_props.lot_size),
            tick_size=kwargs.get('tick_size', domain_props.tick_size),
            minimum_price_variation=kwargs.get('minimum_price_variation', domain_props.minimum_price_variation),
            contract_multiplier=kwargs.get('contract_multiplier', domain_props.contract_multiplier),
            minimum_order_size=kwargs.get('minimum_order_size', domain_props.minimum_order_size),
            maximum_order_size=kwargs.get('maximum_order_size', domain_props.maximum_order_size),
            price_scaling=kwargs.get('price_scaling', domain_props.price_scaling),
            margin_requirement=kwargs.get('margin_requirement', domain_props.margin_requirement),
            short_able=kwargs.get('short_able', domain_props.short_able),
            pip_size=kwargs.get('pip_size', 0.0001),
            market_ticker=kwargs.get('market_ticker', ''),
            description=kwargs.get('description', ''),
            fee_model=kwargs.get('fee_model'),
            margin_model=kwargs.get('margin_model')
        )
    
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