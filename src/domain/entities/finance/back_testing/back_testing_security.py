"""
Domain entities for securities system.
Pure domain entities following DDD principles.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Any

from src.domain.entities.finance.financial_assets import security

from .back_testing_data_types import BackTestingBaseData
from .financial_assets.symbol import Symbol, SymbolProperties
from .enums import SecurityType
from ..financial_assets.security import Security

@dataclass
class SecurityHolding:
    """Tracks portfolio holdings for a security."""
    symbol: Symbol
    quantity: int = 0
    average_price: Decimal = field(default_factory=lambda: Decimal('0'))
    
    def __post_init__(self):
        """Ensure decimal precision."""
        self.average_price = Decimal(str(self.average_price))
    
    @property
    def market_value(self) -> Decimal:
        """Calculate market value (requires current price)."""
        # This would typically use current market price
        return self.average_price * self.quantity
    
    @property
    def cost_basis(self) -> Decimal:
        """Calculate cost basis."""
        return self.average_price * abs(self.quantity)
    
    @property
    def unrealized_profit(self) -> Decimal:
        """Calculate unrealized profit (requires current price)."""
        # This would typically use current market price - cost basis
        return Decimal('0')  # Simplified for domain entity
    
    @property
    def unrealized_profit_percent(self) -> Decimal:
        """Calculate unrealized profit percentage."""
        if self.cost_basis == 0:
            return Decimal('0')
        return (self.unrealized_profit / self.cost_basis) * 100
    
    def add_shares(self, quantity: int, price: Decimal):
        """Add shares to holding."""
        price = Decimal(str(price))
        if self.quantity == 0:
            self.average_price = price
        else:
            total_cost = (self.average_price * self.quantity) + (price * quantity)
            self.quantity += quantity
            if self.quantity != 0:
                self.average_price = total_cost / self.quantity
    
    def remove_shares(self, quantity: int) -> Decimal:
        """Remove shares from holding. Returns realized P&L."""
        if quantity > self.quantity:
            raise ValueError("Cannot remove more shares than held")
        
        self.quantity -= quantity
        if self.quantity == 0:
            realized_pnl = Decimal('0')  # Would calculate with sell price
            self.average_price = Decimal('0')
        else:
            realized_pnl = Decimal('0')  # Simplified
        
        return realized_pnl


class SecurityBackTesting(Security):
    """Main security class representing a tradeable instrument."""
    
    def __init__(self, symbol: Symbol, symbol_properties: SymbolProperties = None,
                 resolution: str = "Minute", leverage: Decimal = Decimal('1'),
                 fill_data_forward: bool = True):
        self.symbol = symbol
        self.symbol_properties = symbol_properties or SymbolProperties.get_default(symbol.security_type)
        self.resolution = resolution
        self.leverage = Decimal(str(leverage))
        self.fill_data_forward = fill_data_forward
        
        # Market data
        self._market_price: Optional[Decimal] = None
        self._bid_price: Optional[Decimal] = None
        self._ask_price: Optional[Decimal] = None
        self._last_data: Optional[BackTestingBaseData] = None
        self._volume: int = 0
        
        # Caching and metadata
        self._data_cache: List[BackTestingBaseData] = []
        self._last_update_time: Optional[datetime] = None
    
    @property
    def market_price(self) -> Decimal:
        """Get current market price."""
        return self._market_price or Decimal('0')
    
    @property
    def bid_price(self) -> Decimal:
        """Get current bid price."""
        return self._bid_price or self.market_price
    
    @property
    def ask_price(self) -> Decimal:
        """Get current ask price."""
        return self._ask_price or self.market_price
    
    @property
    def volume(self) -> int:
        """Get current volume."""
        return self._volume
    
    def update_market_price(self, price: Decimal, volume: int = 0, 
                           time: datetime = None):
        """Update market price."""
        self._market_price = Decimal(str(price))
        self._volume = volume
        self._last_update_time = time or datetime.now(timezone.utc)
    
    def update_data(self, data: BackTestingBaseData):
        """Update with new market data."""
        self._last_data = data
        self._market_price = data.price
        self._last_update_time = data.time
        
        # Keep limited cache
        self._data_cache.append(data)
        if len(self._data_cache) > 1000:  # Limit cache size
            self._data_cache = self._data_cache[-1000:]
    
    def get_last_data(self) -> Optional[BackTestingBaseData]:
        """Get last data point."""
        return self._last_data
    
    def __str__(self) -> str:
        return f"Security({self.symbol}, {self.market_price})"


class Securities:
    """Dictionary-like collection for managing multiple securities."""
    
    def __init__(self):
        self._securities: Dict[Symbol, Security] = {}
    
    def add(self, security: Security):
        """Add a security to the collection."""
        self._securities[security.symbol] = security
    
    def remove(self, symbol: Symbol) -> bool:
        """Remove a security from the collection."""
        if symbol in self._securities:
            del self._securities[symbol]
            return True
        return False
    
    def get(self, symbol: Symbol) -> Optional[Security]:
        """Get a security by symbol."""
        return self._securities.get(symbol)
    
    def contains(self, symbol: Symbol) -> bool:
        """Check if collection contains a symbol."""
        return symbol in self._securities
    
    def keys(self) -> List[Symbol]:
        """Get all symbols."""
        return list(self._securities.keys())
    
    def values(self) -> List[Security]:
        """Get all securities."""
        return list(self._securities.values())
    
    def items(self) -> List[tuple]:
        """Get all symbol-security pairs."""
        return list(self._securities.items())
    
    def __len__(self) -> int:
        return len(self._securities)
    
    def __getitem__(self, symbol: Symbol) -> Security:
        return self._securities[symbol]
    
    def __setitem__(self, symbol: Symbol, security: Security):
        self._securities[symbol] = security
    
    def __contains__(self, symbol: Symbol) -> bool:
        return symbol in self._securities

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
class SecurityPortfolioManager:
    """Manages portfolio holdings and cash."""
    cash: Decimal = field(default_factory=lambda: Decimal('100000'))  # Default $100k
    holdings: Dict[Symbol, SecurityHolding] = field(default_factory=dict)
    
    def __post_init__(self):
        """Ensure decimal precision."""
        self.cash = Decimal(str(self.cash))
    
    @property
    def total_portfolio_value(self) -> Decimal:
        """Calculate total portfolio value."""
        holdings_value = sum(holding.market_value for holding in self.holdings.values())
        return self.cash + holdings_value
    
    @property
    def total_unrealized_profit(self) -> Decimal:
        """Calculate total unrealized profit."""
        return sum(holding.unrealized_profit for holding in self.holdings.values())
    
    @property
    def net_profit(self) -> Decimal:
        """Calculate net profit."""
        # This would include realized + unrealized profits
        return self.total_unrealized_profit  # Simplified
    
    @property
    def invested(self) -> Decimal:
        """Calculate total invested amount."""
        return sum(holding.cost_basis for holding in self.holdings.values())
    
    def get_holding(self, symbol: Symbol) -> Optional[SecurityHolding]:
        """Get holding for a symbol."""
        return self.holdings.get(symbol)
    
    def add_transaction(self, symbol: Symbol, quantity: int, price: Decimal):
        """Add a transaction (buy/sell)."""
        price = Decimal(str(price))
        transaction_value = price * abs(quantity)
        
        if quantity > 0:  # Buy
            if self.cash < transaction_value:
                raise ValueError("Insufficient cash for purchase")
            
            if symbol not in self.holdings:
                self.holdings[symbol] = SecurityHolding(symbol)
            
            self.holdings[symbol].add_shares(quantity, price)
            self.cash -= transaction_value
            
        else:  # Sell
            if symbol not in self.holdings:
                raise ValueError("No holdings to sell")
            
            holding = self.holdings[symbol]
            if abs(quantity) > holding.quantity:
                raise ValueError("Insufficient shares to sell")
            
            realized_pnl = holding.remove_shares(abs(quantity))
            self.cash += transaction_value + realized_pnl
            
            # Remove holding if quantity is zero
            if holding.quantity == 0:
                del self.holdings[symbol]
    
    def get_holdings(self) -> List[SecurityHolding]:
        """Get all holdings."""
        return list(self.holdings.values())

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
class Portfolio:
    """High-level wrapper for portfolio management."""
    
    def __init__(self, starting_cash: Decimal = Decimal('100000')):
        self._manager = SecurityPortfolioManager(cash=starting_cash)
    
    @property
    def cash(self) -> Decimal:
        """Get current cash."""
        return self._manager.cash
    
    @property
    def total_portfolio_value(self) -> Decimal:
        """Get total portfolio value."""
        return self._manager.total_portfolio_value
    
    @property
    def total_unrealized_profit(self) -> Decimal:
        """Get total unrealized profit."""
        return self._manager.total_unrealized_profit
    
    @property
    def net_profit(self) -> Decimal:
        """Get net profit."""
        return self._manager.net_profit
    
    @property
    def invested(self) -> Decimal:
        """Get total invested."""
        return self._manager.invested
    
    def get_holding(self, symbol: Symbol) -> Optional[SecurityHolding]:
        """Get holding for symbol."""
        return self._manager.get_holding(symbol)
    
    def get_holdings(self) -> List[SecurityHolding]:
        """Get all holdings."""
        return self._manager.get_holdings()


@dataclass
class SecurityCache:
    """Caches recent security data."""
    symbol: Symbol
    last_data: Optional[BackTestingBaseData] = None
    bid_price: Optional[Decimal] = None
    ask_price: Optional[Decimal] = None
    bid_size: int = 0
    ask_size: int = 0
    open_interest: int = 0
    
    def store_data(self, data: BackTestingBaseData):
        """Store data in cache."""
        self.last_data = data
    
    def clear(self):
        """Clear cached data."""
        self.last_data = None
        self.bid_price = None
        self.ask_price = None
        self.bid_size = 0
        self.ask_size = 0
        self.open_interest = 0


@dataclass
class SecurityChanges:
    """Tracks security additions/removals."""
    added_securities: List[Security] = field(default_factory=list)
    removed_securities: List[Security] = field(default_factory=list)
    
    def add_security(self, security: Security):
        """Add a security to the added list."""
        self.added_securities.append(security)
    
    def remove_security(self, security: Security):
        """Add a security to the removed list."""
        self.removed_securities.append(security)
    
    @property
    def count(self) -> int:
        """Get total number of changes."""
        return len(self.added_securities) + len(self.removed_securities)