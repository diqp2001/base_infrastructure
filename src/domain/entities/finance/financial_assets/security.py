"""
Security base class following QuantConnect Lean architecture patterns.
Provides template method pattern and common functionality for all tradeable securities.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from enum import Enum


class SecurityType(Enum):
    """Types of financial securities."""
    EQUITY = "equity"
    SHARE = "share"
    FOREX = "forex" 
    CRYPTO = "crypto"
    OPTION = "option"
    FUTURE = "future"
    BOND = "bond"
    INDEX = "index"
    COMMODITY = "commodity"
    DERIVATIVE = "derivative"
    SWAP = "swap"
    FORWARD = "forward"


@dataclass
class Symbol:
    """Value object representing a trading symbol."""
    ticker: str
    exchange: str
    security_type: SecurityType
    
    def __str__(self) -> str:
        return f"{self.ticker}.{self.exchange}"


@dataclass 
class MarketData:
    """Value object for market data updates."""
    timestamp: datetime
    price: Decimal
    volume: Optional[int] = None
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    
    def __post_init__(self):
        """Validate market data on creation."""
        if self.price < 0:
            raise ValueError("Price cannot be negative")
        if self.volume is not None and self.volume < 0:
            raise ValueError("Volume cannot be negative")


@dataclass
class Holdings:
    """Value object representing position holdings."""
    quantity: Decimal
    average_cost: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    
    @property
    def total_fees(self) -> Decimal:
        """Calculate total fees paid."""
        return abs(self.quantity) * self.average_cost * Decimal('0.001')  # 0.1% fee


class Security(ABC):
    """
    Base class for all tradeable securities following QuantConnect architecture.
    Implements template method pattern for market data processing.
    """
    
    def __init__(self, symbol: Symbol):
        self._symbol = symbol
        self._price = Decimal('0')
        self._holdings = Holdings(Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0'))
        self._last_update: Optional[datetime] = None
        self._market_data_cache: Dict[str, Any] = {}
        self._price_history: List[MarketData] = []
        self._is_tradeable = True
        
    @property
    def symbol(self) -> Symbol:
        """Get the security symbol."""
        return self._symbol
    
    @property
    def security_type(self) -> SecurityType:
        """Get the security type."""
        return self._symbol.security_type
    
    @property
    def price(self) -> Decimal:
        """Get current market price."""
        return self._price
    
    @property
    def holdings(self) -> Holdings:
        """Get current holdings."""
        return self._holdings
    
    @property
    def last_update(self) -> Optional[datetime]:
        """Get timestamp of last market data update."""
        return self._last_update
    
    @property
    def is_tradeable(self) -> bool:
        """Whether security can be traded."""
        return self._is_tradeable
    
    def update_market_data(self, data: MarketData) -> None:
        """
        Template method for updating market data.
        Defines the algorithm flow while allowing customization.
        """
        # Validate data first
        if not self._validate_market_data(data):
            return
            
        # Pre-processing hook
        self._pre_process_data(data)
        
        # Core price update logic  
        self._update_price(data)
        
        # Post-processing hook
        self._post_process_data(data)
        
        # Update timestamp and cache
        self._last_update = data.timestamp
        self._market_data_cache['last_data'] = data
        self._price_history.append(data)
        
        # Keep only last 100 price points for memory efficiency
        if len(self._price_history) > 100:
            self._price_history = self._price_history[-100:]
    
    def _validate_market_data(self, data: MarketData) -> bool:
        """Validate incoming market data."""
        if data.price <= 0:
            print(f"Invalid price {data.price} for {self.symbol}")
            return False
        
        # Circuit breaker - reject price changes > 50%
        if self._price > 0:
            price_change = abs(data.price - self._price) / self._price
            if price_change > Decimal('0.5'):
                print(f"Circuit breaker triggered for {self.symbol}: {price_change:.2%} change")
                return False
        
        return True
    
    def _pre_process_data(self, data: MarketData) -> None:
        """Hook method for pre-processing - can be overridden by subclasses."""
        pass
    
    def _update_price(self, data: MarketData) -> None:
        """Core price update logic - common to all securities."""
        old_price = self._price
        self._price = data.price
        
        # Update market value of holdings
        if self._holdings.quantity != 0:
            self._holdings = Holdings(
                quantity=self._holdings.quantity,
                average_cost=self._holdings.average_cost,
                market_value=self._holdings.quantity * data.price,
                unrealized_pnl=(data.price - self._holdings.average_cost) * self._holdings.quantity
            )
    
    def _post_process_data(self, data: MarketData) -> None:
        """Hook method for post-processing - can be overridden by subclasses.""" 
        pass
    
    def get_market_data_history(self, lookback_periods: int = 10) -> List[MarketData]:
        """Get recent market data history."""
        return self._price_history[-lookback_periods:]
    
    def calculate_volatility(self, periods: int = 20) -> Decimal:
        """Calculate historical volatility from recent price data."""
        if len(self._price_history) < periods:
            return Decimal('0')
            
        recent_prices = [data.price for data in self._price_history[-periods:]]
        if len(recent_prices) < 2:
            return Decimal('0')
        
        # Simple volatility calculation (standard deviation of returns)
        returns = []
        for i in range(1, len(recent_prices)):
            ret = (recent_prices[i] - recent_prices[i-1]) / recent_prices[i-1]
            returns.append(ret)
        
        if not returns:
            return Decimal('0')
            
        # Calculate standard deviation
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
        volatility = variance ** Decimal('0.5')
        
        return volatility * Decimal('100')  # Convert to percentage
    
    @abstractmethod
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """Calculate margin requirement for a given position size."""
        pass
    
    @abstractmethod  
    def get_contract_multiplier(self) -> Decimal:
        """Get the contract multiplier for the security."""
        pass
    
    def update_holdings(self, quantity: Decimal, average_cost: Decimal) -> None:
        """Update position holdings."""
        market_value = quantity * self._price
        unrealized_pnl = (self._price - average_cost) * quantity
        
        self._holdings = Holdings(
            quantity=quantity,
            average_cost=average_cost, 
            market_value=market_value,
            unrealized_pnl=unrealized_pnl
        )
    
    def __str__(self) -> str:
        return f"Security({self.symbol}, ${self.price})"
    
    def __repr__(self) -> str:
        return (f"Security(symbol={self.symbol}, price={self.price}, "
                f"holdings={self.holdings.quantity})")