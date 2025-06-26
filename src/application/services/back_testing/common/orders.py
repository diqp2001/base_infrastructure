"""
Order management classes for all order types and order processing.
"""

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Callable
from decimal import Decimal
from dataclasses import dataclass, field

from .symbol import Symbol
from .enums import OrderType, OrderStatus, OrderDirection


@dataclass
class OrderEvent:
    """
    Represents an event that occurs during order processing.
    """
    order_id: str
    symbol: Symbol
    status: OrderStatus
    quantity: int
    fill_price: Optional[Decimal] = None
    fill_quantity: int = 0
    remaining_quantity: int = 0
    direction: OrderDirection = OrderDirection.BUY
    time: datetime = field(default_factory=datetime.utcnow)
    message: str = ""
    commission: Decimal = field(default=Decimal('0.0'))
    
    def __post_init__(self):
        """Post-initialization to ensure proper types."""
        if self.fill_price is not None and not isinstance(self.fill_price, Decimal):
            self.fill_price = Decimal(str(self.fill_price))
        if not isinstance(self.commission, Decimal):
            self.commission = Decimal(str(self.commission))
    
    @property
    def is_fill(self) -> bool:
        """Returns true if this is a fill event."""
        return self.status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]
    
    @property
    def is_complete(self) -> bool:
        """Returns true if the order is complete (filled or cancelled)."""
        return self.status in [OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.INVALID]
    
    def __str__(self) -> str:
        """String representation of the order event."""
        return f"OrderEvent({self.order_id}, {self.status.value}, {self.fill_quantity}@${self.fill_price})"


@dataclass
class OrderFill:
    """
    Represents a fill of an order.
    """
    order_id: str
    symbol: Symbol
    quantity: int
    fill_price: Decimal
    fill_time: datetime
    commission: Decimal = field(default=Decimal('0.0'))
    
    def __post_init__(self):
        """Post-initialization to ensure proper types."""
        if not isinstance(self.fill_price, Decimal):
            self.fill_price = Decimal(str(self.fill_price))
        if not isinstance(self.commission, Decimal):
            self.commission = Decimal(str(self.commission))
    
    @property
    def fill_value(self) -> Decimal:
        """Total value of the fill."""
        return self.fill_price * abs(self.quantity)
    
    def __str__(self) -> str:
        """String representation of the fill."""
        return f"OrderFill({self.order_id}, {self.quantity}@${self.fill_price})"


class Order(ABC):
    """
    Abstract base class for all order types.
    """
    
    def __init__(self, symbol: Symbol, quantity: int, direction: OrderDirection, 
                 time: datetime, tag: str = ""):
        self.id = str(uuid.uuid4())
        self.symbol = symbol
        self.quantity = abs(quantity)  # Always store as positive
        self.direction = direction
        self.time = time
        self.tag = tag
        self.status = OrderStatus.NEW
        self.order_type = self._get_order_type()
        
        # Fill tracking
        self.filled_quantity = 0
        self.remaining_quantity = self.quantity
        self.fills: List[OrderFill] = []
        
        # Fees and commission
        self.commission = Decimal('0.0')
        self.fees = Decimal('0.0')
    
    @abstractmethod
    def _get_order_type(self) -> OrderType:
        """Get the order type for this order."""
        pass
    
    @property
    def signed_quantity(self) -> int:
        """Get the signed quantity (positive for buy, negative for sell)."""
        return self.quantity if self.direction == OrderDirection.BUY else -self.quantity
    
    @property
    def is_buy(self) -> bool:
        """Returns true if this is a buy order."""
        return self.direction == OrderDirection.BUY
    
    @property
    def is_sell(self) -> bool:
        """Returns true if this is a sell order."""
        return self.direction == OrderDirection.SELL
    
    @property
    def is_filled(self) -> bool:
        """Returns true if the order is completely filled."""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_partially_filled(self) -> bool:
        """Returns true if the order is partially filled."""
        return self.status == OrderStatus.PARTIALLY_FILLED
    
    @property
    def is_open(self) -> bool:
        """Returns true if the order is still open."""
        return self.status in [OrderStatus.NEW, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
    
    @property
    def average_fill_price(self) -> Decimal:
        """Calculate the average fill price."""
        if not self.fills:
            return Decimal('0.0')
        
        total_value = sum(fill.fill_price * fill.quantity for fill in self.fills)
        total_quantity = sum(fill.quantity for fill in self.fills)
        
        return total_value / total_quantity if total_quantity > 0 else Decimal('0.0')
    
    def add_fill(self, fill: OrderFill):
        """Add a fill to this order."""
        self.fills.append(fill)
        self.filled_quantity += abs(fill.quantity)
        self.remaining_quantity = self.quantity - self.filled_quantity
        self.commission += fill.commission
        
        # Update status
        if self.remaining_quantity <= 0:
            self.status = OrderStatus.FILLED
        else:
            self.status = OrderStatus.PARTIALLY_FILLED
    
    def cancel(self) -> bool:
        """Cancel the order if possible."""
        if self.is_open:
            self.status = OrderStatus.CANCELED
            return True
        return False
    
    def clone(self) -> 'Order':
        """Create a copy of this order with a new ID."""
        # This is abstract and should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement clone method")
    
    def __str__(self) -> str:
        """String representation of the order."""
        return (f"{self.__class__.__name__}({self.symbol}, {self.direction.value} "
                f"{self.quantity}, {self.status.value})")


class MarketOrder(Order):
    """
    Market order - executes immediately at current market price.
    """
    
    def _get_order_type(self) -> OrderType:
        return OrderType.MARKET
    
    def clone(self) -> 'MarketOrder':
        """Create a copy of this market order."""
        return MarketOrder(
            symbol=self.symbol,
            quantity=self.signed_quantity,
            direction=self.direction,
            time=self.time,
            tag=self.tag
        )


class LimitOrder(Order):
    """
    Limit order - executes only at the specified price or better.
    """
    
    def __init__(self, symbol: Symbol, quantity: int, direction: OrderDirection,
                 time: datetime, limit_price: Decimal, tag: str = ""):
        super().__init__(symbol, quantity, direction, time, tag)
        if not isinstance(limit_price, Decimal):
            limit_price = Decimal(str(limit_price))
        self.limit_price = limit_price
    
    def _get_order_type(self) -> OrderType:
        return OrderType.LIMIT
    
    def clone(self) -> 'LimitOrder':
        """Create a copy of this limit order."""
        return LimitOrder(
            symbol=self.symbol,
            quantity=self.signed_quantity,
            direction=self.direction,
            time=self.time,
            limit_price=self.limit_price,
            tag=self.tag
        )


class StopMarketOrder(Order):
    """
    Stop market order - becomes a market order when stop price is reached.
    """
    
    def __init__(self, symbol: Symbol, quantity: int, direction: OrderDirection,
                 time: datetime, stop_price: Decimal, tag: str = ""):
        super().__init__(symbol, quantity, direction, time, tag)
        if not isinstance(stop_price, Decimal):
            stop_price = Decimal(str(stop_price))
        self.stop_price = stop_price
        self.stop_triggered = False
    
    def _get_order_type(self) -> OrderType:
        return OrderType.STOP_MARKET
    
    def clone(self) -> 'StopMarketOrder':
        """Create a copy of this stop market order."""
        return StopMarketOrder(
            symbol=self.symbol,
            quantity=self.signed_quantity,
            direction=self.direction,
            time=self.time,
            stop_price=self.stop_price,
            tag=self.tag
        )


class StopLimitOrder(Order):
    """
    Stop limit order - becomes a limit order when stop price is reached.
    """
    
    def __init__(self, symbol: Symbol, quantity: int, direction: OrderDirection,
                 time: datetime, stop_price: Decimal, limit_price: Decimal, tag: str = ""):
        super().__init__(symbol, quantity, direction, time, tag)
        if not isinstance(stop_price, Decimal):
            stop_price = Decimal(str(stop_price))
        if not isinstance(limit_price, Decimal):
            limit_price = Decimal(str(limit_price))
        self.stop_price = stop_price
        self.limit_price = limit_price
        self.stop_triggered = False
    
    def _get_order_type(self) -> OrderType:
        return OrderType.STOP_LIMIT
    
    def clone(self) -> 'StopLimitOrder':
        """Create a copy of this stop limit order."""
        return StopLimitOrder(
            symbol=self.symbol,
            quantity=self.signed_quantity,
            direction=self.direction,
            time=self.time,
            stop_price=self.stop_price,
            limit_price=self.limit_price,
            tag=self.tag
        )


class MarketOnOpenOrder(Order):
    """
    Market on open order - executes at market open.
    """
    
    def _get_order_type(self) -> OrderType:
        return OrderType.MARKET_ON_OPEN
    
    def clone(self) -> 'MarketOnOpenOrder':
        """Create a copy of this market on open order."""
        return MarketOnOpenOrder(
            symbol=self.symbol,
            quantity=self.signed_quantity,
            direction=self.direction,
            time=self.time,
            tag=self.tag
        )


class MarketOnCloseOrder(Order):
    """
    Market on close order - executes at market close.
    """
    
    def _get_order_type(self) -> OrderType:
        return OrderType.MARKET_ON_CLOSE
    
    def clone(self) -> 'MarketOnCloseOrder':
        """Create a copy of this market on close order."""
        return MarketOnCloseOrder(
            symbol=self.symbol,
            quantity=self.signed_quantity,
            direction=self.direction,
            time=self.time,
            tag=self.tag
        )


@dataclass
class OrderTicket:
    """
    Represents a ticket for tracking order status and updates.
    """
    order_id: str
    symbol: Symbol
    quantity: int
    order_type: OrderType
    tag: str
    time: datetime
    status: OrderStatus = OrderStatus.NEW
    limit_price: Optional[Decimal] = None
    stop_price: Optional[Decimal] = None
    
    # Update tracking
    update_requests: List[Dict[str, Any]] = field(default_factory=list)
    
    def __post_init__(self):
        """Post-initialization to ensure proper types."""
        if self.limit_price is not None and not isinstance(self.limit_price, Decimal):
            self.limit_price = Decimal(str(self.limit_price))
        if self.stop_price is not None and not isinstance(self.stop_price, Decimal):
            self.stop_price = Decimal(str(self.stop_price))
    
    def cancel(self) -> bool:
        """Request cancellation of the order."""
        if self.status in [OrderStatus.NEW, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]:
            # In a real implementation, this would send a cancel request to the broker
            self.status = OrderStatus.CANCELED
            return True
        return False
    
    def update(self, **kwargs) -> bool:
        """Request an update to the order."""
        if self.status not in [OrderStatus.NEW, OrderStatus.SUBMITTED]:
            return False
        
        # Store the update request
        update_request = {
            'timestamp': datetime.utcnow(),
            'updates': kwargs
        }
        self.update_requests.append(update_request)
        
        # In a real implementation, this would send the update to the broker
        self.status = OrderStatus.UPDATE_SUBMITTED
        return True
    
    def get_order_events(self) -> List[OrderEvent]:
        """Get all order events for this ticket."""
        # In a real implementation, this would fetch events from the order management system
        return []
    
    def get_fill_events(self) -> List[OrderFill]:
        """Get all fill events for this ticket."""
        # In a real implementation, this would fetch fills from the order management system
        return []
    
    @property
    def is_open(self) -> bool:
        """Returns true if the order is still open."""
        return self.status in [OrderStatus.NEW, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
    
    @property
    def is_filled(self) -> bool:
        """Returns true if the order is completely filled."""
        return self.status == OrderStatus.FILLED
    
    @property
    def is_cancelled(self) -> bool:
        """Returns true if the order is cancelled."""
        return self.status == OrderStatus.CANCELED
    
    def __str__(self) -> str:
        """String representation of the order ticket."""
        return f"OrderTicket({self.order_id}, {self.symbol}, {self.status.value})"


class OrderBuilder:
    """
    Builder class for creating orders with a fluent interface.
    """
    
    def __init__(self):
        self.reset()
    
    def reset(self):
        """Reset the builder to initial state."""
        self._symbol: Optional[Symbol] = None
        self._quantity: int = 0
        self._direction: OrderDirection = OrderDirection.BUY
        self._order_type: OrderType = OrderType.MARKET
        self._limit_price: Optional[Decimal] = None
        self._stop_price: Optional[Decimal] = None
        self._tag: str = ""
        self._time: datetime = datetime.utcnow()
        return self
    
    def symbol(self, symbol: Symbol) -> 'OrderBuilder':
        """Set the symbol."""
        self._symbol = symbol
        return self
    
    def quantity(self, quantity: int) -> 'OrderBuilder':
        """Set the quantity."""
        self._quantity = abs(quantity)
        self._direction = OrderDirection.BUY if quantity > 0 else OrderDirection.SELL
        return self
    
    def buy(self, quantity: int) -> 'OrderBuilder':
        """Set as buy order."""
        self._quantity = abs(quantity)
        self._direction = OrderDirection.BUY
        return self
    
    def sell(self, quantity: int) -> 'OrderBuilder':
        """Set as sell order."""
        self._quantity = abs(quantity)
        self._direction = OrderDirection.SELL
        return self
    
    def market(self) -> 'OrderBuilder':
        """Set as market order."""
        self._order_type = OrderType.MARKET
        return self
    
    def limit(self, price: Decimal) -> 'OrderBuilder':
        """Set as limit order."""
        self._order_type = OrderType.LIMIT
        if not isinstance(price, Decimal):
            price = Decimal(str(price))
        self._limit_price = price
        return self
    
    def stop_market(self, stop_price: Decimal) -> 'OrderBuilder':
        """Set as stop market order."""
        self._order_type = OrderType.STOP_MARKET
        if not isinstance(stop_price, Decimal):
            stop_price = Decimal(str(stop_price))
        self._stop_price = stop_price
        return self
    
    def stop_limit(self, stop_price: Decimal, limit_price: Decimal) -> 'OrderBuilder':
        """Set as stop limit order."""
        self._order_type = OrderType.STOP_LIMIT
        if not isinstance(stop_price, Decimal):
            stop_price = Decimal(str(stop_price))
        if not isinstance(limit_price, Decimal):
            limit_price = Decimal(str(limit_price))
        self._stop_price = stop_price
        self._limit_price = limit_price
        return self
    
    def tag(self, tag: str) -> 'OrderBuilder':
        """Set the order tag."""
        self._tag = tag
        return self
    
    def time(self, time: datetime) -> 'OrderBuilder':
        """Set the order time."""
        self._time = time
        return self
    
    def build(self) -> Order:
        """Build the order."""
        if self._symbol is None:
            raise ValueError("Symbol must be set")
        if self._quantity <= 0:
            raise ValueError("Quantity must be positive")
        
        # Create the appropriate order type
        if self._order_type == OrderType.MARKET:
            return MarketOrder(self._symbol, self._quantity, self._direction, self._time, self._tag)
        elif self._order_type == OrderType.LIMIT:
            if self._limit_price is None:
                raise ValueError("Limit price must be set for limit orders")
            return LimitOrder(self._symbol, self._quantity, self._direction, self._time, 
                            self._limit_price, self._tag)
        elif self._order_type == OrderType.STOP_MARKET:
            if self._stop_price is None:
                raise ValueError("Stop price must be set for stop market orders")
            return StopMarketOrder(self._symbol, self._quantity, self._direction, self._time,
                                 self._stop_price, self._tag)
        elif self._order_type == OrderType.STOP_LIMIT:
            if self._stop_price is None or self._limit_price is None:
                raise ValueError("Both stop price and limit price must be set for stop limit orders")
            return StopLimitOrder(self._symbol, self._quantity, self._direction, self._time,
                                self._stop_price, self._limit_price, self._tag)
        elif self._order_type == OrderType.MARKET_ON_OPEN:
            return MarketOnOpenOrder(self._symbol, self._quantity, self._direction, self._time, self._tag)
        elif self._order_type == OrderType.MARKET_ON_CLOSE:
            return MarketOnCloseOrder(self._symbol, self._quantity, self._direction, self._time, self._tag)
        else:
            raise ValueError(f"Unsupported order type: {self._order_type}")


def create_order(order_type: OrderType, symbol: Symbol, quantity: int, **kwargs) -> Order:
    """
    Factory function to create orders.
    """
    direction = OrderDirection.BUY if quantity > 0 else OrderDirection.SELL
    abs_quantity = abs(quantity)
    time = kwargs.get('time', datetime.utcnow())
    tag = kwargs.get('tag', '')
    
    if order_type == OrderType.MARKET:
        return MarketOrder(symbol, abs_quantity, direction, time, tag)
    elif order_type == OrderType.LIMIT:
        limit_price = kwargs.get('limit_price')
        if limit_price is None:
            raise ValueError("limit_price required for limit orders")
        return LimitOrder(symbol, abs_quantity, direction, time, limit_price, tag)
    elif order_type == OrderType.STOP_MARKET:
        stop_price = kwargs.get('stop_price')
        if stop_price is None:
            raise ValueError("stop_price required for stop market orders")
        return StopMarketOrder(symbol, abs_quantity, direction, time, stop_price, tag)
    elif order_type == OrderType.STOP_LIMIT:
        stop_price = kwargs.get('stop_price')
        limit_price = kwargs.get('limit_price')
        if stop_price is None or limit_price is None:
            raise ValueError("stop_price and limit_price required for stop limit orders")
        return StopLimitOrder(symbol, abs_quantity, direction, time, stop_price, limit_price, tag)
    elif order_type == OrderType.MARKET_ON_OPEN:
        return MarketOnOpenOrder(symbol, abs_quantity, direction, time, tag)
    elif order_type == OrderType.MARKET_ON_CLOSE:
        return MarketOnCloseOrder(symbol, abs_quantity, direction, time, tag)
    else:
        raise ValueError(f"Unsupported order type: {order_type}")