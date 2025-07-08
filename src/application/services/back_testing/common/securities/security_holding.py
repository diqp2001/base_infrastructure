"""
SecurityHolding class for tracking portfolio holdings.
"""

from decimal import Decimal
from typing import Optional
from dataclasses import dataclass, field

from ..symbol import Symbol
from .security import Security


@dataclass
class SecurityHolding:
    """
    Represents a holding of a security in the portfolio.
    Tracks quantity, average price, and profit/loss.
    """
    security: Security
    quantity: Decimal = field(default=Decimal('0'))
    average_price: Decimal = field(default=Decimal('0'))
    
    def __post_init__(self):
        """Post-initialization to ensure proper types."""
        if not isinstance(self.quantity, Decimal):
            self.quantity = Decimal(str(self.quantity))
        if not isinstance(self.average_price, Decimal):
            self.average_price = Decimal(str(self.average_price))
    
    @property
    def symbol(self) -> Symbol:
        """The symbol of the held security."""
        return self.security.symbol
    
    @property
    def market_price(self) -> Decimal:
        """Current market price of the held security."""
        return self.security.market_price
    
    @property
    def market_value(self) -> Decimal:
        """Current market value of the holding."""
        return self.quantity * self.market_price
    
    @property
    def cost_basis(self) -> Decimal:
        """Total cost basis of the holding."""
        return self.quantity * self.average_price
    
    @property
    def unrealized_profit(self) -> Decimal:
        """Unrealized profit/loss of the holding."""
        return self.market_value - self.cost_basis
    
    @property
    def unrealized_profit_percent(self) -> Decimal:
        """Unrealized profit/loss as a percentage."""
        if self.cost_basis == 0:
            return Decimal('0')
        return (self.unrealized_profit / self.cost_basis) * 100
    
    @property
    def is_long(self) -> bool:
        """True if the holding is long (positive quantity)."""
        return self.quantity > 0
    
    @property
    def is_short(self) -> bool:
        """True if the holding is short (negative quantity)."""
        return self.quantity < 0
    
    @property
    def invested(self) -> bool:
        """True if there is a position in this security."""
        return self.quantity != 0
    
    def add_shares(self, quantity: Decimal, price: Decimal) -> None:
        """Add shares to the holding with weighted average price calculation."""
        if not isinstance(quantity, Decimal):
            quantity = Decimal(str(quantity))
        if not isinstance(price, Decimal):
            price = Decimal(str(price))
        
        if self.quantity == 0:
            # First purchase
            self.quantity = quantity
            self.average_price = price
        else:
            # Calculate weighted average price
            total_cost = self.cost_basis + (quantity * price)
            self.quantity += quantity
            if self.quantity != 0:
                self.average_price = total_cost / self.quantity
            else:
                self.average_price = Decimal('0')
    
    def remove_shares(self, quantity: Decimal) -> Decimal:
        """Remove shares from the holding and return realized profit."""
        if not isinstance(quantity, Decimal):
            quantity = Decimal(str(quantity))
        
        if abs(quantity) > abs(self.quantity):
            raise ValueError("Cannot remove more shares than held")
        
        # Calculate realized profit
        realized_profit = quantity * (self.market_price - self.average_price)
        
        # Update quantity
        self.quantity -= quantity
        
        # If position is closed, reset average price
        if self.quantity == 0:
            self.average_price = Decimal('0')
        
        return realized_profit
    
    def __str__(self) -> str:
        """String representation of the holding."""
        return f"SecurityHolding({self.symbol}, {self.quantity} @ ${self.average_price})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"SecurityHolding(symbol={self.symbol}, quantity={self.quantity}, "
                f"avg_price=${self.average_price}, market_value=${self.market_value})")