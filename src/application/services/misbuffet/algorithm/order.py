from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from decimal import Decimal
import uuid

from .symbol import Symbol
from .enums import OrderType, OrderStatus, OrderDirection, FillType

# Import domain entities for proper inheritance
from domain.entities.finance.back_testing.orders import (
    Order as DomainOrder,
    MarketOrder as DomainMarketOrder,
    LimitOrder as DomainLimitOrder,
    StopMarketOrder as DomainStopMarketOrder,
    StopLimitOrder as DomainStopLimitOrder,
    MarketOnOpenOrder as DomainMarketOnOpenOrder,
    MarketOnCloseOrder as DomainMarketOnCloseOrder,
    OrderTicket as DomainOrderTicket,
    OrderFill as DomainOrderFill,
    OrderEvent as DomainOrderEvent,
)
from domain.entities.finance.back_testing.enums import OrderDirection as DomainOrderDirection


class OrderTicket(DomainOrderTicket):
    """
    Algorithm framework order ticket extending domain OrderTicket.
    Provides QuantConnect-style API with float convenience methods.
    """
    
    def __init__(self, order: 'Order'):
        """Initialize OrderTicket with domain model compatibility."""
        super().__init__(order)
        
        # Algorithm convenience fields
        self.symbol = order.symbol
        self.quantity = order.quantity
        self.order_type = self._map_order_type(order.order_type)
        self.status = self._map_order_status(order.status) 
        self.tag = order.tag
        self.time = order.time
        self.quantity_filled = order.filled_quantity
        self.average_fill_price = float(order.average_fill_price)
        self.time_in_force = order.time_in_force
        self.extended_market_hours = getattr(order, 'extended_market_hours', False)
        
        # Price fields
        self.limit_price = getattr(order, 'limit_price', None)
        if self.limit_price:
            self.limit_price = float(self.limit_price)
        self.stop_price = getattr(order, 'stop_price', None)
        if self.stop_price:
            self.stop_price = float(self.stop_price)
    
    @staticmethod
    def _map_order_type(domain_type) -> OrderType:
        """Map domain OrderType to algorithm OrderType."""
        # Implementation would map between enum types
        return OrderType.MARKET  # Simplified
    
    @staticmethod
    def _map_order_status(domain_status) -> OrderStatus:
        """Map domain OrderStatus to algorithm OrderStatus.""" 
        # Implementation would map between enum types
        return OrderStatus.NEW  # Simplified
    
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


class Order(DomainOrder):
    """
    Algorithm framework order extending domain Order.
    Provides QuantConnect-style API with algorithm-specific convenience methods.
    """
    
    def __init__(self, symbol: Symbol, quantity: int, direction: OrderDirection, 
                 tag: str = "", time: datetime = None):
        """Initialize Order with algorithm-specific features."""
        # Map algorithm types to domain types
        domain_direction = self._map_direction(direction)
        
        # Initialize domain Order
        super().__init__(symbol, quantity, domain_direction, tag, time)
        
        # Algorithm convenience fields
        self.direction = direction
        self.extended_market_hours: bool = False
    
    @staticmethod
    def _map_direction(algo_direction: OrderDirection) -> DomainOrderDirection:
        """Map algorithm OrderDirection to domain OrderDirection."""
        mapping = {
            OrderDirection.BUY: DomainOrderDirection.BUY,
            OrderDirection.SELL: DomainOrderDirection.SELL,
        }
        return mapping.get(algo_direction, DomainOrderDirection.BUY)
    
    @property
    @abstractmethod
    def order_type(self) -> OrderType:
        """Returns the type of this order"""
        pass
    
    @property
    def quantity_remaining(self) -> int:
        """Returns the remaining quantity to be filled"""
        return self.remaining_quantity
    
    @property
    def quantity_filled(self) -> int:
        """Returns filled quantity for algorithm compatibility"""
        return self.filled_quantity
    
    @property
    def average_fill_price(self) -> float:
        """Returns average fill price as float for algorithm compatibility"""
        return float(super().average_fill_price)
    
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


class MarketOrder(Order, DomainMarketOrder):
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
