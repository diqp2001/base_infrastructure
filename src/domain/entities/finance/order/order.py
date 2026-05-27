from __future__ import annotations

from datetime import datetime
from typing import Optional
from enum import Enum

from src.domain.entities.entity import Entity


class OrderType(Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP = "STOP"
    STOP_LIMIT = "STOP_LIMIT"


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class Order(Entity):
    """
    Pure domain model representing a financial order.
    """

    def __init__(
        self,
        id: Optional[int],
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
        super().__init__(id)
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
        return self.filled_quantity >= self.quantity

    def is_active(self) -> bool:
        return self.status in {
            OrderStatus.PENDING,
            OrderStatus.SUBMITTED,
            OrderStatus.PARTIALLY_FILLED,
        }

    def remaining_quantity(self) -> float:
        return max(0.0, self.quantity - self.filled_quantity)

    def is_buy(self) -> bool:
        return self.side == OrderSide.BUY

    def is_sell(self) -> bool:
        return self.side == OrderSide.SELL

    def __repr__(self) -> str:
        return (
            f"Order(id={self.id}, side={self.side.value}, "
            f"type={self.order_type.value}, status={self.status.value})"
        )
