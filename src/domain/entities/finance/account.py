from __future__ import annotations

from datetime import datetime
from typing import Optional
from enum import Enum

from src.domain.entities.entity import Entity


class AccountType(Enum):
    CASH = "CASH"
    MARGIN = "MARGIN"
    RETIREMENT = "RETIREMENT"
    OTHER = "OTHER"


class AccountStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


class Account(Entity):
    """
    Pure domain model representing a trading account.
    """

    def __init__(
        self,
        id: Optional[int],
        account_id: str,
        account_type: AccountType,
        status: AccountStatus,
        base_currency_id: int,
        created_at: datetime,
    ):
        super().__init__(id)
        self.account_id = account_id
        self.account_type = account_type
        self.status = status
        self.base_currency_id = base_currency_id
        self.created_at = created_at

    def is_active(self) -> bool:
        return self.status == AccountStatus.ACTIVE

    def __repr__(self):
        return f"Account(id={self.id}, account_id='{self.account_id}', status={self.status.value})"
