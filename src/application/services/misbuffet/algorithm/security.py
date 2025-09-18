from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from decimal import Decimal
from collections import defaultdict

from .symbol import Symbol, SymbolProperties
from .enums import SecurityType, Resolution, DataNormalizationMode, LogLevel
from .data_handlers import BaseData, TradeBar, QuoteBar, Tick

# Import domain entities for proper inheritance
from domain.entities.finance.portfolio import SecurityHoldings as DomainSecurityHoldings
from domain.entities.finance.financial_assets.security import Security as DomainSecurity
from decimal import Decimal


@dataclass
class SecurityHolding(DomainSecurityHoldings):
    """
    Algorithm framework holding extending domain SecurityHoldings.
    Provides QuantConnect-style API with float convenience methods while maintaining domain precision.
    """
    # Additional algorithm-specific fields
    market_price: float = field(default=0.0, init=False)
    total_fees: float = field(default=0.0, init=False)
    _transactions: List[Dict[str, Any]] = field(default_factory=list, init=False)

    def __init__(self, symbol: Symbol, quantity: int = 0, average_price: float = 0.0):
        """Initialize SecurityHolding with domain model compatibility."""
        # Convert to Decimal for domain layer
        quantity_decimal = Decimal(str(quantity))
        average_cost_decimal = Decimal(str(average_price))

        # Initialize domain SecurityHoldings (uses Decimal fields)
        super().__init__(
            symbol=symbol,
            quantity=quantity_decimal,
            average_cost=average_cost_decimal,
            market_value=Decimal("0"),
            unrealized_pnl=Decimal("0"),
            realized_pnl=Decimal("0"),
            holdings_value=Decimal("0"),
        )

        # Set algorithm-specific fields
        object.__setattr__(self, "market_price", float(average_price))
        object.__setattr__(self, "total_fees", 0.0)
        object.__setattr__(self, "_transactions", [])

    # ---------------- Convenience float views ----------------

    @property
    def quantity_float(self) -> int:
        return int(self.quantity)

    @property
    def average_price_float(self) -> float:
        return float(self.average_cost)

    @property
    def market_value_float(self) -> float:
        return float(self.market_value)

    @property
    def unrealized_pnl_float(self) -> float:
        return float(self.unrealized_pnl)

    # ---------------- Algorithm-like API ----------------

    @property
    def cost_basis(self) -> float:
        return float(self.quantity * self.average_cost)

    @property
    def unrealized_profit_loss(self) -> float:
        if self.quantity == 0:
            return 0.0
        return (self.market_price - self.average_price_float) * self.quantity_float

    @property
    def unrealized_profit_loss_percent(self) -> float:
        if self.average_price_float == 0:
            return 0.0
        return (self.market_price - self.average_price_float) / self.average_price_float

    @property
    def total_profit_loss(self) -> float:
        return float(self.realized_pnl) + self.unrealized_profit_loss

    @property
    def is_long(self) -> bool:
        return self.quantity > 0

    @property
    def is_short(self) -> bool:
        return self.quantity < 0

    @property
    def is_invested(self) -> bool:
        return self.quantity != 0

    # ---------------- Transaction handling ----------------

    def add_transaction(self, quantity: int, price: float, fees: float = 0.0, timestamp: datetime = None):
        timestamp = timestamp or datetime.now()

        # Record transaction
        transaction = {
            "timestamp": timestamp,
            "quantity": quantity,
            "price": price,
            "fees": fees,
            "type": "buy" if quantity > 0 else "sell",
        }
        self._transactions.append(transaction)

        # Update fees
        self.total_fees += fees

        # TODO: update realized_pnl, quantity, and average_cost safely using Decimal

    def update_market_price(self, price: float):
        self.market_price = price
        self.unrealized_pnl = Decimal(str(self.unrealized_profit_loss))

    def set_holdings(self, quantity: int, average_price: float):
        """
        Update the holding's quantity, average cost, market value, and algorithm fields.
        """
        quantity_decimal = Decimal(str(quantity))
        average_cost_decimal = Decimal(str(average_price))

        # Update domain fields
        object.__setattr__(self, 'quantity', quantity_decimal)
        object.__setattr__(self, 'average_cost', average_cost_decimal)
        object.__setattr__(self, 'market_value', quantity_decimal * average_cost_decimal)
        object.__setattr__(self, 'holdings_value', quantity_decimal * average_cost_decimal)
        object.__setattr__(self, 'unrealized_pnl', Decimal('0.0'))  # Reset or recalc if needed

        # Update algorithm convenience fields
        self.market_price = float(average_price)


class Security(DomainSecurity):
    """
    Algorithm framework security extending domain Security.
    Provides QuantConnect-style API while maintaining domain model integrity.
    """
    
    def __init__(self, symbol: Symbol, resolution: Resolution = Resolution.MINUTE, 
                 leverage: float = 1.0, fill_data_forward: bool = True, 
                 extended_market_hours: bool = False):
        """Initialize Security with algorithm-specific features."""
        # Initialize domain Security
        super().__init__(symbol)
        
        # Algorithm-specific fields
        self.properties = SymbolProperties(symbol)
        self.resolution = resolution
        self.leverage = leverage
        self.fill_data_forward = fill_data_forward
        self.extended_market_hours = extended_market_hours
        self.margin_model: Optional[str] = None
        
        # Market data (algorithm convenience fields)
        self.open: float = 0.0
        self.high: float = 0.0 
        self.low: float = 0.0
        self.close: float = 0.0
        self.volume: int = 0
        self.bid_price: float = 0.0
        self.ask_price: float = 0.0
        self.bid_size: int = 0
        self.ask_size: int = 0
        
        # Historical data cache
        self._price_history: List[BaseData] = []
        self._last_data: Optional[BaseData] = None
    
    @property
    def has_data(self) -> bool:
        """Returns True if security has current market data"""
        return float(self.price) > 0.0 or self._last_data is not None
    
    @property
    def market_price(self) -> float:
        """Returns the current market price"""
        return float(self.price) or self.close
    
    @property
    def price(self) -> float:
        """Get current price as float for algorithm compatibility"""
        return float(super().price)
    
    @property
    def spread(self) -> float:
        """Returns the bid-ask spread"""
        if self.bid_price > 0 and self.ask_price > 0:
            return self.ask_price - self.bid_price
        return 0.0
    
    def update(self, data: BaseData):
        """Updates the security with new market data"""
        self._last_data = data
        self.price = data.price
        
        if isinstance(data, TradeBar):
            self.open = data.open
            self.high = data.high
            self.low = data.low
            self.close = data.close
            self.volume = data.volume
        elif isinstance(data, QuoteBar):
            self.bid_price = data.bid_close
            self.ask_price = data.ask_close
            self.bid_size = data.bid_size
            self.ask_size = data.ask_size
        elif isinstance(data, Tick):
            if data.tick_type.value == "Trade":
                self.price = data.value
                self.volume += data.quantity
            elif data.tick_type.value == "Quote":
                self.bid_price = data.bid_price
                self.ask_price = data.ask_price
                self.bid_size = data.bid_size
                self.ask_size = data.ask_size
        
        # Store in history (keep last 1000 points)
        self._price_history.append(data)
        if len(self._price_history) > 1000:
            self._price_history.pop(0)
    
    def calculate_margin_requirement(self, quantity: Decimal) -> Decimal:
        """Calculate margin requirement for a given position size."""
        if self.properties and hasattr(self.properties, 'margin_requirement'):
            return abs(quantity) * Decimal(str(self.price)) * self.properties.margin_requirement
        return abs(quantity) * Decimal(str(self.price)) * Decimal('0.25')  # Default 25% margin
    
    def get_contract_multiplier(self) -> Decimal:
        """Get the contract multiplier for the security."""
        if self.properties and hasattr(self.properties, 'contract_multiplier'):
            return Decimal(str(self.properties.contract_multiplier))
        return Decimal('1')
    
    def get_last_data(self) -> Optional[BaseData]:
        """Returns the most recent data point"""
        return self._last_data
    
    def get_price_history(self, count: int = None) -> List[BaseData]:
        """Returns historical price data"""
        if count is None:
            return self._price_history.copy()
        return self._price_history[-count:] if count <= len(self._price_history) else self._price_history.copy()


class Securities(Dict[Symbol, Security]):
    """
    Collection of Security objects keyed by Symbol.
    Provides convenient access to securities and their data.
    """
    
    def __init__(self):
        super().__init__()
        self._symbol_lookup: Dict[str, Symbol] = {}
    
    def add(self, symbol: Symbol, resolution: Resolution = Resolution.MINUTE, 
            leverage: float = 1.0, fill_data_forward: bool = True, 
            extended_market_hours: bool = False) -> Security:
        """
        Adds a new security to the collection.
        """
        security = Security(
            symbol=symbol,
            resolution=resolution,
            leverage=leverage,
            fill_data_forward=fill_data_forward,
            extended_market_hours=extended_market_hours
        )
        
        self[symbol] = security
        self._symbol_lookup[symbol.value] = symbol
        return security
    
    def get_by_ticker(self, ticker: str) -> Optional[Security]:
        """Gets a security by ticker string"""
        symbol = self._symbol_lookup.get(ticker)
        return self.get(symbol) if symbol else None
    
    def contains_key(self, key: Union[Symbol, str]) -> bool:
        """Checks if security exists by Symbol or ticker string"""
        if isinstance(key, str):
            return key in self._symbol_lookup
        return key in self
    
    def update_prices(self, data_dict: Dict[Symbol, BaseData]):
        """Updates multiple securities with new data"""
        for symbol, data in data_dict.items():
            if symbol in self:
                self[symbol].update(data)


class SecurityPortfolioManager:
    """
    Manages the portfolio of securities, cash, and positions.
    This is the main portfolio interface exposed to algorithms.
    """
    
    def __init__(self, cash: float = 100000.0, fee_model: Optional[str] = None):
        self.cash: float = cash
        self.total_fees: float = 0.0
        self.fee_model = fee_model
        
        # Holdings tracking
        self._holdings: Dict[Symbol, SecurityHolding] = {}
        
        # Performance tracking
        self.total_portfolio_value: float = cash
        self.total_unrealized_profit_loss: float = 0.0
        self.total_profit_loss: float = 0.0
        
        # Statistics
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        
        # Value history for performance calculation
        self._value_history: List[Dict[str, Any]] = []
    
    @property
    def invested(self) -> bool:
        """Returns True if there are any open positions"""
        return any(holding.is_invested for holding in self._holdings.values())
    
    @property
    def cash_held(self) -> float:
        """Returns the amount of cash held"""
        return self.cash - self.unsettled_cash
    
    @property
    def unsettled_cash(self) -> float:
        """Returns the amount of unsettled cash (from recent trades)"""
        # Simplified - in practice this would track T+2 settlement
        return 0.0
    
    @property
    def total_holdings_value(self) -> float:
        """Returns the total market value of all holdings"""
        return sum(holding.market_value for holding in self._holdings.values())
    
    @property
    def total_unrealized_profit(self) -> float:
        """Returns total unrealized profit/loss"""
        return sum(holding.unrealized_profit_loss for holding in self._holdings.values())
    
    @property
    def total_portfolio_value_current(self) -> float:
        """Returns current total portfolio value"""
        return self.cash + float(self.total_holdings_value)
    
    @property
    def cash_balance(self) -> float:
        """Returns the cash balance (alias for cash property for compatibility)"""
        return self.cash
    
    def __getitem__(self, symbol: Union[Symbol, str]) -> SecurityHolding:
        """
        Gets a SecurityHolding for the given symbol.
        WARNING: This method creates empty holdings if they don't exist!
        For read-only access, use get_holding() instead.
        """
        if isinstance(symbol, str):
            # Try to find existing symbol
            for sym in self._holdings.keys():
                if sym.value == symbol:
                    symbol = sym
                    break
            else:
                # Create new symbol
                symbol = Symbol.create_equity(symbol)
        
        if symbol not in self._holdings:
            # NOTE: This creates an empty holding without transaction data
            # This should only be used when you intend to create a position
            self._holdings[symbol] = SecurityHolding(symbol)
        
        return self._holdings[symbol]
    
    def __contains__(self, symbol: Union[Symbol, str]) -> bool:
        """Checks if symbol has holdings"""
        if isinstance(symbol, str):
            return any(sym.value == symbol for sym in self._holdings.keys())
        return symbol in self._holdings
    
    def get_holding(self, symbol: Union[Symbol, str]) -> Optional[SecurityHolding]:
        """Gets holding for symbol, returns None if no holding exists"""
        if isinstance(symbol, str):
            for sym, holding in self._holdings.items():
                if sym.value == symbol:
                    return holding
            return None
        return self._holdings.get(symbol)
    
    def is_invested(self, symbol: Union[Symbol, str]) -> bool:
        """Returns True if invested in the given symbol"""
        holding = self.get_holding(symbol)
        return holding.is_invested if holding else False
    
    def process_fill(self, symbol: Symbol, quantity: int, price: float, fees: float = 0.0, 
                    timestamp: datetime = None):
        """
        Processes a trade fill and updates the portfolio.
        """
        holding = self[symbol]
        
        # Calculate transaction value
        transaction_value = abs(quantity) * price
        
        # Update cash (subtract for buys, add for sells)
        if quantity > 0:  # Buy
            self.cash -= transaction_value + fees
        else:  # Sell
            self.cash += transaction_value - fees
        
        # Update holding
        holding.add_transaction(quantity, price, fees, timestamp)
        
        # Update the market price to the transaction price (important for market_value calculation)
        holding.update_market_price(price)
        
        # Update statistics
        self.total_trades += 1
        self.total_fees += fees
        
        # Update portfolio value
        self.total_portfolio_value = self.total_portfolio_value_current
    
    def update_market_values(self, securities: Securities):
        """Updates market values of all holdings based on current security prices"""
        for symbol, holding in self._holdings.items():
            if symbol in securities:
                security = securities[symbol]
                holding.update_market_price(security.market_price)
        
        # Update total portfolio value
        self.total_portfolio_value = self.total_portfolio_value_current
        self.total_unrealized_profit_loss = self.total_unrealized_profit
    
    def get_positions(self) -> Dict[Symbol, SecurityHolding]:
        """Returns all current positions"""
        return {symbol: holding for symbol, holding in self._holdings.items() if holding.is_invested}
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Returns performance statistics"""
        return {
            'total_portfolio_value': self.total_portfolio_value,
            'cash': self.cash,
            'total_holdings_value': self.total_holdings_value,
            'total_unrealized_pnl': self.total_unrealized_profit_loss,
            'total_fees': self.total_fees,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.winning_trades / self.total_trades if self.total_trades > 0 else 0.0
        }


class Portfolio:
    """
    Legacy Portfolio class for backward compatibility.
    Wraps SecurityPortfolioManager with simplified interface.
    """
    
    def __init__(self, cash: float = 100000.0):
        self._manager = SecurityPortfolioManager(cash)
        self.securities = {}
    
    def is_invested(self, symbol: Union[Symbol, str]) -> bool:
        return self._manager.is_invested(symbol)
    
    def process_orders(self):
        """Legacy method - no-op for compatibility"""
        pass
    
    def __getitem__(self, symbol: Union[Symbol, str]) -> SecurityHolding:
        return self._manager[symbol]
    
    @property
    def cash(self) -> float:
        return self._manager.cash
    
    @property
    def total_portfolio_value(self) -> float:
        return self._manager.total_portfolio_value
