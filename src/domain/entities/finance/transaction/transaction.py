from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from enum import Enum

from src.domain.entities.entity import Entity


class TransactionType(Enum):
    MARKET_ORDER = "MARKET_ORDER"
    LIMIT_ORDER = "LIMIT_ORDER"
    STOP_ORDER = "STOP_ORDER"
    STOP_LIMIT_ORDER = "STOP_LIMIT_ORDER"


class TransactionStatus(Enum):
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    REJECTED = "REJECTED"


class Transaction(Entity):
    """
    Pure domain model representing a financial transaction.
    """

    def __init__(
        self,
        id: Optional[int],
        portfolio_id: int,
        holding_id: int,
        order_id: int,
        date: datetime,
        transaction_type: TransactionType,
        transaction_id: str,
        account_id: str,
        trade_date: date,
        value_date: date,
        settlement_date: date,
        status: TransactionStatus,
        spread: float,
        currency_id: int,
        exchange_id: int,
        external_transaction_id: Optional[str] = None,
    ):
        super().__init__(id)
        self.portfolio_id = portfolio_id
        self.holding_id = holding_id
        self.order_id = order_id
        self.date = date
        self.transaction_type = transaction_type
        self.transaction_id = transaction_id
        self.account_id = account_id
        self.trade_date = trade_date
        self.value_date = value_date
        self.settlement_date = settlement_date
        self.currency_id = currency_id
        self.status = status
        self.spread = spread
        self.exchange_id = exchange_id
        self.external_transaction_id = external_transaction_id

    def is_settled(self) -> bool:
        return datetime.now().date() >= self.settlement_date

    def is_executed(self) -> bool:
        return self.status == TransactionStatus.EXECUTED

    def __repr__(self) -> str:
        return f"Transaction(id={self.id}, type={self.transaction_type.value}, status={self.status.value})"
