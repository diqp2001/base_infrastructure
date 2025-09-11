"""
Domain entities for order system.
Pure domain entities following DDD principles.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional, Dict, Any
from uuid import uuid4

from .enums import OrderType, OrderStatus, OrderDirection
from .symbol import Symbol


@dataclass
class OrderFill:
    """Represents an order fill."""
    fill_id: str = field(default_factory=lambda: str(uuid4()))
    order_id: str = ""
    fill_time: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    fill_price: Decimal = field(default_factory=lambda: Decimal('0'))
    fill_quantity: int = 0
    commission: Decimal = field(default_factory=lambda: Decimal('0'))
    fees: Decimal = field(default_factory=lambda: Decimal('0'))
    
    def __post_init__(self):
        """Ensure decimal precision for financial fields."""
        self.fill_price = Decimal(str(self.fill_price))
        self.commission = Decimal(str(self.commission))
        self.fees = Decimal(str(self.fees))


@dataclass
class OrderEvent:
    """Represents an order event (status change, fill, etc.)."""
    event_id: str = field(default_factory=lambda: str(uuid4()))
    order_id: str = ""
    status: OrderStatus = OrderStatus.NEW
    quantity: int = 0
    fill_price: Optional[Decimal] = None
    message: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Ensure decimal precision."""
        if self.fill_price:
            self.fill_price = Decimal(str(self.fill_price))


class Order(ABC):
    """Abstract base class for all order types."""
    
    def __init__(self, symbol: Symbol, quantity: int, direction: OrderDirection, 
                 tag: str = "", time: datetime = None):
        self.id = str(uuid4())
        self.symbol = symbol
        self.quantity = abs(quantity)  # Always positive, direction determines buy/sell
        self.direction = direction
        self.tag = tag or ""
        self.time = time or datetime.now(timezone.utc)
        self.status = OrderStatus.NEW
        self.order_type = OrderType.MARKET  # Override in subclasses
        
        # Fill tracking
        self.filled_quantity = 0
        self.remaining_quantity = self.quantity
        self.fills: List[OrderFill] = []
        self.commission = Decimal('0')
        self.fees = Decimal('0')
        
        # Validation
        if self.quantity <= 0:
            raise ValueError("Order quantity must be positive")
    
    @property
    def is_filled(self) -> bool:
        """Check if order is completely filled."""
        return self.filled_quantity >= self.quantity
    
    @property
    def is_partially_filled(self) -> bool:
        """Check if order is partially filled."""
        return 0 < self.filled_quantity < self.quantity
    
    @property
    def average_fill_price(self) -> Decimal:
        """Calculate average fill price."""
        if not self.fills:
            return Decimal('0')
        
        total_value = sum(fill.fill_price * fill.fill_quantity for fill in self.fills)
        total_quantity = sum(fill.fill_quantity for fill in self.fills)
        
        return total_value / total_quantity if total_quantity > 0 else Decimal('0')
    
    def add_fill(self, fill: OrderFill):
        """Add a fill to this order."""
        if fill.fill_quantity <= 0:
            raise ValueError("Fill quantity must be positive")
        
        if self.filled_quantity + fill.fill_quantity > self.quantity:
            raise ValueError("Fill would exceed order quantity")
        
        fill.order_id = self.id
        self.fills.append(fill)
        self.filled_quantity += fill.fill_quantity
        self.remaining_quantity = self.quantity - self.filled_quantity
        self.commission += fill.commission
        self.fees += fill.fees
        
        # Update status
        if self.is_filled:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED
    
    def cancel(self):
        """Cancel this order."""
        if self.status in [OrderStatus.FILLED, OrderStatus.CANCELED]:
            raise ValueError(f"Cannot cancel order with status {self.status}")
        
        self.status = OrderStatus.CANCELED
    
    @abstractmethod
    def clone(self) -> 'Order':
        """Create a deep copy of this order."""
        pass
    
    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.symbol}, {self.direction.value}, {self.quantity})"


class MarketOrder(Order):
    """Market order - executes immediately at current market price."""
    
    def __init__(self, symbol: Symbol, quantity: int, direction: OrderDirection, 
                 tag: str = "", time: datetime = None):
        super().__init__(symbol, quantity, direction, tag, time)
        self.order_type = OrderType.MARKET
    
    def clone(self) -> 'MarketOrder':
        """Create a deep copy of this market order."""
        cloned = MarketOrder(self.symbol, self.quantity, self.direction, self.tag, self.time)
        cloned.id = self.id
        cloned.status = self.status
        cloned.filled_quantity = self.filled_quantity
        cloned.remaining_quantity = self.remaining_quantity
        cloned.fills = self.fills.copy()
        cloned.commission = self.commission
        cloned.fees = self.fees
        return cloned


class LimitOrder(Order):
    """Limit order - executes only at specified price or better."""
    
    def __init__(self, symbol: Symbol, quantity: int, direction: OrderDirection,
                 limit_price: Decimal, tag: str = "", time: datetime = None):
        super().__init__(symbol, quantity, direction, tag, time)
        self.order_type = OrderType.LIMIT
        self.limit_price = Decimal(str(limit_price))
        
        if self.limit_price <= 0:
            raise ValueError("Limit price must be positive")
    
    def clone(self) -> 'LimitOrder':
        """Create a deep copy of this limit order."""
        cloned = LimitOrder(self.symbol, self.quantity, self.direction, 
                           self.limit_price, self.tag, self.time)
        cloned.id = self.id
        cloned.status = self.status
        cloned.filled_quantity = self.filled_quantity
        cloned.remaining_quantity = self.remaining_quantity
        cloned.fills = self.fills.copy()
        cloned.commission = self.commission
        cloned.fees = self.fees
        return cloned


class StopMarketOrder(Order):
    """Stop market order - becomes market order when stop price is reached."""
    
    def __init__(self, symbol: Symbol, quantity: int, direction: OrderDirection,
                 stop_price: Decimal, tag: str = "", time: datetime = None):
        super().__init__(symbol, quantity, direction, tag, time)
        self.order_type = OrderType.STOP_MARKET
        self.stop_price = Decimal(str(stop_price))
        self.stop_triggered = False
        
        if self.stop_price <= 0:
            raise ValueError("Stop price must be positive")
    
    def trigger_stop(self):
        """Trigger the stop order."""
        self.stop_triggered = True
        self.status = OrderStatus.SUBMITTED
    
    def clone(self) -> 'StopMarketOrder':
        """Create a deep copy of this stop market order."""
        cloned = StopMarketOrder(self.symbol, self.quantity, self.direction, 
                                self.stop_price, self.tag, self.time)
        cloned.id = self.id
        cloned.status = self.status
        cloned.stop_triggered = self.stop_triggered
        cloned.filled_quantity = self.filled_quantity
        cloned.remaining_quantity = self.remaining_quantity
        cloned.fills = self.fills.copy()
        cloned.commission = self.commission
        cloned.fees = self.fees
        return cloned


class StopLimitOrder(Order):
    """Stop limit order - becomes limit order when stop price is reached."""
    
    def __init__(self, symbol: Symbol, quantity: int, direction: OrderDirection,
                 stop_price: Decimal, limit_price: Decimal, tag: str = "", 
                 time: datetime = None):
        super().__init__(symbol, quantity, direction, tag, time)
        self.order_type = OrderType.STOP_LIMIT
        self.stop_price = Decimal(str(stop_price))
        self.limit_price = Decimal(str(limit_price))
        self.stop_triggered = False
        
        if self.stop_price <= 0 or self.limit_price <= 0:
            raise ValueError("Stop and limit prices must be positive")
    
    def trigger_stop(self):
        """Trigger the stop order."""
        self.stop_triggered = True
        self.status = OrderStatus.SUBMITTED
    
    def clone(self) -> 'StopLimitOrder':
        """Create a deep copy of this stop limit order."""
        cloned = StopLimitOrder(self.symbol, self.quantity, self.direction, 
                               self.stop_price, self.limit_price, self.tag, self.time)
        cloned.id = self.id
        cloned.status = self.status
        cloned.stop_triggered = self.stop_triggered
        cloned.filled_quantity = self.filled_quantity
        cloned.remaining_quantity = self.remaining_quantity
        cloned.fills = self.fills.copy()
        cloned.commission = self.commission
        cloned.fees = self.fees
        return cloned


class MarketOnOpenOrder(Order):
    """Market on open order - executes at market open."""
    
    def __init__(self, symbol: Symbol, quantity: int, direction: OrderDirection, 
                 tag: str = "", time: datetime = None):
        super().__init__(symbol, quantity, direction, tag, time)
        self.order_type = OrderType.MARKET_ON_OPEN
    
    def clone(self) -> 'MarketOnOpenOrder':
        """Create a deep copy of this market on open order."""
        cloned = MarketOnOpenOrder(self.symbol, self.quantity, self.direction, 
                                  self.tag, self.time)
        cloned.id = self.id
        cloned.status = self.status
        cloned.filled_quantity = self.filled_quantity
        cloned.remaining_quantity = self.remaining_quantity
        cloned.fills = self.fills.copy()
        cloned.commission = self.commission
        cloned.fees = self.fees
        return cloned


class MarketOnCloseOrder(Order):
    """Market on close order - executes at market close."""
    
    def __init__(self, symbol: Symbol, quantity: int, direction: OrderDirection, 
                 tag: str = "", time: datetime = None):
        super().__init__(symbol, quantity, direction, tag, time)
        self.order_type = OrderType.MARKET_ON_CLOSE
    
    def clone(self) -> 'MarketOnCloseOrder':
        """Create a deep copy of this market on close order."""
        cloned = MarketOnCloseOrder(self.symbol, self.quantity, self.direction, 
                                   self.tag, self.time)
        cloned.id = self.id
        cloned.status = self.status
        cloned.filled_quantity = self.filled_quantity
        cloned.remaining_quantity = self.remaining_quantity
        cloned.fills = self.fills.copy()
        cloned.commission = self.commission
        cloned.fees = self.fees
        return cloned


class OrderTicket:
    """Tracks order status and allows updates."""
    
    def __init__(self, order: Order):
        self.order_id = order.id
        self.order = order
        self.events: List[OrderEvent] = []
        self.created_time = datetime.now(timezone.utc)
    
    def add_event(self, event: OrderEvent):
        """Add an event to this order ticket."""
        event.order_id = self.order_id
        self.events.append(event)
    
    def get_status(self) -> OrderStatus:
        """Get current order status."""
        return self.order.status
    
    def get_filled_quantity(self) -> int:
        """Get filled quantity."""
        return self.order.filled_quantity
    
    def get_remaining_quantity(self) -> int:
        """Get remaining quantity."""
        return self.order.remaining_quantity


class OrderBuilder:
    """Fluent interface for building orders."""
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset builder to initial state."""
        self._symbol: Optional[Symbol] = None
        self._quantity: int = 0
        self._direction: OrderDirection = OrderDirection.BUY
        self._order_type: OrderType = OrderType.MARKET
        self._limit_price: Optional[Decimal] = None
        self._stop_price: Optional[Decimal] = None
        self._tag: str = ""
        self._time: Optional[datetime] = None
        return self
    
    def symbol(self, symbol: Symbol):
        """Set the symbol."""
        self._symbol = symbol
        return self
    
    def quantity(self, quantity: int):
        """Set the quantity."""
        self._quantity = quantity
        return self
    
    def direction(self, direction: OrderDirection):
        """Set the direction."""
        self._direction = direction
        return self
    
    def market_order(self):
        """Set as market order."""
        self._order_type = OrderType.MARKET
        return self
    
    def limit_order(self, limit_price: Decimal):
        """Set as limit order."""
        self._order_type = OrderType.LIMIT
        self._limit_price = Decimal(str(limit_price))
        return self
    
    def stop_market_order(self, stop_price: Decimal):
        """Set as stop market order."""
        self._order_type = OrderType.STOP_MARKET
        self._stop_price = Decimal(str(stop_price))
        return self
    
    def stop_limit_order(self, stop_price: Decimal, limit_price: Decimal):
        """Set as stop limit order."""
        self._order_type = OrderType.STOP_LIMIT
        self._stop_price = Decimal(str(stop_price))
        self._limit_price = Decimal(str(limit_price))
        return self
    
    def tag(self, tag: str):
        """Set the tag."""
        self._tag = tag
        return self
    
    def time(self, time: datetime):
        """Set the time."""
        self._time = time
        return self
    
    def build(self) -> Order:
        """Build the order."""
        if not self._symbol:
            raise ValueError("Symbol is required")
        if self._quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        if self._order_type == OrderType.MARKET:
            return MarketOrder(self._symbol, self._quantity, self._direction, 
                             self._tag, self._time)
        elif self._order_type == OrderType.LIMIT:
            if not self._limit_price:
                raise ValueError("Limit price is required for limit orders")
            return LimitOrder(self._symbol, self._quantity, self._direction,
                            self._limit_price, self._tag, self._time)
        elif self._order_type == OrderType.STOP_MARKET:
            if not self._stop_price:
                raise ValueError("Stop price is required for stop market orders")
            return StopMarketOrder(self._symbol, self._quantity, self._direction,
                                 self._stop_price, self._tag, self._time)
        elif self._order_type == OrderType.STOP_LIMIT:
            if not self._stop_price or not self._limit_price:
                raise ValueError("Stop and limit prices are required for stop limit orders")
            return StopLimitOrder(self._symbol, self._quantity, self._direction,
                                self._stop_price, self._limit_price, self._tag, self._time)
        elif self._order_type == OrderType.MARKET_ON_OPEN:
            return MarketOnOpenOrder(self._symbol, self._quantity, self._direction,
                                   self._tag, self._time)
        elif self._order_type == OrderType.MARKET_ON_CLOSE:
            return MarketOnCloseOrder(self._symbol, self._quantity, self._direction,
                                    self._tag, self._time)
        else:
            raise ValueError(f"Unsupported order type: {self._order_type}")


def create_order(order_type: OrderType, symbol: Symbol, quantity: int, 
                direction: OrderDirection, **kwargs) -> Order:
    """Factory function for creating orders."""
    if order_type == OrderType.MARKET:
        return MarketOrder(symbol, quantity, direction, 
                         kwargs.get('tag', ''), kwargs.get('time'))
    elif order_type == OrderType.LIMIT:
        limit_price = kwargs.get('limit_price')
        if not limit_price:
            raise ValueError("limit_price is required for limit orders")
        return LimitOrder(symbol, quantity, direction, limit_price,
                        kwargs.get('tag', ''), kwargs.get('time'))
    elif order_type == OrderType.STOP_MARKET:
        stop_price = kwargs.get('stop_price')
        if not stop_price:
            raise ValueError("stop_price is required for stop market orders")
        return StopMarketOrder(symbol, quantity, direction, stop_price,
                             kwargs.get('tag', ''), kwargs.get('time'))
    elif order_type == OrderType.STOP_LIMIT:
        stop_price = kwargs.get('stop_price')
        limit_price = kwargs.get('limit_price')
        if not stop_price or not limit_price:
            raise ValueError("stop_price and limit_price are required for stop limit orders")
        return StopLimitOrder(symbol, quantity, direction, stop_price, limit_price,
                            kwargs.get('tag', ''), kwargs.get('time'))
    elif order_type == OrderType.MARKET_ON_OPEN:
        return MarketOnOpenOrder(symbol, quantity, direction,
                               kwargs.get('tag', ''), kwargs.get('time'))
    elif order_type == OrderType.MARKET_ON_CLOSE:
        return MarketOnCloseOrder(symbol, quantity, direction,
                                kwargs.get('tag', ''), kwargs.get('time'))
    else:
        raise ValueError(f"Unsupported order type: {order_type}")