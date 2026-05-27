from __future__ import annotations

from enum import Enum
from typing import Optional, List
from datetime import datetime

from src.domain.entities.entity import Entity


class PositionType(Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class Position(Entity):
    """
    Represents a financial position built up from transactions.
    """

    def __init__(
        self,
        id: Optional[int],
        quantity: int,
        position_type: PositionType,
        asset_id: Optional[int] = None,
        transactions: Optional[List] = None,
        last_updated: Optional[datetime] = None,
    ):
        super().__init__(id)
        self.quantity = quantity
        self.position_type = position_type
        self.asset_id = asset_id
        self.transactions = transactions or []
        self.last_updated = last_updated or datetime.now()

    def add_transaction(self, transaction) -> None:
        if transaction not in self.transactions:
            self.transactions.append(transaction)
            self.last_updated = datetime.now()

    def calculate_quantity_from_transactions(self) -> int:
        return len(self.transactions)

    def has_transactions(self) -> bool:
        return len(self.transactions) > 0

    def __repr__(self) -> str:
        return f"Position(id={self.id}, quantity={self.quantity}, type={self.position_type.value})"
