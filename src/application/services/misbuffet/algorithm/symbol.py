from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
from .enums import SecurityType, OptionRight, OptionStyle

# Import domain entities for proper inheritance
from domain.entities.finance.back_testing.symbol import Symbol as DomainSymbol
from domain.entities.finance.back_testing.symbol import SymbolProperties as DomainSymbolProperties
from domain.entities.finance.back_testing.enums import SecurityType as DomainSecurityType, Market


@dataclass(frozen=True)
class Symbol(DomainSymbol):
    """
    Algorithm framework symbol extending domain Symbol with algorithm-specific features.
    Inherits immutable value object properties and adds QuantConnect-style convenience methods.
    """
    # Algorithm-specific fields (in addition to domain fields)
    option_right: Optional[OptionRight] = field(default=None, init=False)
    option_style: Optional[OptionStyle] = field(default=None, init=False)
    strike_price: Optional[float] = field(default=None, init=False)
    expiry: Optional[datetime] = field(default=None, init=False)
    properties: Dict[str, Any] = field(default_factory=dict, init=False)
    
    def __new__(cls, value: str, security_type: SecurityType = SecurityType.EQUITY, 
                market: str = "USA", **kwargs):
        """Create new Symbol instance with domain model compatibility."""
        # Map algorithm security types to domain security types
        domain_security_type = cls._map_security_type(security_type)
        domain_market = cls._map_market(market)
        
        # Create domain symbol instance
        instance = super().__new__(cls, value=value, 
                                  security_type=domain_security_type, 
                                  market=domain_market)
        
        # Store algorithm-specific fields
        if 'option_right' in kwargs:
            object.__setattr__(instance, 'option_right', kwargs['option_right'])
        if 'option_style' in kwargs:
            object.__setattr__(instance, 'option_style', kwargs['option_style'])
        if 'strike_price' in kwargs:
            object.__setattr__(instance, 'strike_price', kwargs['strike_price'])
        if 'expiry' in kwargs:
            object.__setattr__(instance, 'expiry', kwargs['expiry'])
        if 'properties' in kwargs:
            object.__setattr__(instance, 'properties', kwargs['properties'])
        
        return instance
    
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
class SymbolProperties(DomainSymbolProperties):
    """
    Algorithm framework symbol properties extending domain SymbolProperties.
    Adds algorithm-specific convenience methods and QuantConnect compatibility.
    """
    # Algorithm-specific fields (extending domain properties)
    pip_size: float = field(default=0.0001, init=False)
    market_ticker: str = field(default="", init=False) 
    description: str = field(default="", init=False)
    fee_model: Optional[str] = field(default=None, init=False)
    margin_model: Optional[str] = field(default=None, init=False)
    
    def __new__(cls, symbol=None, **kwargs):
        """Create SymbolProperties with domain model compatibility."""
        # Use domain defaults if symbol provided
        if symbol and hasattr(symbol, 'security_type'):
            domain_props = DomainSymbolProperties.get_default(symbol.security_type)
            instance = super().__new__(cls,
                                      time_zone=domain_props.time_zone,
                                      exchange_hours=domain_props.exchange_hours,
                                      lot_size=domain_props.lot_size,
                                      tick_size=domain_props.tick_size,
                                      minimum_price_variation=domain_props.minimum_price_variation,
                                      contract_multiplier=domain_props.contract_multiplier,
                                      minimum_order_size=domain_props.minimum_order_size,
                                      maximum_order_size=domain_props.maximum_order_size,
                                      price_scaling=domain_props.price_scaling,
                                      margin_requirement=domain_props.margin_requirement,
                                      short_able=domain_props.short_able)
        else:
            # Use provided values or defaults
            instance = super().__new__(cls,
                                      time_zone=kwargs.get('time_zone', 'America/New_York'),
                                      exchange_hours=kwargs.get('exchange_hours'),
                                      lot_size=kwargs.get('lot_size', 1),
                                      tick_size=kwargs.get('tick_size', float(0.01)),
                                      minimum_price_variation=kwargs.get('minimum_price_variation', float(0.01)),
                                      contract_multiplier=kwargs.get('contract_multiplier', 1),
                                      minimum_order_size=kwargs.get('minimum_order_size', 1),
                                      maximum_order_size=kwargs.get('maximum_order_size'),
                                      price_scaling=kwargs.get('price_scaling', float(1)),
                                      margin_requirement=kwargs.get('margin_requirement', float(0.25)),
                                      short_able=kwargs.get('short_able', True))
        
        # Set algorithm-specific fields
        object.__setattr__(instance, 'pip_size', kwargs.get('pip_size', 0.0001))
        object.__setattr__(instance, 'market_ticker', kwargs.get('market_ticker', ''))
        object.__setattr__(instance, 'description', kwargs.get('description', ''))
        object.__setattr__(instance, 'fee_model', kwargs.get('fee_model'))
        object.__setattr__(instance, 'margin_model', kwargs.get('margin_model'))
        
        return instance
    
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