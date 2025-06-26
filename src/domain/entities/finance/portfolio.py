from typing import List, Dict, Optional
from decimal import Decimal
from datetime import datetime
from .position import Position

class Portfolio:
    """Domain entity representing a financial portfolio containing positions in various assets."""
    
    def __init__(self, id: int, name: str, initial_capital: Decimal, created_date: datetime):
        self.id = id
        self.name = name
        self.initial_capital = initial_capital
        self.created_date = created_date
        self.positions: List[Position] = []
        self._cash_balance = initial_capital
    
    @property
    def cash_balance(self) -> Decimal:
        """Current cash balance in the portfolio."""
        return self._cash_balance
    
    def add_position(self, position: Position) -> None:
        """Add a position to the portfolio."""
        self.positions.append(position)
        
    def remove_position(self, position_id: int) -> bool:
        """Remove a position from the portfolio by ID."""
        for i, position in enumerate(self.positions):
            if position.id == position_id:
                self.positions.pop(i)
                return True
        return False
    
    def get_position(self, asset_id: int) -> Optional[Position]:
        """Get position for a specific asset."""
        for position in self.positions:
            if position.asset_id == asset_id:
                return position
        return None
    
    def calculate_total_value(self, current_prices: Dict[int, Decimal]) -> Decimal:
        """Calculate total portfolio value based on current asset prices."""
        total_positions_value = sum(
            position.calculate_value(current_prices.get(position.asset_id, Decimal('0')))
            for position in self.positions
        )
        return self.cash_balance + total_positions_value
    
    def calculate_pnl(self, current_prices: Dict[int, Decimal]) -> Decimal:
        """Calculate unrealized profit and loss."""
        current_value = self.calculate_total_value(current_prices)
        return current_value - self.initial_capital
    
    def update_cash_balance(self, amount: Decimal) -> None:
        """Update cash balance (positive for deposits, negative for withdrawals)."""
        self._cash_balance += amount
    
    def __repr__(self):
        return f"<Portfolio(id={self.id}, name='{self.name}', positions={len(self.positions)})>"