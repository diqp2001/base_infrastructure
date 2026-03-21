from __future__ import annotations

from datetime import datetime
from typing import Optional
from enum import Enum


class AccountType(Enum):
    """Enumeration for account types"""
    CASH = "CASH"
    MARGIN = "MARGIN"
    RETIREMENT = "RETIREMENT"
    OTHER = "OTHER"


class AccountStatus(Enum):
    """Enumeration for account status"""
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"
    CLOSED = "CLOSED"


class Account:
    """
    Pure domain model representing a trading account.

    An account is the container through which orders are placed and
    transactions are executed. It holds cash balances and is linked
    to portfolios.
    """

    def __init__(
        self,
        id: int,
        account_id: str,
        account_type: AccountType,
        status: AccountStatus,
        base_currency_id: int,
        created_at: datetime
    ):
        
        self.id = id
        self.account_id = account_id
        self.account_type = account_type
        self.status = status
        self.base_currency_id = base_currency_id
        self.created_at = created_at

    def is_active(self) -> bool:
        """Check if account is active."""
        return self.status == AccountStatus.ACTIVE

    

    

    