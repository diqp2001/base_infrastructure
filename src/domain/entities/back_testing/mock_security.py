"""
Mock Security domain entity for backtesting operations.
Provides simplified security functionality for test scenarios.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Dict, Any
from .symbol import Symbol
from .enums import SecurityType


@dataclass
class MockMarketData:
    """Value object for mock market data updates."""
    timestamp: datetime
    price: Decimal
    volume: Optional[int] = None
    bid: Optional[Decimal] = None
    ask: Optional[Decimal] = None
    high: Optional[Decimal] = None
    low: Optional[Decimal] = None
    open: Optional[Decimal] = None
    close: Optional[Decimal] = None
    
    def __post_init__(self):
        """Validate market data on creation."""
        if self.price <= 0:
            raise ValueError("Price must be positive")
        if self.volume is not None and self.volume < 0:
            raise ValueError("Volume cannot be negative")


@dataclass
class MockSecurityHoldings:
    """Value object representing security holdings in portfolio."""
    quantity: Decimal
    average_cost: Decimal
    market_value: Decimal
    unrealized_pnl: Decimal
    realized_pnl: Decimal = Decimal('0')
    
    @property
    def total_fees(self) -> Decimal:
        """Calculate estimated fees for position."""
        return abs(self.quantity) * self.average_cost * Decimal('0.001')  # 0.1% fee
    
    @property
    def holdings_cost(self) -> Decimal:
        """Calculate total cost of holdings."""
        return self.quantity * self.average_cost


class MockSecurity:
    """
    Mock security implementation for backtesting.
    Simulates security behavior with simplified market data processing.
    """
    
    def __init__(self, symbol: Symbol, initial_price: Decimal = Decimal('100')):
        self._symbol = symbol
        self._price = initial_price
        self._last_update: Optional[datetime] = None
        self._price_history: List[MockMarketData] = []
        self._is_tradeable = True
        self._is_delisted = False
        
        # Holdings information (for portfolio context)
        self._holdings = MockSecurityHoldings(
            quantity=Decimal('0'),
            average_cost=Decimal('0'),
            market_value=Decimal('0'),
            unrealized_pnl=Decimal('0')
        )
        
        # Market data cache
        self._market_data_cache: Dict[str, Any] = {
            'bid': None,
            'ask': None,
            'volume': 0,
            'high': initial_price,
            'low': initial_price,
            'open': initial_price,
            'close': initial_price
        }
        
        # Performance tracking
        self._daily_high = initial_price
        self._daily_low = initial_price
        self._volatility_cache: Optional[Decimal] = None
    
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
    def holdings(self) -> MockSecurityHoldings:
        """Get current holdings."""
        return self._holdings
    
    @property
    def holdings_value(self) -> Decimal:
        """Get market value of current holdings."""
        return self._holdings.market_value
    
    @property
    def last_update(self) -> Optional[datetime]:
        """Get timestamp of last market data update."""
        return self._last_update
    
    @property
    def is_tradeable(self) -> bool:
        """Whether security can be traded."""
        return self._is_tradeable and not self._is_delisted
    
    @property
    def is_delisted(self) -> bool:
        """Whether security has been delisted."""
        return self._is_delisted
    
    @property
    def bid(self) -> Optional[Decimal]:
        """Get current bid price."""
        return self._market_data_cache.get('bid')
    
    @property
    def ask(self) -> Optional[Decimal]:
        """Get current ask price."""
        return self._market_data_cache.get('ask')
    
    @property
    def volume(self) -> int:
        """Get current volume."""
        return self._market_data_cache.get('volume', 0)
    
    @property
    def high(self) -> Decimal:
        """Get daily high."""
        return self._daily_high
    
    @property
    def low(self) -> Decimal:
        """Get daily low."""
        return self._daily_low
    
    @property
    def open(self) -> Decimal:
        """Get opening price."""
        return self._market_data_cache.get('open', self._price)
    
    @property
    def close(self) -> Decimal:
        """Get closing price."""
        return self._market_data_cache.get('close', self._price)
    
    def update_market_data(self, data: MockMarketData) -> None:
        """Update security with new market data."""
        if not self._validate_market_data(data):
            return
        
        # Update price and timestamp
        old_price = self._price
        self._price = data.price
        self._last_update = data.timestamp
        
        # Update daily high/low
        if data.price > self._daily_high:
            self._daily_high = data.price
        if data.price < self._daily_low:
            self._daily_low = data.price
        
        # Update market data cache
        self._market_data_cache.update({
            'bid': data.bid,
            'ask': data.ask,
            'volume': data.volume or 0,
            'high': data.high or self._daily_high,
            'low': data.low or self._daily_low,
            'open': data.open or self._market_data_cache.get('open', data.price),
            'close': data.close or data.price
        })
        
        # Store in price history
        self._price_history.append(data)
        
        # Keep only last 252 trading days for memory efficiency
        if len(self._price_history) > 252:
            self._price_history = self._price_history[-252:]
        
        # Update holdings market value if we have positions
        if self._holdings.quantity != 0:
            self._update_holdings_value()
        
        # Clear volatility cache as prices have changed
        self._volatility_cache = None
    
    def _validate_market_data(self, data: MockMarketData) -> bool:
        """Validate incoming market data."""
        if data.price <= 0:
            return False
        
        # Simple circuit breaker - reject price changes > 50% in backtesting
        if self._price > 0:
            price_change = abs(data.price - self._price) / self._price
            if price_change > Decimal('0.5'):
                return False
        
        return True
    
    def _update_holdings_value(self) -> None:
        """Update holdings market value and unrealized PnL."""
        market_value = self._holdings.quantity * self._price
        unrealized_pnl = (self._price - self._holdings.average_cost) * self._holdings.quantity
        
        self._holdings = MockSecurityHoldings(
            quantity=self._holdings.quantity,
            average_cost=self._holdings.average_cost,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=self._holdings.realized_pnl
        )
    
    def update_holdings(self, quantity: Decimal, average_cost: Decimal) -> None:
        """Update position holdings for this security."""
        market_value = quantity * self._price
        unrealized_pnl = (self._price - average_cost) * quantity
        
        self._holdings = MockSecurityHoldings(
            quantity=quantity,
            average_cost=average_cost,
            market_value=market_value,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=self._holdings.realized_pnl
        )
    
    def realize_pnl(self, pnl: Decimal) -> None:
        """Add to realized PnL (e.g., when closing positions)."""
        self._holdings = MockSecurityHoldings(
            quantity=self._holdings.quantity,
            average_cost=self._holdings.average_cost,
            market_value=self._holdings.market_value,
            unrealized_pnl=self._holdings.unrealized_pnl,
            realized_pnl=self._holdings.realized_pnl + pnl
        )
    
    def get_price_history(self, lookback_periods: int = 20) -> List[MockMarketData]:
        """Get recent price history."""
        return self._price_history[-lookback_periods:] if self._price_history else []
    
    def calculate_volatility(self, periods: int = 20) -> Decimal:
        """Calculate historical volatility from recent price data."""
        if self._volatility_cache is not None and len(self._price_history) >= periods:
            return self._volatility_cache
        
        if len(self._price_history) < periods:
            return Decimal('0')
        
        recent_prices = [data.price for data in self._price_history[-periods:]]
        if len(recent_prices) < 2:
            return Decimal('0')
        
        # Calculate standard deviation of returns
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
        
        # Cache the result
        self._volatility_cache = volatility * Decimal('100')  # Convert to percentage
        return self._volatility_cache
    
    def get_return(self, periods: int = 1) -> Decimal:
        """Calculate return over specified periods."""
        if len(self._price_history) < periods + 1:
            return Decimal('0')
        
        current_price = self._price_history[-1].price
        past_price = self._price_history[-(periods + 1)].price
        
        return (current_price - past_price) / past_price
    
    def reset_daily_data(self) -> None:
        """Reset daily tracking data (high/low)."""
        self._daily_high = self._price
        self._daily_low = self._price
        
        # Update open price for new day
        self._market_data_cache['open'] = self._price
    
    def delist(self) -> None:
        """Mark security as delisted."""
        self._is_delisted = True
        self._is_tradeable = False
    
    def suspend_trading(self) -> None:
        """Temporarily suspend trading."""
        self._is_tradeable = False
    
    def resume_trading(self) -> None:
        """Resume trading if not delisted."""
        if not self._is_delisted:
            self._is_tradeable = True
    
    def get_contract_multiplier(self) -> Decimal:
        """Get contract multiplier (simplified for stocks)."""
        return Decimal('1')
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """Calculate margin requirement (simplified - 50% for stocks)."""
        if self._symbol.security_type == SecurityType.EQUITY:
            return abs(quantity) * self._price * Decimal('0.5')
        return Decimal('0')  # No margin for other types in this mock
    
    def __str__(self) -> str:
        return f"MockSecurity({self._symbol.ticker}, ${self._price})"
    
    def __repr__(self) -> str:
        return (f"MockSecurity(symbol={self._symbol.ticker}, price={self._price}, "
                f"tradeable={self._is_tradeable})")