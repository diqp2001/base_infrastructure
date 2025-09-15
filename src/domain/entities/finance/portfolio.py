"""
Portfolio domain entity following DDD principles.
Pure domain logic without external dependencies.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional, Any
from enum import Enum

from .financial_assets.security import Symbol, Security, MarketData


class PortfolioType(Enum):
    """Portfolio types."""
    STANDARD = "STANDARD"
    RETIREMENT = "RETIREMENT"
    BACKTEST = "BACKTEST"
    PAPER_TRADING = "PAPER_TRADING"


class RiskTolerance(Enum):
    """Risk tolerance levels."""
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"


@dataclass
class SecurityHoldings:
    """Holdings for a specific security in a portfolio."""
    symbol: Symbol
    quantity: Decimal
    average_cost: Decimal
    market_value: Decimal = field(default_factory=lambda: Decimal('0'))
    unrealized_pnl: Decimal = field(default_factory=lambda: Decimal('0'))
    realized_pnl: Decimal = field(default_factory=lambda: Decimal('0'))
    holdings_value: Decimal = field(default_factory=lambda: Decimal('0'))
    
    def __post_init__(self):
        """Ensure decimal precision."""
        self.quantity = Decimal(str(self.quantity))
        self.average_cost = Decimal(str(self.average_cost))
        self.market_value = Decimal(str(self.market_value))
        self.unrealized_pnl = Decimal(str(self.unrealized_pnl))
        self.realized_pnl = Decimal(str(self.realized_pnl))
        self.holdings_value = Decimal(str(self.holdings_value))
    
    def update_market_value(self, current_price: Decimal) -> None:
        """Update market value and unrealized P&L based on current price."""
        current_price = Decimal(str(current_price))
        self.market_value = self.quantity * current_price
        self.unrealized_pnl = (current_price - self.average_cost) * self.quantity


@dataclass
class PortfolioHoldings:
    """Complete holdings snapshot for a portfolio."""
    holdings: Dict[Symbol, SecurityHoldings] = field(default_factory=dict)
    cash_balance: Decimal = field(default_factory=lambda: Decimal('0'))
    total_value: Decimal = field(default_factory=lambda: Decimal('0'))
    
    def __post_init__(self):
        """Ensure decimal precision."""
        self.cash_balance = Decimal(str(self.cash_balance))
        self.total_value = Decimal(str(self.total_value))
    
    def add_holding(self, holding: SecurityHoldings) -> None:
        """Add or update a security holding."""
        self.holdings[holding.symbol] = holding
        self._recalculate_total_value()
    
    def remove_holding(self, symbol: Symbol) -> bool:
        """Remove a security holding."""
        if symbol in self.holdings:
            del self.holdings[symbol]
            self._recalculate_total_value()
            return True
        return False
    
    def get_holding(self, symbol: Symbol) -> Optional[SecurityHoldings]:
        """Get holding for a specific symbol."""
        return self.holdings.get(symbol)
    
    def _recalculate_total_value(self) -> None:
        """Recalculate total portfolio value."""
        holdings_value = sum(holding.market_value for holding in self.holdings.values())
        self.total_value = self.cash_balance + holdings_value
    
    @property
    def holdings_value(self) -> Decimal:
        """Get total value of all holdings."""
        return sum(holding.market_value for holding in self.holdings.values())
    
    @property
    def total_unrealized_pnl(self) -> Decimal:
        """Get total unrealized P&L."""
        return sum(holding.unrealized_pnl for holding in self.holdings.values())
    
    @property
    def total_realized_pnl(self) -> Decimal:
        """Get total realized P&L."""
        return sum(holding.realized_pnl for holding in self.holdings.values())


@dataclass
class PortfolioStatistics:
    """Performance and risk statistics for a portfolio."""
    total_return: Decimal = field(default_factory=lambda: Decimal('0'))
    total_return_percent: Decimal = field(default_factory=lambda: Decimal('0'))
    max_drawdown: Decimal = field(default_factory=lambda: Decimal('0'))
    high_water_mark: Decimal = field(default_factory=lambda: Decimal('0'))
    volatility: Decimal = field(default_factory=lambda: Decimal('0'))
    sharpe_ratio: Decimal = field(default_factory=lambda: Decimal('0'))
    beta: Decimal = field(default_factory=lambda: Decimal('0'))
    alpha: Decimal = field(default_factory=lambda: Decimal('0'))
    var_95: Decimal = field(default_factory=lambda: Decimal('0'))
    tracking_error: Decimal = field(default_factory=lambda: Decimal('0'))
    win_rate: Decimal = field(default_factory=lambda: Decimal('0'))
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    def __post_init__(self):
        """Ensure decimal precision."""
        self.total_return = Decimal(str(self.total_return))
        self.total_return_percent = Decimal(str(self.total_return_percent))
        self.max_drawdown = Decimal(str(self.max_drawdown))
        self.high_water_mark = Decimal(str(self.high_water_mark))
        self.volatility = Decimal(str(self.volatility))
        self.sharpe_ratio = Decimal(str(self.sharpe_ratio))
        self.beta = Decimal(str(self.beta))
        self.alpha = Decimal(str(self.alpha))
        self.var_95 = Decimal(str(self.var_95))
        self.tracking_error = Decimal(str(self.tracking_error))
        self.win_rate = Decimal(str(self.win_rate))
    
    def update_trade_statistics(self, is_winning: bool) -> None:
        """Update trade statistics."""
        self.total_trades += 1
        if is_winning:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        # Recalculate win rate
        if self.total_trades > 0:
            self.win_rate = Decimal(self.winning_trades) / Decimal(self.total_trades) * 100


@dataclass
class Portfolio:
    """Main portfolio domain entity."""
    name: str
    portfolio_type: PortfolioType = PortfolioType.STANDARD
    initial_cash: Decimal = field(default_factory=lambda: Decimal('100000'))
    currency: str = "USD"
    inception_date: Optional[date] = None
    owner_id: Optional[int] = None
    manager_id: Optional[int] = None
    account_number: Optional[str] = None
    
    # Core portfolio data
    holdings: PortfolioHoldings = field(default_factory=PortfolioHoldings)
    statistics: PortfolioStatistics = field(default_factory=PortfolioStatistics)
    
    # Configuration
    risk_tolerance: RiskTolerance = RiskTolerance.MODERATE
    investment_strategy: Optional[str] = None
    rebalancing_frequency: Optional[str] = None
    benchmark_id: Optional[int] = None
    
    # Status
    is_active: bool = True
    is_paper_trading: bool = False
    
    # Fees
    management_fee_rate: Decimal = field(default_factory=lambda: Decimal('0'))
    performance_fee_rate: Decimal = field(default_factory=lambda: Decimal('0'))
    total_fees_paid: Decimal = field(default_factory=lambda: Decimal('0'))
    
    # Timestamps
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_rebalance_date: Optional[date] = None
    last_valuation_date: Optional[datetime] = None
    
    # Backtest specific
    backtest_id: Optional[str] = None
    backtest_start_date: Optional[datetime] = None
    backtest_end_date: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize portfolio."""
        self.initial_cash = Decimal(str(self.initial_cash))
        self.management_fee_rate = Decimal(str(self.management_fee_rate))
        self.performance_fee_rate = Decimal(str(self.performance_fee_rate))
        self.total_fees_paid = Decimal(str(self.total_fees_paid))
        
        # Set inception date if not provided
        if self.inception_date is None:
            self.inception_date = date.today()
        
        # Initialize cash balance if holdings is new
        if self.holdings.cash_balance == 0:
            self.holdings.cash_balance = self.initial_cash
    
    @property
    def current_value(self) -> Decimal:
        """Get current portfolio value."""
        return self.holdings.total_value
    
    @property
    def total_portfolio_value(self) -> Decimal:
        """Get total portfolio value (alias for current_value for compatibility)."""
        return self.current_value
    
    @property
    def cash_balance(self) -> Decimal:
        """Get current cash balance."""
        return self.holdings.cash_balance
    
    @property
    def invested_amount(self) -> Decimal:
        """Get total invested amount."""
        return self.holdings.holdings_value
    
    @property
    def total_return(self) -> Decimal:
        """Get total return."""
        return self.current_value - self.initial_cash
    
    @property
    def total_return_percent(self) -> Decimal:
        """Get total return percentage."""
        if self.initial_cash == 0:
            return Decimal('0')
        return (self.total_return / self.initial_cash) * 100
    
    def add_security_holding(self, holding: SecurityHoldings) -> None:
        """Add or update a security holding."""
        self.holdings.add_holding(holding)
        self._update_statistics()
    
    def remove_security_holding(self, symbol: Symbol) -> bool:
        """Remove a security holding."""
        result = self.holdings.remove_holding(symbol)
        if result:
            self._update_statistics()
        return result
    
    def get_security_holding(self, symbol: Symbol) -> Optional[SecurityHoldings]:
        """Get holding for a specific symbol."""
        return self.holdings.get_holding(symbol)
    
    def update_market_data(self, symbol: Symbol, market_data: MarketData) -> None:
        """Update portfolio with new market data."""
        holding = self.get_security_holding(symbol)
        if holding:
            holding.update_market_value(market_data.price)
            self._update_statistics()
            self.last_valuation_date = market_data.timestamp
    
    def execute_trade(self, symbol: Symbol, quantity: Decimal, price: Decimal) -> bool:
        """Execute a trade (buy/sell)."""
        quantity = Decimal(str(quantity))
        price = Decimal(str(price))
        trade_value = Decimal(str(abs(quantity))) * price
        
        try:
            if quantity > 0:  # Buy
                if self.cash_balance < trade_value:
                    return False  # Insufficient funds
                
                # Update or create holding
                existing_holding = self.get_security_holding(symbol)
                if existing_holding:
                    # Update existing holding with new average cost
                    total_quantity = existing_holding.quantity + quantity
                    total_cost = (existing_holding.quantity * existing_holding.average_cost) + trade_value
                    new_avg_cost = total_cost / total_quantity if total_quantity > 0 else price
                    
                    existing_holding.quantity = total_quantity
                    existing_holding.average_cost = new_avg_cost
                    existing_holding.update_market_value(price)
                else:
                    # Create new holding
                    new_holding = SecurityHoldings(
                        symbol=symbol,
                        quantity=quantity,
                        average_cost=price,
                        market_value=trade_value
                    )
                    self.add_security_holding(new_holding)
                
                # Update cash balance
                self.holdings.cash_balance -= trade_value
                
            else:  # Sell
                holding = self.get_security_holding(symbol)
                if not holding or holding.quantity < abs(quantity):
                    return False  # Insufficient shares
                
                # Calculate realized P&L
                realized_pnl = (price - holding.average_cost) * Decimal(str(abs(quantity)))
                holding.realized_pnl += realized_pnl
                
                # Update holding quantity
                holding.quantity -= Decimal(str(abs(quantity)))
                if holding.quantity == 0:
                    self.remove_security_holding(symbol)
                else:
                    holding.update_market_value(price)
                
                # Update cash balance
                self.holdings.cash_balance += trade_value
            
            # Update statistics
            self._update_statistics()
            return True
            
        except Exception:
            return False
    
    def _update_statistics(self) -> None:
        """Update portfolio statistics."""
        # Update basic return metrics
        self.statistics.total_return = self.total_return
        self.statistics.total_return_percent = self.total_return_percent
        
        # Update holdings value
        self.holdings._recalculate_total_value()
        
        # Update high water mark
        if self.current_value > self.statistics.high_water_mark:
            self.statistics.high_water_mark = self.current_value
        
        # Calculate drawdown
        if self.statistics.high_water_mark > 0:
            drawdown = (self.statistics.high_water_mark - self.current_value) / self.statistics.high_water_mark
            if drawdown > self.statistics.max_drawdown:
                self.statistics.max_drawdown = drawdown
    
    def get_asset_allocation(self) -> Dict[Symbol, Decimal]:
        """Get asset allocation percentages."""
        allocation = {}
        if self.current_value == 0:
            return allocation
        
        for symbol, holding in self.holdings.holdings.items():
            allocation[symbol] = (holding.market_value / self.current_value) * 100
        
        return allocation
    
    def __str__(self) -> str:
        return f"Portfolio({self.name}, {self.currency}{self.current_value})"
    
    def __getitem__(self, symbol) -> Optional[SecurityHoldings]:
        """Make Portfolio subscriptable to access holdings by symbol."""
        # Handle both Symbol objects and string tickers
        if isinstance(symbol, str):
            # Find holding by ticker string
            for sym, holding in self.holdings.holdings.items():
                if hasattr(sym, 'ticker') and sym.ticker == symbol:
                    return holding
                elif str(sym) == symbol:
                    return holding
            # If no holding found, return empty holding for compatibility
            from .financial_assets.security import Symbol, SecurityType
            symbol_obj = Symbol(ticker=symbol, exchange="USA", security_type=SecurityType.EQUITY)
            return SecurityHoldings(
                symbol=symbol_obj,
                quantity=Decimal('0'),
                average_cost=Decimal('0'),
                market_value=Decimal('0')
            )
        else:
            # Handle Symbol objects directly
            return self.holdings.get_holding(symbol)
    
    def __setitem__(self, symbol, holding: SecurityHoldings) -> None:
        """Allow setting holdings via subscript notation."""
        self.add_security_holding(holding)
    
    def __contains__(self, symbol) -> bool:
        """Check if portfolio contains a holding for the given symbol."""
        if isinstance(symbol, str):
            return any(
                (hasattr(sym, 'ticker') and sym.ticker == symbol) or
                str(sym) == symbol
                for sym in self.holdings.holdings.keys()
            )
        else:
            return symbol in self.holdings.holdings

    def __repr__(self) -> str:
        return (f"Portfolio(name='{self.name}', value={self.current_value}, "
                f"type={self.portfolio_type.value}, cash={self.cash_balance})")