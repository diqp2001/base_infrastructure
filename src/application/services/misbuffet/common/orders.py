"""
Order management classes for the backtesting framework.
Based on QuantConnect's order system architecture.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional, Any, Union
import uuid

from .symbol import Symbol
from .enums import OrderType, OrderDirection, OrderStatus, OrderFillStatus


@dataclass
class Order:
    """
    Base class for all order types.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: Symbol = None
    quantity: int = 0
    direction: OrderDirection = OrderDirection.BUY
    order_type: OrderType = OrderType.MARKET
    status: OrderStatus = OrderStatus.NEW
    time: datetime = field(default_factory=datetime.now)
    created_time: datetime = field(default_factory=datetime.now)
    last_fill_time: Optional[datetime] = None
    last_update_time: Optional[datetime] = None
    tag: str = ""
    
    # Price fields
    price: float = 0.0
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Execution tracking
    quantity_filled: int = 0
    price_filled: float = 0.0
    average_fill_price: float = 0.0
    
    def __post_init__(self):
        if self.created_time is None:
            self.created_time = datetime.now()
        if self.last_update_time is None:
            self.last_update_time = self.created_time
    
    @property
    def is_filled(self) -> bool:
        """Returns True if the order is completely filled."""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_partially_filled(self) -> bool:
        """Returns True if the order is partially filled."""
        return self.status == OrderStatus.PARTIAL_FILLED
    
    @property
    def quantity_remaining(self) -> int:
        """Returns the remaining quantity to be filled."""
        return abs(self.quantity) - abs(self.quantity_filled)
    
    @property
    def absolute_quantity(self) -> int:
        """Returns the absolute quantity of the order."""
        return abs(self.quantity)
    
    def update_status(self, status: OrderStatus, time: Optional[datetime] = None):
        """Update the order status."""
        self.status = status
        self.last_update_time = time or datetime.now()
    
    def add_fill(self, fill_quantity: int, fill_price: float, time: Optional[datetime] = None):
        """Add a fill to this order."""
        fill_time = time or datetime.now()
        
        # Update fill tracking
        total_quantity_filled = abs(self.quantity_filled) + abs(fill_quantity)
        total_value = (self.average_fill_price * abs(self.quantity_filled) + 
                      fill_price * abs(fill_quantity))
        
        self.quantity_filled += fill_quantity
        self.average_fill_price = total_value / total_quantity_filled if total_quantity_filled > 0 else 0.0
        self.price_filled = fill_price
        self.last_fill_time = fill_time
        self.last_update_time = fill_time
        
        # Update status
        if abs(self.quantity_filled) >= abs(self.quantity):
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIAL_FILLED


@dataclass
class MarketOrder(Order):
    """Market order implementation."""
    order_type: OrderType = field(default=OrderType.MARKET, init=False)


@dataclass
class LimitOrder(Order):
    """Limit order implementation."""
    order_type: OrderType = field(default=OrderType.LIMIT, init=False)
    
    def __post_init__(self):
        super().__post_init__()
        if self.limit_price is None and self.price > 0:
            self.limit_price = self.price


@dataclass
class StopMarketOrder(Order):
    """Stop market order implementation."""
    order_type: OrderType = field(default=OrderType.STOP_MARKET, init=False)
    
    def __post_init__(self):
        super().__post_init__()
        if self.stop_price is None and self.price > 0:
            self.stop_price = self.price


@dataclass
class StopLimitOrder(Order):
    """Stop limit order implementation."""
    order_type: OrderType = field(default=OrderType.STOP_LIMIT, init=False)
    
    def __post_init__(self):
        super().__post_init__()
        if self.stop_price is None and self.price > 0:
            self.stop_price = self.price


@dataclass
class MarketOnOpenOrder(Order):
    """Market on open order implementation."""
    order_type: OrderType = field(default=OrderType.MARKET_ON_OPEN, init=False)


@dataclass
class MarketOnCloseOrder(Order):
    """Market on close order implementation."""
    order_type: OrderType = field(default=OrderType.MARKET_ON_CLOSE, init=False)


@dataclass
class OrderEvent:
    """
    Represents an event that occurred with an order (fill, cancellation, etc.).
    """
    order_id: str
    symbol: Symbol
    status: OrderStatus
    fill_quantity: int = 0
    fill_price: float = 0.0
    direction: OrderDirection = OrderDirection.BUY
    order_fee: float = 0.0
    message: str = ""
    time: datetime = field(default_factory=datetime.now)
    
    @property
    def absolute_fill_quantity(self) -> int:
        """Returns the absolute fill quantity."""
        return abs(self.fill_quantity)
    
    @property
    def fill_price_currency(self) -> str:
        """Returns the currency of the fill price."""
        # This would normally be determined by the symbol properties
        return "USD"
    
    def is_fill(self) -> bool:
        """Returns True if this is a fill event."""
        return self.status in [OrderStatus.FILLED, OrderStatus.PARTIAL_FILLED] and self.fill_quantity != 0


@dataclass
class OrderFill:
    """
    Represents a fill (partial or complete) of an order.
    """
    order_id: str
    symbol: Symbol
    quantity: int
    price: float
    time: datetime
    commission: float = 0.0
    fee: float = 0.0
    fill_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    @property
    def value(self) -> float:
        """Returns the monetary value of this fill."""
        return abs(self.quantity) * self.price
    
    @property
    def total_fees(self) -> float:
        """Returns total fees for this fill."""
        return self.commission + self.fee


@dataclass
class OrderTicket:
    """
    Represents a ticket for tracking an order through its lifecycle.
    """
    order_id: str
    symbol: Symbol
    quantity: int
    order_type: OrderType
    tag: str = ""
    time: datetime = field(default_factory=datetime.now)
    status: OrderStatus = OrderStatus.NEW
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Tracking fields
    quantity_filled: int = 0
    average_fill_price: float = 0.0
    order_events: List[OrderEvent] = field(default_factory=list)
    
    def update(self, order_event: OrderEvent):
        """Update the ticket with an order event."""
        self.order_events.append(order_event)
        self.status = order_event.status
        
        if order_event.is_fill():
            self.quantity_filled += order_event.fill_quantity
            # Update average fill price
            if self.quantity_filled != 0:
                total_value = sum(event.fill_quantity * event.fill_price 
                                for event in self.order_events if event.is_fill())
                self.average_fill_price = total_value / self.quantity_filled
    
    def cancel(self) -> bool:
        """Attempt to cancel this order."""
        if self.status in [OrderStatus.NEW, OrderStatus.SUBMITTED, OrderStatus.PARTIAL_FILLED]:
            self.status = OrderStatus.CANCEL_PENDING
            return True
        return False
    
    @property
    def quantity_remaining(self) -> int:
        """Returns the remaining quantity to be filled."""
        return abs(self.quantity) - abs(self.quantity_filled)
    
    @property
    def is_filled(self) -> bool:
        """Returns True if the order is completely filled."""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_open(self) -> bool:
        """Returns True if the order is still open (not filled or canceled)."""
        return self.status in [
            OrderStatus.NEW, 
            OrderStatus.SUBMITTED, 
            OrderStatus.PARTIAL_FILLED,
            OrderStatus.UPDATE_SUBMITTED
        ]


class OrderBuilder:
    """
    Builder class for creating orders with fluent interface.
    """
    
    def __init__(self, order_type: OrderType):
        self.order_type = order_type
        self._symbol = None
        self._quantity = 0
        self._price = 0.0
        self._limit_price = None
        self._stop_price = None
        self._tag = ""
        self._time = None
    
    def for_symbol(self, symbol: Symbol):
        """Set the symbol for the order."""
        self._symbol = symbol
        return self
    
    def with_quantity(self, quantity: int):
        """Set the quantity for the order."""
        self._quantity = quantity
        return self
    
    def at_price(self, price: float):
        """Set the price for the order."""
        self._price = price
        return self
    
    def with_limit_price(self, limit_price: float):
        """Set the limit price for the order."""
        self._limit_price = limit_price
        return self
    
    def with_stop_price(self, stop_price: float):
        """Set the stop price for the order."""
        self._stop_price = stop_price
        return self
    
    def with_tag(self, tag: str):
        """Set a tag for the order."""
        self._tag = tag
        return self
    
    def at_time(self, time: datetime):
        """Set the time for the order."""
        self._time = time
        return self
    
    def build(self) -> Order:
        """Build and return the order."""
        direction = OrderDirection.BUY if self._quantity > 0 else OrderDirection.SELL
        
        order_kwargs = {
            'symbol': self._symbol,
            'quantity': self._quantity,
            'direction': direction,
            'price': self._price,
            'limit_price': self._limit_price,
            'stop_price': self._stop_price,
            'tag': self._tag,
            'time': self._time or datetime.now()
        }
        
        if self.order_type == OrderType.MARKET:
            return MarketOrder(**order_kwargs)
        elif self.order_type == OrderType.LIMIT:
            return LimitOrder(**order_kwargs)
        elif self.order_type == OrderType.STOP_MARKET:
            return StopMarketOrder(**order_kwargs)
        elif self.order_type == OrderType.STOP_LIMIT:
            return StopLimitOrder(**order_kwargs)
        elif self.order_type == OrderType.MARKET_ON_OPEN:
            return MarketOnOpenOrder(**order_kwargs)
        elif self.order_type == OrderType.MARKET_ON_CLOSE:
            return MarketOnCloseOrder(**order_kwargs)
        else:
            return Order(**order_kwargs)


def create_order(order_type: OrderType, symbol: Symbol, quantity: int, **kwargs) -> Order:
    """
    Factory function to create orders.
    """
    direction = OrderDirection.BUY if quantity > 0 else OrderDirection.SELL
    
    order_kwargs = {
        'symbol': symbol,
        'quantity': quantity,
        'direction': direction,
        'time': kwargs.get('time', datetime.now()),
        **kwargs
    }
    
    if order_type == OrderType.MARKET:
        return MarketOrder(**order_kwargs)
    elif order_type == OrderType.LIMIT:
        return LimitOrder(**order_kwargs)
    elif order_type == OrderType.STOP_MARKET:
        return StopMarketOrder(**order_kwargs)
    elif order_type == OrderType.STOP_LIMIT:
        return StopLimitOrder(**order_kwargs)
    elif order_type == OrderType.MARKET_ON_OPEN:
        return MarketOnOpenOrder(**order_kwargs)
    elif order_type == OrderType.MARKET_ON_CLOSE:
        return MarketOnCloseOrder(**order_kwargs)
    else:
        return Order(**order_kwargs)