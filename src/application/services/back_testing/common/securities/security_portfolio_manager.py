"""
SecurityPortfolioManager class for managing portfolio and cash.
"""

from typing import Dict, List, Optional
from decimal import Decimal
from dataclasses import dataclass, field

from ..symbol import Symbol
from .security import Security
from .security_holding import SecurityHolding


@dataclass
class SecurityPortfolioManager:
    """
    Manages portfolio holdings, cash, and overall portfolio performance.
    """
    cash: Decimal = field(default=Decimal('100000'))
    _holdings: Dict[Symbol, SecurityHolding] = field(default_factory=dict, init=False)
    _total_portfolio_value: Decimal = field(default=Decimal('0'), init=False)
    
    def __post_init__(self):
        """Post-initialization to ensure proper types."""
        if not isinstance(self.cash, Decimal):
            self.cash = Decimal(str(self.cash))
        self._total_portfolio_value = self.cash
    
    @property
    def total_portfolio_value(self) -> Decimal:
        """Total value of the portfolio including cash and holdings."""
        holdings_value = sum(holding.market_value for holding in self._holdings.values())
        return self.cash + holdings_value
    
    @property
    def total_unrealized_profit(self) -> Decimal:
        """Total unrealized profit/loss across all holdings."""
        return sum(holding.unrealized_profit for holding in self._holdings.values())
    
    @property
    def total_fees(self) -> Decimal:
        """Total fees paid (placeholder for future implementation)."""
        return Decimal('0')
    
    @property
    def net_profit(self) -> Decimal:
        """Net profit including realized and unrealized gains."""
        starting_cash = Decimal('100000')  # TODO: Make this configurable
        return self.total_portfolio_value - starting_cash
    
    @property
    def invested(self) -> bool:
        """True if there are any positions in the portfolio."""
        return any(holding.invested for holding in self._holdings.values())
    
    def get_holding(self, symbol: Symbol) -> SecurityHolding:
        """Get or create a holding for the given symbol."""
        if symbol not in self._holdings:
            # Create a placeholder security for the holding
            # In a real implementation, this would come from the securities collection
            from ..symbol import SymbolProperties
            from ..enums import SecurityType
            
            symbol_props = SymbolProperties(
                description=str(symbol),
                security_type=symbol.security_type,
                lot_size=1,
                price_variation=Decimal('0.01'),
                market_ticker=str(symbol)
            )
            
            security = Security(
                symbol=symbol,
                symbol_properties=symbol_props
            )
            
            self._holdings[symbol] = SecurityHolding(security=security)
        
        return self._holdings[symbol]
    
    def add_transaction(self, symbol: Symbol, quantity: Decimal, price: Decimal, fee: Decimal = Decimal('0')) -> None:
        """Add a transaction to the portfolio."""
        if not isinstance(quantity, Decimal):
            quantity = Decimal(str(quantity))
        if not isinstance(price, Decimal):
            price = Decimal(str(price))
        if not isinstance(fee, Decimal):
            fee = Decimal(str(fee))
        
        # Calculate transaction value
        transaction_value = quantity * price + fee
        
        # Check if we have enough cash for purchases
        if quantity > 0 and self.cash < transaction_value:
            raise ValueError(f"Insufficient cash for transaction. Required: ${transaction_value}, Available: ${self.cash}")
        
        # Update cash
        self.cash -= transaction_value
        
        # Update holding
        holding = self.get_holding(symbol)
        holding.add_shares(quantity, price)
        
        # Remove holding if position is closed
        if not holding.invested:
            del self._holdings[symbol]
    
    def get_holdings(self) -> List[SecurityHolding]:
        """Get all holdings in the portfolio."""
        return list(self._holdings.values())
    
    def get_holdings_dict(self) -> Dict[Symbol, SecurityHolding]:
        """Get holdings as a dictionary."""
        return self._holdings.copy()
    
    def contains_key(self, symbol: Symbol) -> bool:
        """Check if the portfolio contains a holding for the given symbol."""
        return symbol in self._holdings
    
    def __getitem__(self, symbol: Symbol) -> SecurityHolding:
        """Get a holding by symbol using bracket notation."""
        return self.get_holding(symbol)
    
    def __contains__(self, symbol: Symbol) -> bool:
        """Check if a symbol exists using 'in' operator."""
        return symbol in self._holdings
    
    def __str__(self) -> str:
        """String representation of the portfolio."""
        return f"Portfolio(Value: ${self.total_portfolio_value}, Cash: ${self.cash}, Holdings: {len(self._holdings)})"
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return (f"SecurityPortfolioManager(total_value=${self.total_portfolio_value}, "
                f"cash=${self.cash}, holdings={len(self._holdings)})")