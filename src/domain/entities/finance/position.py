from decimal import Decimal
from datetime import datetime
from typing import Optional

class Position:
    """Domain entity representing a position in a financial asset within a portfolio."""
    
    def __init__(self, id: int, asset_id: int, quantity: Decimal, 
                 entry_price: Decimal, entry_date: datetime):
        self.id = id
        self.asset_id = asset_id
        self.quantity = quantity
        self.entry_price = entry_price
        self.entry_date = entry_date
        self.exit_price: Optional[Decimal] = None
        self.exit_date: Optional[datetime] = None
        
    @property
    def is_open(self) -> bool:
        """Check if position is still open."""
        return self.exit_price is None and self.exit_date is None
    
    def calculate_value(self, current_price: Decimal) -> Decimal:
        """Calculate current value of the position."""
        if self.is_open:
            return self.quantity * current_price
        else:
            return self.quantity * self.exit_price
    
    def calculate_unrealized_pnl(self, current_price: Decimal) -> Decimal:
        """Calculate unrealized profit and loss for open positions."""
        if not self.is_open:
            return Decimal('0')
        return (current_price - self.entry_price) * self.quantity
    
    def calculate_realized_pnl(self) -> Decimal:
        """Calculate realized profit and loss for closed positions."""
        if self.is_open:
            return Decimal('0')
        return (self.exit_price - self.entry_price) * self.quantity
    
    def close_position(self, exit_price: Decimal, exit_date: datetime) -> None:
        """Close the position with exit price and date."""
        self.exit_price = exit_price
        self.exit_date = exit_date
    
    def __repr__(self):
        status = "Open" if self.is_open else "Closed"
        return f"<Position(id={self.id}, asset_id={self.asset_id}, quantity={self.quantity}, status={status})>"