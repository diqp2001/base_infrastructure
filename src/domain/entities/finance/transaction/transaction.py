from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from enum import Enum




class TransactionType(Enum):
    """Enumeration for transaction types"""
    MARKET_ORDER = "MARKET_ORDER"
    LIMIT_ORDER = "LIMIT_ORDER"
    STOP_ORDER = "STOP_ORDER"
    STOP_LIMIT_ORDER = "STOP_LIMIT_ORDER"


class TransactionStatus(Enum):
    """Enumeration for transaction status"""
    PENDING = "PENDING"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    REJECTED = "REJECTED"


class Transaction:
    """
    Pure domain model representing a financial transaction.
    
    A transaction represents the execution of a trade involving a portfolio
    and a holding, with all relevant details about timing, execution, and status.
    """

    def __init__(
        self,
        id: int,
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
        """
        Initialize a Transaction entity.
        
        :param id: Unique identifier for the transaction
        :param portfolio: Portfolio involved in the transaction
        :param holding: Holding involved in the transaction
        :param date: Date and time when the transaction occurred
        :param entity: The entity with which the transaction was made
        :param transaction_type: Type of transaction (market order, limit order, etc.)
        :param transaction_id: Internal transaction identifier
        :param account_id: Account identifier
        :param trade_date: Date when the trade was executed
        :param value_date: Date when the trade value is determined
        :param settlement_date: Date when the trade settles
        :param currency: Currency of the transaction
        :param status: Current status of the transaction
        :param spread: Spread associated with the transaction
        :param exchange: Optional exchange where the transaction occurred
        :param external_transaction_id: Optional external system transaction ID
        """
        self.id = id
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
        self.currency = currency_id
        self.status = status
        self.spread = spread
        self.exchange_id = exchange_id
        self.external_transaction_id = external_transaction_id

    def is_settled(self) -> bool:
        """Check if the transaction has settled."""
        return datetime.now().date() >= self.settlement_date

    def is_executed(self) -> bool:
        """Check if the transaction has been executed."""
        return self.status == TransactionStatus.EXECUTED

    def __repr__(self) -> str:
        return f"Transaction(id={self.id}, type={self.transaction_type.value}, status={self.status.value})"