"""
Base Security domain entity following QuantConnect Lean architecture.
Provides common functionality for all tradeable securities.
"""
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum
from dataclasses import dataclass

from .financial_asset import FinancialAsset


class SecurityType(Enum):
    """Enumeration for different security types."""
    EQUITY = "EQUITY"
    BOND = "BOND"
    OPTION = "OPTION"
    FUTURE = "FUTURE"
    FOREX = "FOREX"
    CRYPTO = "CRYPTO"
    COMMODITY = "COMMODITY"


@dataclass(frozen=True)
class Symbol:
    """Value object representing a security symbol."""
    ticker: str
    security_id: str
    exchange: str
    
    def __str__(self) -> str:
        return f"{self.ticker}"


@dataclass(frozen=True)
class MarketData:
    """Value object for market data snapshot."""
    price: Decimal
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    volume: Optional[int] = None
    timestamp: Optional[datetime] = None


class Security(FinancialAsset, ABC):
    """
    Base domain entity for all tradeable securities.
    Follows QuantConnect Lean architecture pattern.
    """
    
    def __init__(self, 
                 id: int,
                 symbol: Symbol,
                 security_type: SecurityType,
                 start_date: datetime,
                 end_date: Optional[datetime] = None,
                 leverage: Decimal = Decimal('1.0'),
                 is_tradeable: bool = True):
        """
        Initialize a Security entity.
        
        Args:
            id: Unique identifier for the security
            symbol: Symbol information (ticker, exchange, etc.)
            security_type: Type of security (EQUITY, BOND, etc.)
            start_date: Date when security data starts
            end_date: Date when security data ends (optional)
            leverage: Leverage multiplier for trading
            is_tradeable: Whether security can be traded
        """
        super().__init__(id, start_date, end_date)
        self.symbol = symbol
        self.security_type = security_type
        self.leverage = leverage
        self.is_tradeable = is_tradeable
        
        # Market data
        self._current_market_data: Optional[MarketData] = None
        
        # Trading properties
        self._last_price: Optional[Decimal] = None
        self._price_change_percent: Optional[Decimal] = None
    
    @property
    def asset_type(self) -> str:
        """Return the security type as string."""
        return self.security_type.value
    
    @property
    def ticker(self) -> str:
        """Return the ticker symbol."""
        return self.symbol.ticker
    
    @property
    def current_price(self) -> Optional[Decimal]:
        """Get current price from market data."""
        return self._current_market_data.price if self._current_market_data else None
    
    @property
    def current_market_data(self) -> Optional[MarketData]:
        """Get current market data snapshot."""
        return self._current_market_data
    
    def update_market_data(self, market_data: MarketData) -> None:
        """
        Update market data with validation and price change calculation.
        Template method that can be overridden by subclasses.
        """
        self._validate_market_data(market_data)
        self._calculate_price_change(market_data.price)
        self._apply_market_data_update(market_data)
        self._notify_price_change()
    
    def _validate_market_data(self, market_data: MarketData) -> None:
        """Validate market data before applying update."""
        if market_data.price <= 0:
            raise ValueError(f"Invalid price {market_data.price} for {self.ticker}")
        
        # Security-specific validation can be overridden
        self._validate_security_specific_data(market_data)
    
    @abstractmethod
    def _validate_security_specific_data(self, market_data: MarketData) -> None:
        """Override in subclasses for security-specific validation."""
        pass
    
    def _calculate_price_change(self, new_price: Decimal) -> None:
        """Calculate price change percentage."""
        if self._last_price is not None and self._last_price > 0:
            change = (new_price - self._last_price) / self._last_price
            self._price_change_percent = change * 100
        else:
            self._price_change_percent = Decimal('0')
    
    def _apply_market_data_update(self, market_data: MarketData) -> None:
        """Apply the market data update."""
        self._last_price = self._current_market_data.price if self._current_market_data else None
        self._current_market_data = market_data
    
    def _notify_price_change(self) -> None:
        """Notify observers of price change - can be extended for domain events."""
        # This could publish domain events in a full implementation
        pass
    
    def get_effective_leverage(self) -> Decimal:
        """Get effective leverage for position sizing."""
        return self.leverage if self.is_tradeable else Decimal('0')
    
    def is_valid_for_trading(self) -> bool:
        """Check if security is valid for trading."""
        return (self.is_tradeable and 
                self.current_price is not None and 
                self.current_price > 0)
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}({self.ticker})>"