from __future__ import annotations

from datetime import datetime
from typing import Optional
from enum import Enum


class OrderType(Enum):
    """Enumeration for order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderSide(Enum):
    """Enumeration for order side"""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """Enumeration for order status"""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Order:
    """
    Pure domain model representing a financial order.

    An order represents an instruction to buy or sell a financial instrument,
    which may or may not result in one or more transactions.
    """

    def __init__(
        self,
        id: int,
        portfolio_id: int,
        holding_id: int,
        order_type: OrderType,
        side: OrderSide,
        quantity: float,
        created_at: datetime,
        status: OrderStatus,
        account_id: str,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        filled_quantity: float = 0.0,
        average_fill_price: Optional[float] = None,
        time_in_force: Optional[str] = None,
        external_order_id: Optional[str] = None,
    ):
        """
        Initialize an Order entity.

        :param id: Unique identifier for the order
        :param portfolio_id: Portfolio placing the order
        :param holding_id: Target holding/instrument
        :param order_type: Type of order (market, limit, etc.)
        :param side: Buy or Sell
        :param quantity: Total requested quantity
        :param created_at: Timestamp when order was created
        :param status: Current order status
        :param account_id: Account identifier
        :param price: Limit price (if applicable)
        :param stop_price: Stop price (if applicable)
        :param filled_quantity: Quantity already filled
        :param average_fill_price: Average execution price
        :param time_in_force: Order duration (GTC, DAY, IOC, etc.)
        :param external_order_id: External system identifier
        """
        self.id = id
        self.portfolio_id = portfolio_id
        self.holding_id = holding_id
        self.order_type = order_type
        self.side = side
        self.quantity = quantity
        self.created_at = created_at
        self.status = status
        self.account_id = account_id
        self.price = price
        self.stop_price = stop_price
        self.filled_quantity = filled_quantity
        self.average_fill_price = average_fill_price
        self.time_in_force = time_in_force
        self.external_order_id = external_order_id

    def is_filled(self) -> bool:
        """Check if the order is completely filled."""
        return self.filled_quantity >= self.quantity

    def is_active(self) -> bool:
        """Check if the order is still active."""
        return self.status in {
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIALLY_FILLED,
        }

    def remaining_quantity(self) -> float:
        """Return remaining quantity to be filled."""
        return max(0.0, self.quantity - self.filled_quantity)

    def is_buy(self) -> bool:
        """Check if order is a buy order."""
        return self.side == OrderSide.BUY

    def is_sell(self) -> bool:
        """Check if order is a sell order."""
        return self.side == OrderSide.SELL

    def __repr__(self) -> str:
        return (
            f"Order(id={self.id}, side={self.side.value}, "
            f"type={self.order_type.value}, status={self.status.value})"
        )