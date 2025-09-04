from abc import ABC, abstractmethod
from decimal import Decimal
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field

@dataclass
class Symbol:
    """Value object for security symbols following QuantConnect patterns"""
    ticker: str
    exchange: str
    security_type: str
    market: str = "USA"
    
    def __post_init__(self):
        if not self.ticker or not self.exchange:
            raise ValueError("Ticker and exchange are required")
    
    def __str__(self):
        return f"{self.ticker}.{self.exchange}"

@dataclass
class MarketData:
    """Value object for market data updates"""
    price: Decimal
    volume: int = 0
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if self.price < 0:
            raise ValueError("Price cannot be negative")
        if self.volume < 0:
            raise ValueError("Volume cannot be negative")

@dataclass
class Dividend:
    """Value object for dividend information"""
    amount: Decimal
    ex_date: datetime
    pay_date: Optional[datetime] = None
    record_date: Optional[datetime] = None
    
    def __post_init__(self):
        if self.amount < 0:
            raise ValueError("Dividend amount cannot be negative")

@dataclass 
class StockSplit:
    """Value object for stock split information"""
    split_factor: Decimal  # e.g., 2.0 for 2:1 split
    ex_date: datetime
    
    def __post_init__(self):
        if self.split_factor <= 0:
            raise ValueError("Split factor must be positive")

class Security(ABC):
    """
    Base Security class following QuantConnect patterns with market data management.
    Pure domain entity - no SQLAlchemy dependencies.
    """
    
    def __init__(self, symbol: Symbol, security_id: Optional[int] = None):
        self._symbol = symbol
        self._security_id = security_id
        self._current_price = Decimal('0.0')
        self._market_data: Optional[MarketData] = None
        self._last_update = datetime.now()
        self._is_tradeable = True
        self._leverage = Decimal('1.0')
        self._price_history: List[MarketData] = []
        
    @property
    def symbol(self) -> Symbol:
        return self._symbol
    
    @property
    def security_id(self) -> Optional[int]:
        return self._security_id
        
    @property
    def current_price(self) -> Decimal:
        return self._current_price
    
    @property
    def last_update(self) -> datetime:
        return self._last_update
    
    @property
    def is_tradeable(self) -> bool:
        return self._is_tradeable
    
    @property
    def leverage(self) -> Decimal:
        return self._leverage
    
    def set_leverage(self, leverage: Decimal) -> None:
        """Set leverage for this security"""
        if leverage <= 0:
            raise ValueError("Leverage must be positive")
        self._leverage = leverage
    
    def update_market_data(self, market_data: MarketData) -> None:
        """
        Template method for updating market data.
        Base implementation handles common logic, derived classes can override.
        """
        # Validation (circuit breaker pattern)
        if self._current_price > 0:
            price_change = abs(market_data.price - self._current_price) / self._current_price
            if price_change > Decimal('0.50'):  # 50% price change circuit breaker
                raise ValueError(f"Suspicious price change: {price_change:.2%}")
        
        # Update core data
        self._current_price = market_data.price
        self._market_data = market_data
        self._last_update = market_data.timestamp
        
        # Store in history (keep last 1000 updates)
        self._price_history.append(market_data)
        if len(self._price_history) > 1000:
            self._price_history.pop(0)
        
        # Allow derived classes to handle specific updates
        self._on_price_update(market_data)
    
    @abstractmethod
    def _on_price_update(self, market_data: MarketData) -> None:
        """Hook for derived classes to handle price updates"""
        pass
    
    @abstractmethod  
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """Calculate margin requirement for a given quantity"""
        pass
    
    @property
    @abstractmethod
    def security_type(self) -> str:
        """Return the security type (e.g., 'EQUITY', 'OPTION', etc.)"""
        pass
    
    def get_price_history(self, count: int = 10) -> List[MarketData]:
        """Get recent price history"""
        return self._price_history[-count:] if self._price_history else []
    
    def __str__(self):
        return f"{self.security_type}({self._symbol})"
    
    def __repr__(self):
        return f"{self.__class__.__name__}(symbol={self._symbol}, price={self._current_price})"