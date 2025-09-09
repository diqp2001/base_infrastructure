"""
Mock Portfolio domain entity for backtesting operations.
Provides simplified portfolio functionality for test scenarios.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Optional
# Forward declaration to avoid circular import
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .mock_security import MockSecurity


@dataclass
class MockPortfolioHoldings:
    """Value object representing portfolio holdings."""
    total_portfolio_value: Decimal = Decimal('0')
    cash: Decimal = Decimal('0')
    holdings_value: Decimal = Decimal('0')
    margin_used: Decimal = Decimal('0')
    margin_remaining: Decimal = Decimal('0')
    unsettled_cash: Decimal = Decimal('0')
    
    @property
    def invested_value(self) -> Decimal:
        """Calculate total invested value (holdings - cash)."""
        return self.holdings_value
    
    @property
    def buying_power(self) -> Decimal:
        """Calculate available buying power."""
        return self.cash + self.margin_remaining


@dataclass
class MockPortfolioStatistics:
    """Value object for portfolio performance statistics."""
    total_performance: Decimal = Decimal('0')
    total_return: Decimal = Decimal('0')
    annual_return: Decimal = Decimal('0')
    sharpe_ratio: Decimal = Decimal('0')
    max_drawdown: Decimal = Decimal('0')
    volatility: Decimal = Decimal('0')
    trades_count: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    @property
    def win_rate(self) -> Decimal:
        """Calculate win rate percentage."""
        if self.trades_count == 0:
            return Decimal('0')
        return Decimal(self.winning_trades) / Decimal(self.trades_count) * Decimal('100')


class MockPortfolio:
    """
    Mock portfolio implementation for backtesting.
    Simulates portfolio behavior without real trading operations.
    """
    
    def __init__(self, initial_cash: Decimal = Decimal('100000')):
        self._initial_cash = initial_cash
        self._cash = initial_cash
        self._securities: Dict[str, 'MockSecurity'] = {}
        self._holdings: Dict[str, Decimal] = {}  # symbol -> quantity
        self._average_costs: Dict[str, Decimal] = {}  # symbol -> avg cost
        self._transactions: List[Dict] = []
        self._created_at = datetime.now()
        self._last_update = datetime.now()
        
        # Portfolio tracking
        self._portfolio_value_history: List[Decimal] = [initial_cash]
        self._high_water_mark = initial_cash
        self._max_drawdown = Decimal('0')
    
    @property
    def cash(self) -> Decimal:
        """Get current cash balance."""
        return self._cash
    
    @property
    def total_portfolio_value(self) -> Decimal:
        """Calculate total portfolio value."""
        holdings_value = sum(
            self._holdings.get(symbol, Decimal('0')) * security.price
            for symbol, security in self._securities.items()
        )
        return self._cash + holdings_value
    
    @property
    def holdings_value(self) -> Decimal:
        """Calculate total holdings value."""
        return sum(
            self._holdings.get(symbol, Decimal('0')) * security.price
            for symbol, security in self._securities.items()
        )
    
    @property
    def invested_value(self) -> Decimal:
        """Get invested value (non-cash holdings)."""
        return self.holdings_value
    
    def add_security(self, security: 'MockSecurity') -> None:
        """Add a security to the portfolio."""
        self._securities[security.symbol.value] = security
        if security.symbol.value not in self._holdings:
            self._holdings[security.symbol.value] = Decimal('0')
            self._average_costs[security.symbol.value] = Decimal('0')
    
    def get_security(self, symbol: str) -> Optional['MockSecurity']:
        """Get security by symbol."""
        return self._securities.get(symbol)
    
    def get_holdings(self) -> Dict[str, Decimal]:
        """Get all holdings quantities."""
        return self._holdings.copy()
    
    def get_holding_quantity(self, symbol: str) -> Decimal:
        """Get quantity held for specific symbol."""
        return self._holdings.get(symbol, Decimal('0'))
    
    def get_holding_value(self, symbol: str) -> Decimal:
        """Get market value of holding for specific symbol."""
        quantity = self._holdings.get(symbol, Decimal('0'))
        if symbol in self._securities:
            return quantity * self._securities[symbol].price
        return Decimal('0')
    
    def get_average_cost(self, symbol: str) -> Decimal:
        """Get average cost for specific symbol."""
        return self._average_costs.get(symbol, Decimal('0'))
    
    def update_holding(self, symbol: str, quantity_change: Decimal, price: Decimal) -> bool:
        """
        Update holdings for a symbol.
        Returns True if successful, False if insufficient funds/shares.
        """
        current_quantity = self._holdings.get(symbol, Decimal('0'))
        new_quantity = current_quantity + quantity_change
        
        # Check if we have enough shares to sell
        if new_quantity < 0:
            return False
        
        # Check if we have enough cash to buy
        if quantity_change > 0:
            cost = quantity_change * price
            if cost > self._cash:
                return False
            self._cash -= cost
        else:  # Selling
            proceeds = abs(quantity_change) * price
            self._cash += proceeds
        
        # Update holdings and average cost
        if new_quantity == 0:
            self._holdings[symbol] = Decimal('0')
            self._average_costs[symbol] = Decimal('0')
        else:
            # Update average cost only when buying
            if quantity_change > 0:
                total_cost = (current_quantity * self._average_costs.get(symbol, Decimal('0'))) + (quantity_change * price)
                self._average_costs[symbol] = total_cost / new_quantity
            
            self._holdings[symbol] = new_quantity
        
        # Record transaction
        self._transactions.append({
            'timestamp': datetime.now(),
            'symbol': symbol,
            'quantity': quantity_change,
            'price': price,
            'type': 'BUY' if quantity_change > 0 else 'SELL'
        })
        
        self._last_update = datetime.now()
        return True
    
    def get_portfolio_holdings(self) -> MockPortfolioHoldings:
        """Get portfolio holdings summary."""
        return MockPortfolioHoldings(
            total_portfolio_value=self.total_portfolio_value,
            cash=self._cash,
            holdings_value=self.holdings_value,
            margin_used=Decimal('0'),  # Simplified - no margin trading
            margin_remaining=Decimal('0'),
            unsettled_cash=Decimal('0')
        )
    
    def calculate_statistics(self) -> MockPortfolioStatistics:
        """Calculate portfolio performance statistics."""
        current_value = self.total_portfolio_value
        total_return = (current_value - self._initial_cash) / self._initial_cash * Decimal('100')
        
        # Update high water mark and drawdown
        if current_value > self._high_water_mark:
            self._high_water_mark = current_value
        
        current_drawdown = (self._high_water_mark - current_value) / self._high_water_mark * Decimal('100')
        if current_drawdown > self._max_drawdown:
            self._max_drawdown = current_drawdown
        
        # Count winning vs losing trades
        winning_trades = 0
        losing_trades = 0
        
        for transaction in self._transactions:
            if transaction['type'] == 'SELL':
                symbol = transaction['symbol']
                avg_cost = self._average_costs.get(symbol, Decimal('0'))
                if transaction['price'] > avg_cost:
                    winning_trades += 1
                else:
                    losing_trades += 1
        
        return MockPortfolioStatistics(
            total_performance=total_return,
            total_return=total_return,
            annual_return=Decimal('0'),  # Simplified
            sharpe_ratio=Decimal('0'),   # Simplified
            max_drawdown=self._max_drawdown,
            volatility=Decimal('0'),     # Simplified
            trades_count=len(self._transactions),
            winning_trades=winning_trades,
            losing_trades=losing_trades
        )
    
    def get_transaction_history(self) -> List[Dict]:
        """Get all transaction history."""
        return self._transactions.copy()
    
    def reset(self, initial_cash: Optional[Decimal] = None) -> None:
        """Reset portfolio to initial state."""
        if initial_cash is not None:
            self._initial_cash = initial_cash
        
        self._cash = self._initial_cash
        self._holdings.clear()
        self._average_costs.clear()
        self._transactions.clear()
        self._portfolio_value_history = [self._initial_cash]
        self._high_water_mark = self._initial_cash
        self._max_drawdown = Decimal('0')
        self._last_update = datetime.now()
    
    def __getitem__(self, symbol: str) -> Optional['MockSecurity']:
        """Allow portfolio[symbol] access."""
        return self._securities.get(symbol)
    
    def __contains__(self, symbol: str) -> bool:
        """Allow 'symbol in portfolio' checks."""
        return symbol in self._securities
    
    def __str__(self) -> str:
        return f"MockPortfolio(value=${self.total_portfolio_value}, cash=${self._cash}, securities={len(self._securities)})"
    
    def __repr__(self) -> str:
        return (f"MockPortfolio(total_value={self.total_portfolio_value}, "
                f"cash={self._cash}, holdings={len(self._holdings)})")