from __future__ import annotations

from enum import Enum
from typing import Optional, List
from datetime import datetime

from src.domain.entities.finance.financial_assets.financial_asset import FinancialAsset

class PositionType(Enum):
    """Type of position for an option leg."""
    LONG = "LONG"
    SHORT = "SHORT"

class Position:
    """
    Represents a financial position built up from transactions.
    
    A position is the net result of all transactions for a specific asset
    and provides the current quantity and position type (long/short).
    The position depends on transactions to calculate its current state.
    """

    def __init__(
        self,
        id: int,
        quantity: int,
        position_type: PositionType,
        asset_id: Optional[int] = None,
        transactions: Optional[List['Transaction']] = None,
        last_updated: Optional[datetime] = None,
    ):
        self.id = id
        self.quantity = quantity
        self.position_type = position_type
        self.asset_id = asset_id
        self.transactions = transactions or []
        self.last_updated = last_updated or datetime.now()

    def add_transaction(self, transaction: 'Transaction') -> None:
        """
        Add a transaction that affects this position.
        
        Args:
            transaction: Transaction to add to this position
        """
        if transaction not in self.transactions:
            self.transactions.append(transaction)
            self.last_updated = datetime.now()
    
    def calculate_quantity_from_transactions(self) -> int:
        """
        Calculate the current quantity based on all transactions.
        
        Returns:
            Net quantity from all transactions
        """
        # Note: This is a simplified calculation. 
        # In practice, you'd need to consider transaction types, 
        # buy/sell directions, etc.
        return len(self.transactions)
    
    def has_transactions(self) -> bool:
        """Check if this position has any associated transactions."""
        return len(self.transactions) > 0

    def __repr__(self) -> str:
        return f"Position(id={self.id}, quantity={self.quantity}, type={self.position_type.value}, transactions={len(self.transactions)})"
