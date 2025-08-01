from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from decimal import Decimal
import uuid

from .symbol import Symbol, SymbolProperties
from .enums import (
    SecurityType, Resolution, OrderType, OrderStatus, OrderDirection,
    DataNormalizationMode, LogLevel
)
from .data_handlers import Slice, BaseData, TradeBar, QuoteBar, Tick
from .order import (
    Order, OrderTicket, OrderEvent, OrderFill, MarketOrder, LimitOrder,
    StopMarketOrder, StopLimitOrder, MarketOnOpenOrder, MarketOnCloseOrder,
    OrderBuilder, create_order
)
from .security import (
    Security, Securities, SecurityHolding, SecurityPortfolioManager, Portfolio
)
from .logging import AlgorithmLogger, LogLevel, log, debug, info, warning, error
from .scheduling import (
    ScheduleManager, DateRules, TimeRules, DayOfWeek, ScheduleFrequency
)
from .utils import (
    AlgorithmUtilities, PerformanceMetrics, set_runtime_parameters,
    set_warmup, set_cash, set_start_date, set_end_date, set_benchmark
)


class QCAlgorithm:
    """
    QCAlgorithm is the base class for all algorithms.
    This provides the core functionality needed to build trading algorithms,
    including data handling, order management, portfolio tracking, and scheduling.
    """
    
    def __init__(self):
        # Core algorithm properties
        self.start_date: Optional[datetime] = None
        self.end_date: Optional[datetime] = None
        self.time: datetime = datetime.now()
        self.utc_time: datetime = datetime.utcnow()
        
        # Securities and portfolio management
        self.securities = Securities()
        self.portfolio = SecurityPortfolioManager(cash=100000.0)
        
        # Order management
        self._order_tickets: Dict[str, OrderTicket] = {}
        self._orders: Dict[str, Order] = {}
        self._order_events: List[OrderEvent] = []
        
        # Scheduling
        self.schedule = ScheduleManager()
        
        # Logging
        self.logger = AlgorithmLogger(name=self.__class__.__name__)
        
        # Performance tracking
        self.performance = PerformanceMetrics()
        
        # Runtime settings
        self.benchmark: Optional[str] = None
        self.warmup_period: timedelta = timedelta(days=0)
        self.live_mode: bool = False
        
        # Data tracking
        self._current_slice: Optional[Slice] = None
        self._universe: List[Symbol] = []
        
        # Event handlers (can be overridden)
        self._initialized = False
        self._is_warming_up = False
    
    # ===========================================
    # Core Algorithm Lifecycle Methods
    # ===========================================
    
    def initialize(self):
        """
        Called once at the start of the algorithm to setup the initial state.
        This is where you should add securities, set parameters, and configure the algorithm.
        """
        pass
    
    def on_data(self, data: Slice):
        """
        Called when new data arrives. This is the main event handler for market data.
        
        Args:
            data: Slice containing all available market data for the current time
        """
        pass
    
    def on_order_event(self, order_event: OrderEvent):
        """
        Called when an order event occurs (fill, partial fill, cancellation, etc.)
        
        Args:
            order_event: The order event that occurred
        """
        pass
    
    def on_end_of_day(self, symbol: Symbol):
        """
        Called at the end of each trading day for each security.
        
        Args:
            symbol: The symbol for which the day ended
        """
        pass
    
    def on_end_of_algorithm(self):
        """
        Called when the algorithm finishes execution.
        Use this for cleanup and final calculations.
        """
        pass
    
    def on_securities_changed(self, changes: Dict[str, List[Security]]):
        """
        Called when the universe of securities changes.
        
        Args:
            changes: Dictionary with 'added' and 'removed' keys containing lists of securities
        """
        pass
    
    def on_margin_call(self, requests: List[Dict[str, Any]]):
        """
        Called when a margin call occurs.
        
        Args:
            requests: List of margin call requests
        """
        pass
    
    def on_assignment(self, assignment_event: Dict[str, Any]):
        """
        Called when an option assignment occurs.
        
        Args:
            assignment_event: Details about the assignment
        """
        pass
    
    # ===========================================
    # Security Management Methods
    # ===========================================
    
    def add_equity(self, ticker: str, resolution: Resolution = Resolution.MINUTE,
                   market: str = "USA", fill_data_forward: bool = True,
                   leverage: float = 1.0, extended_market_hours: bool = False) -> Security:
        """
        Add an equity security to the algorithm.
        
        Args:
            ticker: The ticker symbol (e.g., "AAPL")
            resolution: Data resolution
            market: Market designation
            fill_data_forward: Whether to fill missing data forward
            leverage: Leverage multiplier
            extended_market_hours: Whether to include extended hours data
            
        Returns:
            The Security object that was added
        """
        symbol = Symbol.create_equity(ticker, market)
        security = self.securities.add(
            symbol, resolution, leverage, fill_data_forward, extended_market_hours
        )
        
        self.debug(f"Added equity: {ticker} with {resolution.value} resolution")
        return security
    
    def add_forex(self, ticker: str, resolution: Resolution = Resolution.MINUTE,
                  market: str = "FXCM", fill_data_forward: bool = True,
                  leverage: float = 50.0) -> Security:
        """
        Add a forex pair to the algorithm.
        
        Args:
            ticker: The forex pair (e.g., "EURUSD")
            resolution: Data resolution
            market: Market designation
            fill_data_forward: Whether to fill missing data forward
            leverage: Leverage multiplier
            
        Returns:
            The Security object that was added
        """
        symbol = Symbol.create_forex(ticker, market)
        security = self.securities.add(symbol, resolution, leverage, fill_data_forward)
        
        self.debug(f"Added forex: {ticker} with {resolution.value} resolution")
        return security
    
    def add_crypto(self, ticker: str, resolution: Resolution = Resolution.MINUTE,
                   market: str = "Bitfinex", fill_data_forward: bool = True) -> Security:
        """
        Add a cryptocurrency to the algorithm.
        
        Args:
            ticker: The crypto pair (e.g., "BTCUSD")
            resolution: Data resolution
            market: Market designation
            fill_data_forward: Whether to fill missing data forward
            
        Returns:
            The Security object that was added
        """
        symbol = Symbol.create_crypto(ticker, market)
        security = self.securities.add(symbol, resolution, 1.0, fill_data_forward)
        
        self.debug(f"Added crypto: {ticker} with {resolution.value} resolution")
        return security
    
    def remove_security(self, symbol: Union[Symbol, str]):
        """
        Remove a security from the algorithm.
        
        Args:
            symbol: The symbol to remove
        """
        if isinstance(symbol, str):
            symbol = next((s for s in self.securities.keys() if s.value == symbol), None)
        
        if symbol and symbol in self.securities:
            del self.securities[symbol]
            self.debug(f"Removed security: {symbol}")
    
    # ===========================================
    # Order Management Methods
    # ===========================================
    
    def market_order(self, symbol: Union[Symbol, str], quantity: int, 
                    asynchronous: bool = False, tag: str = "") -> OrderTicket:
        """
        Submit a market order.
        
        Args:
            symbol: The symbol to trade
            quantity: Number of shares (positive for buy, negative for sell)
            asynchronous: Whether to submit asynchronously
            tag: Optional tag for the order
            
        Returns:
            OrderTicket for tracking the order
        """
        return self._submit_order(MarketOrder, symbol, quantity, tag=tag)
    
    def limit_order(self, symbol: Union[Symbol, str], quantity: int, limit_price: float,
                   tag: str = "") -> OrderTicket:
        """
        Submit a limit order.
        
        Args:
            symbol: The symbol to trade
            quantity: Number of shares (positive for buy, negative for sell)
            limit_price: The limit price
            tag: Optional tag for the order
            
        Returns:
            OrderTicket for tracking the order
        """
        return self._submit_order(LimitOrder, symbol, quantity, limit_price=limit_price, tag=tag)
    
    def stop_market_order(self, symbol: Union[Symbol, str], quantity: int, stop_price: float,
                         tag: str = "") -> OrderTicket:
        """
        Submit a stop market order.
        
        Args:
            symbol: The symbol to trade
            quantity: Number of shares (positive for buy, negative for sell)
            stop_price: The stop price
            tag: Optional tag for the order
            
        Returns:
            OrderTicket for tracking the order
        """
        return self._submit_order(StopMarketOrder, symbol, quantity, stop_price=stop_price, tag=tag)
    
    def stop_limit_order(self, symbol: Union[Symbol, str], quantity: int, 
                        stop_price: float, limit_price: float, tag: str = "") -> OrderTicket:
        """
        Submit a stop limit order.
        
        Args:
            symbol: The symbol to trade
            quantity: Number of shares (positive for buy, negative for sell)
            stop_price: The stop price
            limit_price: The limit price
            tag: Optional tag for the order
            
        Returns:
            OrderTicket for tracking the order
        """
        return self._submit_order(
            StopLimitOrder, symbol, quantity, 
            stop_price=stop_price, limit_price=limit_price, tag=tag
        )
    
    def market_on_open_order(self, symbol: Union[Symbol, str], quantity: int,
                            tag: str = "") -> OrderTicket:
        """
        Submit a market on open order.
        
        Args:
            symbol: The symbol to trade
            quantity: Number of shares (positive for buy, negative for sell)
            tag: Optional tag for the order
            
        Returns:
            OrderTicket for tracking the order
        """
        return self._submit_order(MarketOnOpenOrder, symbol, quantity, tag=tag)
    
    def market_on_close_order(self, symbol: Union[Symbol, str], quantity: int,
                             tag: str = "") -> OrderTicket:
        """
        Submit a market on close order.
        
        Args:
            symbol: The symbol to trade
            quantity: Number of shares (positive for buy, negative for sell)  
            tag: Optional tag for the order
            
        Returns:
            OrderTicket for tracking the order
        """
        return self._submit_order(MarketOnCloseOrder, symbol, quantity, tag=tag)
    
    def _submit_order(self, order_class, symbol: Union[Symbol, str], quantity: int, **kwargs) -> OrderTicket:
        """
        Internal method to submit orders.
        """
        # Convert string to Symbol if needed
        if isinstance(symbol, str):
            symbol = next((s for s in self.securities.keys() if s.value == symbol), None)
            if symbol is None:
                symbol = Symbol.create_equity(kwargs.get('symbol', str(symbol)))
        
        # Create the order
        direction = OrderDirection.BUY if quantity > 0 else OrderDirection.SELL
        order_kwargs = {
            'symbol': symbol,
            'quantity': quantity,
            'direction': direction,
            'time': self.time,
            **kwargs
        }
        
        order = order_class(**order_kwargs)
        
        # Create order ticket
        ticket = OrderTicket(
            order_id=order.id,
            symbol=symbol,
            quantity=quantity,
            order_type=order.order_type,
            tag=kwargs.get('tag', ''),
            time=self.time,
            limit_price=kwargs.get('limit_price'),
            stop_price=kwargs.get('stop_price')
        )
        
        # Store order and ticket
        self._orders[order.id] = order
        self._order_tickets[order.id] = ticket
        
        # Log the order
        self.debug(f"Submitted {order.order_type.value} order for {quantity} shares of {symbol}")
        
        # In a real implementation, this would be sent to a broker
        # For now, we'll immediately mark it as submitted
        ticket.status = OrderStatus.SUBMITTED
        
        return ticket
    
    def cancel_order(self, order_ticket: OrderTicket) -> bool:
        """
        Cancel an order.
        
        Args:
            order_ticket: The order ticket to cancel
            
        Returns:
            True if cancellation was successful
        """
        if order_ticket.order_id in self._order_tickets:
            ticket = self._order_tickets[order_ticket.order_id]
            success = ticket.cancel()
            if success:
                self.debug(f"Cancelled order {ticket.order_id}")
            return success
        return False
    
    def liquidate(self, symbol: Union[Symbol, str] = None, tag: str = "Liquidation") -> List[OrderTicket]:
        """
        Liquidate holdings. If no symbol is provided, liquidates all positions.
        
        Args:
            symbol: Specific symbol to liquidate (None for all)
            tag: Tag for liquidation orders
            
        Returns:
            List of order tickets for liquidation orders
        """
        tickets = []
        
        if symbol is None:
            # Liquidate all positions
            positions = self.portfolio.get_positions()
            for pos_symbol, holding in positions.items():
                if holding.is_invested:
                    ticket = self.market_order(pos_symbol, -holding.quantity, tag=tag)
                    tickets.append(ticket)
        else:
            # Liquidate specific symbol
            if isinstance(symbol, str):
                symbol = next((s for s in self.securities.keys() if s.value == symbol), None)
            
            if symbol:
                holding = self.portfolio.get_holding(symbol)
                if holding and holding.is_invested:
                    ticket = self.market_order(symbol, -holding.quantity, tag=tag)
                    tickets.append(ticket)
        
        return tickets
    
    # ===========================================
    # Portfolio Management Methods
    # ===========================================
    
    def set_holdings(self, symbol: Union[Symbol, str], percentage: float, 
                    liquidate_existing_holdings: bool = False, tag: str = ""):
        """
        Set holdings to a target percentage of portfolio.
        
        Args:
            symbol: The symbol to set holdings for
            percentage: Target percentage (0.0 to 1.0)
            liquidate_existing_holdings: Whether to liquidate other holdings first
            tag: Optional tag for the order
        """
        if isinstance(symbol, str):
            symbol = next((s for s in self.securities.keys() if s.value == symbol), None)
            if symbol is None:
                self.error(f"Symbol {symbol} not found in securities")
                return
        
        # Get current security and portfolio info
        if symbol not in self.securities:
            self.error(f"Security {symbol} not added to algorithm")
            return
        
        security = self.securities[symbol]
        current_price = security.market_price
        
        if current_price <= 0:
            self.error(f"No valid price data for {symbol}")
            return
        
        # Calculate target position
        portfolio_value = self.portfolio.total_portfolio_value
        target_value = portfolio_value * percentage
        target_quantity = int(target_value / current_price)
        
        # Get current position
        current_holding = self.portfolio.get_holding(symbol)
        current_quantity = current_holding.quantity if current_holding else 0
        
        # Calculate order quantity
        order_quantity = target_quantity - current_quantity
        
        if order_quantity != 0:
            # Liquidate other holdings if requested
            if liquidate_existing_holdings:
                self.liquidate(tag="Liquidation for rebalancing")
            
            # Place the order
            ticket = self.market_order(symbol, order_quantity, tag=tag)
            self.debug(f"Set holdings for {symbol} to {percentage:.2%} ({target_quantity} shares)")
    
    def calculate_order_quantity(self, symbol: Union[Symbol, str], target: float) -> int:
        """
        Calculate the order quantity needed to reach a target dollar amount.
        
        Args:
            symbol: The symbol to calculate for
            target: Target dollar amount
            
        Returns:
            Order quantity needed
        """
        if isinstance(symbol, str):
            symbol = next((s for s in self.securities.keys() if s.value == symbol), None)
        
        if symbol and symbol in self.securities:
            security = self.securities[symbol]
            if security.market_price > 0:
                current_holding = self.portfolio.get_holding(symbol)
                current_value = current_holding.market_value if current_holding else 0.0
                
                value_difference = target - current_value
                return int(value_difference / security.market_price)
        
        return 0
    
    # ===========================================
    # Scheduling Methods
    # ===========================================
    
    def schedule_function(self, func: Callable, date_rule: Dict[str, Any], 
                         time_rule: Dict[str, Any], name: str = ""):
        """
        Schedule a function to be called at specified times.
        
        Args:
            func: The function to call
            date_rule: Date-based scheduling rule (use DateRules)
            time_rule: Time-based scheduling rule (use TimeRules)
            name: Optional name for the scheduled event
        """
        self.schedule.schedule(func, name, date_rule, time_rule)
    
    # ===========================================
    # Logging Methods
    # ===========================================
    
    def log(self, message: str):
        """Log an informational message"""
        self.logger.info(message)
    
    def debug(self, message: str):
        """Log a debug message"""
        self.logger.debug(message)
    
    def error(self, message: str):
        """Log an error message"""
        self.logger.error(message)
    
    def warning(self, message: str):
        """Log a warning message"""
        self.logger.warning(message)
    
    # ===========================================
    # Properties
    # ===========================================
    
    @property
    def now(self) -> datetime:
        """Current algorithm time"""
        return self.time
    
    @property
    def utc_now(self) -> datetime:
        """Current UTC time"""
        return self.utc_time
    
    @property
    def is_warming_up(self) -> bool:
        """Returns True if algorithm is in warmup period"""
        return self._is_warming_up
    
    @property
    def current_slice(self) -> Optional[Slice]:
        """Returns the current data slice"""
        return self._current_slice
    
    # ===========================================
    # Runtime Configuration Methods
    # ===========================================
    
    def set_start_date(self, year: int, month: int, day: int):
        """Set the algorithm start date"""
        self.start_date = datetime(year, month, day)
        self.debug(f"Start date set to {self.start_date.strftime('%Y-%m-%d')}")
    
    def set_end_date(self, year: int, month: int, day: int):
        """Set the algorithm end date"""
        self.end_date = datetime(year, month, day)
        self.debug(f"End date set to {self.end_date.strftime('%Y-%m-%d')}")
    
    def set_cash(self, starting_cash: float):
        """Set the starting cash amount"""
        self.portfolio.cash = starting_cash
        self.portfolio.total_portfolio_value = starting_cash
        self.debug(f"Starting cash set to ${starting_cash:,.2f}")
    
    def set_benchmark(self, benchmark: str):
        """Set the benchmark for performance comparison"""
        self.benchmark = benchmark
        self.debug(f"Benchmark set to {benchmark}")
    
    def set_warmup(self, period: Union[int, timedelta], resolution: Resolution = Resolution.DAILY):
        """Set the warmup period"""
        if isinstance(period, int):
            # Convert bars to time period (approximation)
            if resolution == Resolution.DAILY:
                self.warmup_period = timedelta(days=period)
            elif resolution == Resolution.HOUR:
                self.warmup_period = timedelta(hours=period)
            elif resolution == Resolution.MINUTE:
                self.warmup_period = timedelta(minutes=period)
            else:
                self.warmup_period = timedelta(days=period)  # Default
        else:
            self.warmup_period = period
        
        self.debug(f"Warmup period set to {self.warmup_period}")
    
    # ===========================================
    # Internal Simulation Methods
    # ===========================================
    
    def _process_data_slice(self, data_slice: Slice):
        """
        Internal method to process a data slice.
        This would be called by the backtesting engine.
        """
        self._current_slice = data_slice
        self.time = data_slice.time
        
        # Update security prices
        self.securities.update_prices(data_slice.bars)
        self.securities.update_prices(data_slice.quote_bars)
        
        # Update portfolio market values
        self.portfolio.update_market_values(self.securities)
        
        # Execute scheduled events
        self.schedule.execute_pending()
        
        # Call user's OnData method
        if not self._is_warming_up:
            self.on_data(data_slice)
    
    def _initialize_algorithm(self):
        """
        Internal method to initialize the algorithm.
        This would be called by the backtesting engine.
        """
        if not self._initialized:
            self.initialize()
            self._initialized = True
            self.debug("Algorithm initialized")
    
    def _finalize_algorithm(self):
        """
        Internal method to finalize the algorithm.
        This would be called by the backtesting engine.
        """
        self.on_end_of_algorithm()
        
        # Generate final performance report
        stats = self.performance.get_stats()
        portfolio_stats = self.portfolio.get_performance_stats()
        
        self.log("=== Final Performance Summary ===")
        self.log(f"Total Portfolio Value: ${portfolio_stats['total_portfolio_value']:,.2f}")
        self.log(f"Total Trades: {portfolio_stats['total_trades']}")
        self.log(f"Win Rate: {portfolio_stats['win_rate']:.2%}")
        
        if stats:
            self.log(f"Sharpe Ratio: {stats['sharpe_ratio']:.3f}")
            self.log(f"Max Drawdown: {stats['max_drawdown']:.2f}%")
            self.log(f"Volatility: {stats['volatility']:.2%}")
        
        self.debug("Algorithm finalized")
