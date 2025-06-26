from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal
import uuid

from .symbol import Symbol
from .enums import OrderType, OrderStatus, OrderDirection, FillType


@dataclass
class OrderTicket:
    """
    Represents a submitted order and provides methods to update and cancel it.
    """
    order_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: Symbol = None
    quantity: int = 0
    order_type: OrderType = OrderType.MARKET
    status: OrderStatus = OrderStatus.NEW
    tag: str = ""
    time: datetime = field(default_factory=datetime.now)
    
    # Price fields
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    
    # Execution details
    quantity_filled: int = 0
    average_fill_price: float = 0.0
    
    # Order properties
    time_in_force: str = "GTC"  # Good Till Canceled
    extended_market_hours: bool = False
    
    @property
    def quantity_remaining(self) -> int:
        """Returns the remaining quantity to be filled"""
        return self.quantity - self.quantity_filled
    
    @property
    def is_filled(self) -> bool:
        """Returns True if the order is completely filled"""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_open(self) -> bool:
        """Returns True if the order is still open (not filled or canceled)"""
        return self.status in [OrderStatus.NEW, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
    
    def cancel(self) -> bool:
        """Attempts to cancel the order"""
        if self.is_open:
            self.status = OrderStatus.CANCELED
            return True
        return False
    
    def update(self, **kwargs) -> bool:
        """Updates order parameters if the order is still open"""
        if not self.is_open:
            return False
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return True


@dataclass
class Order(ABC):
    """
    Base class for all order types.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    symbol: Symbol = None
    quantity: int = 0
    status: OrderStatus = OrderStatus.NEW
    tag: str = ""
    time: datetime = field(default_factory=datetime.now)
    direction: OrderDirection = OrderDirection.BUY
    
    # Execution tracking
    quantity_filled: int = 0
    average_fill_price: float = 0.0
    fills: List['OrderFill'] = field(default_factory=list)
    
    # Order properties
    time_in_force: str = "GTC"
    extended_market_hours: bool = False
    
    @property
    @abstractmethod
    def order_type(self) -> OrderType:
        """Returns the type of this order"""
        pass
    
    @property
    def quantity_remaining(self) -> int:
        """Returns the remaining quantity to be filled"""
        return abs(self.quantity) - self.quantity_filled
    
    @property
    def is_buy(self) -> bool:
        """Returns True if this is a buy order"""
        return self.quantity > 0
    
    @property
    def is_sell(self) -> bool:
        """Returns True if this is a sell order"""
        return self.quantity < 0
    
    @property
    def abs_quantity(self) -> int:
        """Returns the absolute quantity"""
        return abs(self.quantity)
    
    def add_fill(self, fill: 'OrderFill'):
        """Adds a fill to this order"""
        self.fills.append(fill)
        self.quantity_filled += fill.quantity
        
        # Update average fill price
        total_value = sum(f.quantity * f.price for f in self.fills)
        self.average_fill_price = total_value / self.quantity_filled if self.quantity_filled > 0 else 0.0
        
        # Update status
        if self.quantity_filled >= self.abs_quantity:
            self.status = OrderStatus.FILLED
        elif self.quantity_filled > 0:
            self.status = OrderStatus.PARTIALLY_FILLED


class MarketOrder(Order):
    """
    Market order - executes immediately at best available price
    """
    @property
    def order_type(self) -> OrderType:
        return OrderType.MARKET


@dataclass
class LimitOrder(Order):
    """
    Limit order - executes only at specified price or better
    """
    limit_price: float = 0.0
    
    @property
    def order_type(self) -> OrderType:
        return OrderType.LIMIT


@dataclass
class StopMarketOrder(Order):
    """
    Stop market order - becomes market order when stop price is hit
    """
    stop_price: float = 0.0
    
    @property
    def order_type(self) -> OrderType:
        return OrderType.STOP_MARKET


@dataclass
class StopLimitOrder(Order):
    """
    Stop limit order - becomes limit order when stop price is hit
    """
    stop_price: float = 0.0
    limit_price: float = 0.0
    
    @property
    def order_type(self) -> OrderType:
        return OrderType.STOP_LIMIT


@dataclass
class MarketOnOpenOrder(Order):
    """
    Market on open order - executes at market open
    """
    @property
    def order_type(self) -> OrderType:
        return OrderType.MARKET_ON_OPEN


@dataclass
class MarketOnCloseOrder(Order):
    """
    Market on close order - executes at market close
    """
    @property
    def order_type(self) -> OrderType:
        return OrderType.MARKET_ON_CLOSE


@dataclass
class OrderFill:
    """
    Represents a partial or complete fill of an order
    """
    order_id: str
    symbol: Symbol
    quantity: int
    price: float
    time: datetime
    commission: float = 0.0
    fill_type: FillType = FillType.PARTIAL
    
    @property
    def value(self) -> float:
        """Returns the total value of this fill"""
        return self.quantity * self.price


@dataclass
class OrderEvent:
    """
    Represents an event related to an order (submission, fill, cancellation, etc.)
    """
    order_id: str
    symbol: Symbol
    status: OrderStatus
    time: datetime
    message: str = ""
    
    # Fill-specific information
    fill_quantity: int = 0
    fill_price: float = 0.0
    remaining_quantity: int = 0
    
    # Order details
    order: Optional[Order] = None
    
    @property
    def is_fill(self) -> bool:
        """Returns True if this event represents a fill"""
        return self.status in [OrderStatus.PARTIALLY_FILLED, OrderStatus.FILLED]
    
    @property
    def is_error(self) -> bool:
        """Returns True if this event represents an error"""
        return self.status in [OrderStatus.INVALID, OrderStatus.CANCELED_REJECTED]


class OrderBuilder:
    """
    Builder pattern for constructing orders with fluent interface
    """
    def __init__(self, symbol: Symbol, quantity: int):
        self._symbol = symbol
        self._quantity = quantity
        self._order_type = OrderType.MARKET
        self._limit_price = None
        self._stop_price = None
        self._tag = ""
        self._time_in_force = "GTC"
        self._extended_market_hours = False
    
    def as_market_order(self) -> 'OrderBuilder':
        """Configure as market order"""
        self._order_type = OrderType.MARKET
        return self
    
    def as_limit_order(self, limit_price: float) -> 'OrderBuilder':
        """Configure as limit order"""
        self._order_type = OrderType.LIMIT
        self._limit_price = limit_price
        return self
    
    def as_stop_market_order(self, stop_price: float) -> 'OrderBuilder':
        """Configure as stop market order"""
        self._order_type = OrderType.STOP_MARKET
        self._stop_price = stop_price
        return self
    
    def as_stop_limit_order(self, stop_price: float, limit_price: float) -> 'OrderBuilder':
        """Configure as stop limit order"""
        self._order_type = OrderType.STOP_LIMIT
        self._stop_price = stop_price
        self._limit_price = limit_price
        return self
    
    def with_tag(self, tag: str) -> 'OrderBuilder':
        """Add tag to order"""
        self._tag = tag
        return self
    
    def with_time_in_force(self, tif: str) -> 'OrderBuilder':
        """Set time in force"""
        self._time_in_force = tif
        return self
    
    def with_extended_hours(self, extended: bool = True) -> 'OrderBuilder':
        """Enable/disable extended market hours"""
        self._extended_market_hours = extended
        return self
    
    def build(self) -> Order:
        """Build the order"""
        direction = OrderDirection.BUY if self._quantity > 0 else OrderDirection.SELL
        
        base_kwargs = {
            'symbol': self._symbol,
            'quantity': self._quantity,
            'tag': self._tag,
            'direction': direction,
            'time_in_force': self._time_in_force,
            'extended_market_hours': self._extended_market_hours
        }
        
        if self._order_type == OrderType.MARKET:
            return MarketOrder(**base_kwargs)
        elif self._order_type == OrderType.LIMIT:
            return LimitOrder(limit_price=self._limit_price, **base_kwargs)
        elif self._order_type == OrderType.STOP_MARKET:
            return StopMarketOrder(stop_price=self._stop_price, **base_kwargs)
        elif self._order_type == OrderType.STOP_LIMIT:
            return StopLimitOrder(stop_price=self._stop_price, limit_price=self._limit_price, **base_kwargs)
        elif self._order_type == OrderType.MARKET_ON_OPEN:
            return MarketOnOpenOrder(**base_kwargs)
        elif self._order_type == OrderType.MARKET_ON_CLOSE:
            return MarketOnCloseOrder(**base_kwargs)
        else:
            raise ValueError(f"Unsupported order type: {self._order_type}")


def create_order(symbol: Symbol, quantity: int) -> OrderBuilder:
    """Factory function to create an OrderBuilder"""
    return OrderBuilder(symbol, quantity)
