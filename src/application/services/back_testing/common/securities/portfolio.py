"""
Portfolio class for high-level portfolio management.
"""

from typing import Dict, List, Optional
from decimal import Decimal
from dataclasses import dataclass, field

from ..symbol import Symbol
from .security_holding import SecurityHolding
from .security_portfolio_manager import SecurityPortfolioManager


@dataclass
class Portfolio:
    """
    High-level portfolio management class that provides
    simplified access to portfolio functionality.
    """
    _portfolio_manager: SecurityPortfolioManager = field(default_factory=SecurityPortfolioManager, init=False)
    
    @property
    def cash(self) -> Decimal:
        """Available cash in the portfolio."""
        return self._portfolio_manager.cash
    
    @property
    def total_portfolio_value(self) -> Decimal:
        """Total value of the portfolio including cash and holdings."""
        return self._portfolio_manager.total_portfolio_value
    
    @property
    def total_unrealized_profit(self) -> Decimal:
        """Total unrealized profit/loss across all holdings."""
        return self._portfolio_manager.total_unrealized_profit
    
    @property
    def net_profit(self) -> Decimal:
        """Net profit including realized and unrealized gains."""
        return self._portfolio_manager.net_profit
    
    @property
    def invested(self) -> bool:
        """True if there are any positions in the portfolio."""
        return self._portfolio_manager.invested
    
    def get_holding(self, symbol: Symbol) -> SecurityHolding:
        """Get or create a holding for the given symbol."""
        return self._portfolio_manager.get_holding(symbol)
    
    def get_holdings(self) -> List[SecurityHolding]:
        """Get all holdings in the portfolio."""
        return self._portfolio_manager.get_holdings()
    
    def contains_key(self, symbol: Symbol) -> bool:
        """Check if the portfolio contains a holding for the given symbol."""
        return self._portfolio_manager.contains_key(symbol)
    
    def __getitem__(self, symbol: Symbol) -> SecurityHolding:
        """Get a holding by symbol using bracket notation."""
        return self._portfolio_manager[symbol]
    
    def __contains__(self, symbol: Symbol) -> bool:
        """Check if a symbol exists using 'in' operator."""
        return symbol in self._portfolio_manager
    
    def __str__(self) -> str:
        """String representation of the portfolio."""
        return str(self._portfolio_manager)
    
    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"Portfolio({self._portfolio_manager})"