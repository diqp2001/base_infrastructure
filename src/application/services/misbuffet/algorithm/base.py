from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Callable
from decimal import Decimal
import uuid
import pandas as pd

from .symbol import Symbol, SymbolProperties
from .unified_portfolio_manager import UnifiedPortfolioManager
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
        
        # Unified Portfolio Management System
        self._entity_service = None
        self._unified_portfolio_manager: Optional[UnifiedPortfolioManager] = None
        
        # Legacy mappings (deprecated - will be removed)
        self._current_portfolio_entity: Optional[Any] = None
        self._order_entity_mapping: Dict[str, str] = {}
        self._transaction_mapping: Dict[str, str] = {}
        
        # Scheduling
        self.schedule = ScheduleManager()
        self.date_rules = DateRules()
        self.time_rules = TimeRules()
        
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
        Enhanced order event handling with transaction recording.
        
        Args:
            order_event: The order event that occurred
        """
        # Record transaction if filled and EntityService is available
        if (hasattr(order_event, 'status') and 
            order_event.status in ['FILLED', 'PARTIALLY_FILLED'] and 
            self._entity_service and 
            self._current_portfolio_entity):
            
            transaction = self.record_transaction(order_event)
            if transaction:
                self.debug(f"Transaction recorded: {transaction.id}")
        
        # Call any user-defined logic (can be overridden in subclasses)
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
        Submit a market order with unified portfolio management integration.
        
        Args:
            symbol: The symbol to trade
            quantity: Number of shares (positive for buy, negative for sell)
            asynchronous: Whether to submit asynchronously
            tag: Optional tag for the order
            
        Returns:
            OrderTicket for tracking the order
        """
        # Submit the order
        ticket = self._submit_order(MarketOrder, symbol, quantity, tag=tag)
        
        # Register with unified portfolio manager if available
        if self._unified_portfolio_manager:
            order_entity = self.register_order(ticket)
            if order_entity:
                self.debug(f"✅ Order registered with unified portfolio system: {order_entity.id}")
        
        return ticket
    
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
        ticket = OrderTicket(order)
        
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
    
    def set_holding(self, symbol: Union[str, Symbol], quantity: int, price: float):
        """
        Force the portfolio to hold exactly `quantity` shares at the given `price`.

        If the holding already exists but with the wrong quantity, it will be adjusted.
        If it doesn't exist, it will be created.

        Args:
            symbol: The security symbol (Symbol or str)
            quantity: Number of shares (positive = long, negative = short, 0 = flat)
            price: Entry price of the holding
        """
        # Resolve symbol if passed as string
        if isinstance(symbol, str):
            symbol_obj = next((s for s in self.securities.keys() if s.value == symbol), None)
            if symbol_obj is None:
                symbol_obj = Symbol.create_equity(symbol, "USA")
                self.add_equity(symbol, Resolution.DAILY)  # ensure security is added
            symbol = symbol_obj

        # Get current holding (if any)
        holding = self.portfolio._holdings.get(symbol)

        if holding is None:
            # create new
            holding = SecurityHolding(symbol=symbol, quantity=quantity, average_price=price)
            self.portfolio._holdings[symbol] = holding
        else:
            # update existing
            holding.set_holdings(quantity=quantity, average_price=price)

        # Sync portfolio market values
        self.portfolio.update_market_values(self.securities)

        self.debug(f"Set holding: {symbol} → {quantity} @ {price}")


    
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
    # Data Access Methods
    # ===========================================
    
    def history(self, symbols: Union[List[str], str], periods: int, 
                resolution: Resolution = Resolution.DAILY, 
                end_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Get historical data for specified symbols using MarketDataHistoryService.
        
        Args:
            symbols: Symbol or list of symbols
            periods: Number of periods to retrieve
            resolution: Data resolution
            end_time: End time for historical data (None for current time)
            
        Returns:
            DataFrame of historical data
        """
        # Use MarketDataHistoryService if available from the engine/data_loader
        if hasattr(self, '_history_service') and self._history_service:
            try:
                # Set frontier to current algorithm time to prevent look-ahead bias
                self._history_service.set_frontier(self.time)
                
                # Convert resolution to string format
                resolution_str = '1d'  # Default
                if resolution == Resolution.HOUR:
                    resolution_str = '1h'
                elif resolution == Resolution.MINUTE:
                    resolution_str = '1m'
                
                # Get historical data using the service
                df = self._history_service.get_history(
                    symbols=symbols, 
                    periods=periods, 
                    resolution=resolution_str,
                    factor_data_service=getattr(self, '_factor_data_service', None)
                )
                
                if not df.empty:
                    info(f"Retrieved {len(df)} historical records using MarketDataHistoryService")
                    return df
                else:
                    warning(f"No historical data found for symbols {symbols}")
                    
            except Exception as e:
                error(f"Error using MarketDataHistoryService: {e}")
                # Fall through to mock implementation
        
        # Fallback: Generate mock historical data for demonstration
        import pandas as pd
        
        if isinstance(symbols, str):
            symbols = [symbols]
        
        if end_time is None:
            end_time = self.time
        
        data = {}
        for symbol in symbols:
            dates = pd.date_range(
                end=end_time, 
                periods=periods, 
                freq='D' if resolution == Resolution.DAILY else 'min'
            )
            
            # Simple mock data generation
            base_price = 100
            prices = [base_price * (1 + 0.01 * (i % 10 - 5)) for i in range(len(dates))]
            volumes = [1000000 + (i * 10000) for i in range(len(dates))]
            
            df = pd.DataFrame({
                'time': dates,
                'open': prices,
                'high': [p * 1.02 for p in prices],
                'low': [p * 0.98 for p in prices],
                'close': prices,
                'volume': volumes
            })
            df.set_index('time', inplace=True)
            data[symbol] = df
        
        return data[symbols[0]] if len(symbols) == 1 else data
    
    def runtime_statistic(self, name: str, value: str):
        """Add a runtime statistic for display"""
        # This is a placeholder - would be implemented by the engine
        self.log(f"Runtime Stat - {name}: {value}")
    
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
    # Repository Integration Methods
    # ===========================================
    
    def set_entity_service(self, entity_service):
        """Inject EntityService for unified portfolio management."""
        self._entity_service = entity_service
        
        # Initialize unified portfolio manager with repository factory from EntityService
        if entity_service and entity_service.repository_factory and not self._unified_portfolio_manager:
            self._unified_portfolio_manager = UnifiedPortfolioManager(
                repository_factory=entity_service.repository_factory, 
                logger=self.logger
            )
            self.debug("✅ Unified portfolio management system initialized via EntityService")
        
        self.debug("EntityService injected successfully")
        
    @property
    def repository_factory(self):
        """Access repository factory through EntityService."""
        return self._entity_service.repository_factory if self._entity_service else None
    
    def register_portfolio(self, portfolio_config: Dict[str, Any] = None, 
                          name: str = None, initial_cash: float = None, 
                          portfolio_type: str = None) -> Optional[Any]:
        """
        Register portfolio using unified portfolio management system.
        
        Can accept either a portfolio_config dict (new enhanced way) or individual 
        parameters (legacy compatibility).
        
        Args:
            portfolio_config: Full portfolio configuration dict with sub-portfolios
            name: Portfolio name (legacy)
            initial_cash: Initial cash (legacy)
            portfolio_type: Portfolio type (legacy)
        """
        if not self._unified_portfolio_manager:
            self.warning("No unified portfolio manager available")
            return None
        
        # Use enhanced register_portfolio method that handles config dict
        portfolio = self._unified_portfolio_manager.register_portfolio_with_config(
            portfolio_config=portfolio_config,
            name=name,
            initial_cash=initial_cash,
            portfolio_type=portfolio_type
        )
        
        if portfolio:
            # Update QCAlgorithm's portfolio cash to sync with domain entity
            cash_amount = initial_cash or (portfolio_config.get('initial_cash', 100000.0) if portfolio_config else 100000.0)
            self.portfolio.cash = cash_amount
            self.portfolio.total_portfolio_value = cash_amount
            
            # Store reference for legacy compatibility
            self._current_portfolio_entity = portfolio
            
        return portfolio
    
    def register_order(self, order_ticket) -> Optional[Any]:
        """Register an order using unified portfolio management system."""
        if not self._unified_portfolio_manager:
            return None
        
        # Use unified portfolio manager
        return self._unified_portfolio_manager.register_order(order_ticket)
    
    def record_transaction(self, order_event) -> Optional[Any]:
        """Record a transaction using unified portfolio management system."""
        if not self._unified_portfolio_manager:
            return None
        
        # Use unified portfolio manager
        transaction = self._unified_portfolio_manager.record_transaction(order_event)
        
        if transaction:
            # Sync QCAlgorithm portfolio values with unified system
            self._sync_portfolio_values()
        
        return transaction
    
    def update_holding(self, symbol: str, quantity_change: int, 
                      transaction_price: float) -> Optional[Any]:
        """Update holdings using the EntityService and repository system."""
        if not self._entity_service or not self._current_portfolio_entity:
            return None
        
        try:
            holding_repo = self._entity_service.repository_factory.holding_local_repo
            
            # Find or create holding
            holding = holding_repo._create_or_get_holding(
                portfolio_id=self._current_portfolio_entity.id,
                asset_symbol=symbol,
                quantity=quantity_change,
                average_price=transaction_price
            )
            
            return holding
            
        except Exception as e:
            self.error(f"Error updating holding for {symbol}: {e}")
            return None
    
    def get_current_portfolio(self) -> Optional[Any]:
        """Get the current portfolio entity from unified portfolio manager."""
        if self._unified_portfolio_manager:
            return self._unified_portfolio_manager.get_current_portfolio()
        return self._current_portfolio_entity
    
    def _convert_qc_order_to_entity(self, ticket) -> Any:
        """Convert QCAlgorithm order to domain entity."""
        from src.domain.entities.finance.order.order import Order as OrderEntity, OrderType, OrderSide, OrderStatus
        from datetime import datetime
        import uuid
        
        return OrderEntity(
            id=self._get_next_order_id(),
            portfolio_id=self._current_portfolio_entity.id,
            holding_id=self._get_holding_id_for_symbol(ticket.symbol),
            order_type=self._map_order_type(ticket.order_type if hasattr(ticket, 'order_type') else 'MARKET'),
            side=OrderSide.BUY if ticket.quantity > 0 else OrderSide.SELL,
            quantity=abs(ticket.quantity),
            created_at=getattr(ticket, 'time', datetime.now()),
            status=self._map_order_status(getattr(ticket, 'status', 'PENDING')),
            account_id=self._get_account_id(),
            price=getattr(ticket, 'limit_price', None),
            external_order_id=ticket.order_id
        )
    
    def _create_transaction_entity(self, order_event) -> Any:
        """Create transaction entity from order event."""
        from src.domain.entities.finance.transaction.transaction import Transaction as TransactionEntity, TransactionType, TransactionStatus
        from datetime import datetime, timedelta
        import uuid
        
        # Find the corresponding order entity
        order_entity = self._find_order_entity(order_event.order_id)
        
        return TransactionEntity(
            id=self._get_next_transaction_id(),
            portfolio_id=self._current_portfolio_entity.id,
            holding_id=order_entity.holding_id if order_entity else 1,
            order_id=order_entity.id if order_entity else 1,
            date=getattr(order_event, 'time', datetime.now()),
            transaction_type=self._map_to_transaction_type(order_entity.order_type if order_entity else 'MARKET'),
            transaction_id=str(uuid.uuid4()),
            account_id=self._get_account_id(),
            trade_date=getattr(order_event, 'time', datetime.now()).date(),
            value_date=getattr(order_event, 'time', datetime.now()).date(),
            settlement_date=getattr(order_event, 'time', datetime.now()).date() + timedelta(days=2),
            status=TransactionStatus.EXECUTED,
            spread=0.0,
            currency_id=self._get_currency_id(),
            exchange_id=self._get_exchange_id()
        )
    
    def _get_next_order_id(self) -> int:
        """Get next available order ID."""
        return len(self._order_entity_mapping) + 1
    
    def _get_next_transaction_id(self) -> int:
        """Get next available transaction ID."""
        return len(self._transaction_mapping) + 1
    
    def _get_holding_id_for_symbol(self, symbol) -> int:
        """Get holding ID for symbol (simplified implementation)."""
        return 1  # Simplified
    
    def _get_account_id(self) -> str:
        """Get account ID."""
        return "DEFAULT_ACCOUNT"
    
    def _get_currency_id(self) -> int:
        """Get currency ID."""
        return 1  # USD
    
    def _get_exchange_id(self) -> int:
        """Get exchange ID."""
        return 1  # Default exchange
    
    def _map_order_type(self, order_type_str: str):
        """Map QC order type to domain OrderType."""
        from src.domain.entities.finance.order.order import OrderType
        
        mapping = {
            'MARKET': OrderType.MARKET,
            'LIMIT': OrderType.LIMIT,
            'STOP': OrderType.STOP,
            'STOP_LIMIT': OrderType.STOP_LIMIT
        }
        return mapping.get(order_type_str.upper(), OrderType.MARKET)
    
    def _map_order_status(self, status_str: str):
        """Map QC order status to domain OrderStatus."""
        from src.domain.entities.finance.order.order import OrderStatus
        
        mapping = {
            'PENDING': OrderStatus.PENDING,
            'SUBMITTED': OrderStatus.SUBMITTED,
            'PARTIALLY_FILLED': OrderStatus.PARTIALLY_FILLED,
            'FILLED': OrderStatus.FILLED,
            'CANCELLED': OrderStatus.CANCELLED,
            'REJECTED': OrderStatus.REJECTED
        }
        return mapping.get(status_str.upper(), OrderStatus.PENDING)
    
    def _map_to_transaction_type(self, order_type):
        """Map order type to transaction type."""
        from src.domain.entities.finance.transaction.transaction import TransactionType
        from src.domain.entities.finance.order.order import OrderType
        
        mapping = {
            OrderType.MARKET: TransactionType.MARKET_ORDER,
            OrderType.LIMIT: TransactionType.LIMIT_ORDER,
            OrderType.STOP: TransactionType.STOP_ORDER,
            OrderType.STOP_LIMIT: TransactionType.STOP_LIMIT_ORDER
        }
        return mapping.get(order_type, TransactionType.MARKET_ORDER)
    
    def _find_order_entity(self, order_id: str) -> Optional[Any]:
        """Find order entity by QC order ID."""
        entity_id = self._order_entity_mapping.get(order_id)
        if entity_id and self._entity_service:
            order_repo = self._entity_service.repository_factory._local_repositories.get('order')
            if order_repo:
                return order_repo.get_by_id(entity_id)
        return None
    
    def _update_holdings_from_transaction(self, transaction) -> None:
        """Update holdings based on transaction."""
        try:
            if not transaction or not self._entity_service:
                return
            
            # This would typically update holding quantities based on the transaction
            # Implementation depends on your specific business logic
            self.debug(f"Updated holdings from transaction {transaction.id}")
            
        except Exception as e:
            self.error(f"Error updating holdings from transaction: {e}")

    # ===========================================
    # Unified Portfolio Management Methods
    # ===========================================
    
    def get_unified_portfolio_value(self) -> float:
        """
        Get total portfolio value from unified portfolio management system.
        
        This is the single source of truth for portfolio value using domain entities.
        """
        if not self._unified_portfolio_manager:
            # Fallback to QCAlgorithm's built-in portfolio
            return float(self.portfolio.total_portfolio_value)
        
        return float(self._unified_portfolio_manager.get_portfolio_value())

    def get_unified_positions(self) -> List[Dict[str, Any]]:
        """
        Get all active positions from unified portfolio management system.
        
        Returns positions using domain entities instead of custom tracking.
        """
        if not self._unified_portfolio_manager:
            return []
        
        return self._unified_portfolio_manager.get_active_positions()

    def get_unified_orders_summary(self) -> Dict[str, Any]:
        """Get orders summary from unified portfolio management system."""
        if not self._unified_portfolio_manager:
            return {}
        
        return self._unified_portfolio_manager.get_orders_summary()

    def get_unified_transactions_summary(self) -> Dict[str, Any]:
        """Get transactions summary from unified portfolio management system."""
        if not self._unified_portfolio_manager:
            return {}
        
        return self._unified_portfolio_manager.get_transactions_summary()

    def get_unified_portfolio_state(self) -> Dict[str, Any]:
        """
        Get complete portfolio state from unified management system.
        
        This provides a comprehensive view using domain entities and repositories.
        """
        if not self._unified_portfolio_manager:
            # Fallback to basic QCAlgorithm data
            return {
                'portfolio_value': float(self.portfolio.total_portfolio_value),
                'cash': float(self.portfolio.cash),
                'warning': 'Using fallback QCAlgorithm data - unified portfolio manager not available'
            }
        
        return self._unified_portfolio_manager.get_unified_state()

    def _sync_portfolio_values(self):
        """
        Synchronize QCAlgorithm portfolio values with unified portfolio manager.
        
        This ensures consistency between the built-in portfolio and domain entities.
        """
        if not self._unified_portfolio_manager:
            return
        
        try:
            # Get unified portfolio value
            unified_value = self._unified_portfolio_manager.get_portfolio_value()
            
            # Update QCAlgorithm portfolio to match
            self.portfolio.total_portfolio_value = float(unified_value)
            
            # Update cash balance (simplified)
            cash_balance = self._unified_portfolio_manager._get_cash_balance()
            self.portfolio.cash = float(cash_balance)
            
            self.debug(f"✅ Portfolio values synchronized: ${float(unified_value):,.2f}")
            
        except Exception as e:
            self.error(f"❌ Portfolio synchronization failed: {e}")

    def is_unified_portfolio_enabled(self) -> bool:
        """Check if unified portfolio management is available and enabled."""
        return self._unified_portfolio_manager is not None
    
    # ===========================================
    # Data Processing Utility Methods
    # ===========================================
    
    def _has_price_data(self, ticker: str, security_symbol) -> bool:
        """
        Check if price data is available for the given ticker.
        Handles both DataFrame and Slice data formats.
        
        Args:
            ticker: The ticker symbol (e.g., 'AAPL')
            security_symbol: The Symbol object from the security
        
        Returns:
            bool: True if price data is available
        """
        # Check DataFrame format first
        if hasattr(self, '_current_data_frame') and self._current_data_frame is not None:
            # DataFrame format - check if ticker matches symbol column or if we have price columns
            if 'symbol' in self._current_data_frame.columns:
                return ticker in self._current_data_frame['symbol'].values
            else:
                # Assume single-ticker DataFrame - check if we have price data
                price_columns = ['close', 'Close', 'price', 'Price']
                return any(col in self._current_data_frame.columns for col in price_columns)
        
        # Check Slice format
        elif hasattr(self, '_current_data_slice') and self._current_data_slice is not None:
            return self._symbol_in_data(security_symbol, self._current_data_slice)
        
        return False
    
    def _get_current_price(self, ticker: str, security_symbol) -> Optional[float]:
        """
        Get the current price for the given ticker from available data.
        Handles both DataFrame and Slice data formats.
        
        Args:
            ticker: The ticker symbol (e.g., 'AAPL')
            security_symbol: The Symbol object from the security
        
        Returns:
            float: Current price, or None if not available
        """
        try:
            # Handle DataFrame format
            if hasattr(self, '_current_data_frame') and self._current_data_frame is not None:
                df = self._current_data_frame
                
                if 'symbol' in df.columns:
                    # Multi-ticker DataFrame - filter by ticker
                    ticker_data = df[df['symbol'] == ticker]
                    if not ticker_data.empty:
                        # Get the most recent price
                        latest_row = ticker_data.iloc[-1]
                        price_columns = ['close', 'Close', 'price', 'Price']
                        for col in price_columns:
                            if col in latest_row and pd.notna(latest_row[col]):
                                return float(latest_row[col])
                else:
                    # Single-ticker DataFrame - assume it's for our ticker
                    if not df.empty:
                        latest_row = df.iloc[-1]
                        price_columns = ['close', 'Close', 'price', 'Price']
                        for col in price_columns:
                            if col in latest_row and pd.notna(latest_row[col]):
                                return float(latest_row[col])
            
            # Handle Slice format
            elif hasattr(self, '_current_data_slice') and self._current_data_slice is not None:
                data_symbol = self._find_matching_symbol(security_symbol, self._current_data_slice)
                if data_symbol is not None:
                    return float(self._current_data_slice[data_symbol].close)
            
            return None
            
        except Exception as e:
            self.log(f"Error getting current price for {ticker}: {str(e)}")
            return None
    
    def _get_current_holdings_value(self, ticker: str, security_symbol) -> float:
        """
        Get the current holdings value for a security.
        Handles portfolio access safely.
        
        Args:
            ticker: The ticker symbol (e.g., 'AAPL')
            security_symbol: The Symbol object from the security
        
        Returns:
            float: Current holdings value (0.0 if no holdings)
        """
        try:
            # SecurityPortfolioManager direct access - this is the correct approach
            if hasattr(self.portfolio, '_holdings'):
                holdings_dict = self.portfolio._holdings
                if security_symbol in holdings_dict and holdings_dict[security_symbol] is not None:
                    holding = holdings_dict[security_symbol]
                    return float(holding.market_value)  # Use market_value, not holdings_value
            
            # Alternative: try using the SecurityPortfolioManager indexing operator
            try:
                portfolio_holding = self.portfolio[security_symbol]
                if portfolio_holding is not None:
                    return float(portfolio_holding.market_value)  # Use market_value, not holdings_value
            except (KeyError, TypeError, AttributeError):
                # Symbol not found in portfolio or portfolio doesn't support indexing
                pass
            
            return 0.0
            
        except Exception as e:
            self.log(f"Error accessing holdings for {ticker}: {str(e)}")
            return 0.0
    
    def _symbol_in_data(self, security_symbol, data_slice) -> bool:
        """
        Check if a security symbol exists in the data slice.
        Handles different symbol representations (e.g., with/without country codes).
        
        Args:
            security_symbol: The Symbol object from the security
            data_slice: The Slice object containing market data
        
        Returns:
            bool: True if the symbol is found in the data slice
        """
        # Defensive check - ensure data_slice has bars attribute
        if not hasattr(data_slice, 'bars'):
            return False
            
        # Direct comparison first (fastest)
        if security_symbol in data_slice:
            return True
        
        # Check if any symbol in data matches the ticker
        security_ticker = str(security_symbol).split(',')[0].strip("Symbol('")
        
        for data_symbol in data_slice.bars.keys():
            data_ticker = str(data_symbol).split(',')[0].strip("Symbol('")
            if security_ticker == data_ticker:
                return True
        
        return False
    
    def _find_matching_symbol(self, security_symbol, data_slice):
        """
        Find the matching symbol in the data slice for a given security symbol.
        
        Args:
            security_symbol: The Symbol object from the security
            data_slice: The Slice object containing market data
        
        Returns:
            Symbol: The matching symbol from data_slice, or None if not found
        """
        # Only process if data_slice has bars attribute (is a proper Slice object)
        if not hasattr(data_slice, 'bars'):
            return None
            
        # Direct comparison first
        if security_symbol in data_slice:
            return security_symbol
        
        # Check if any symbol in data matches the ticker
        security_ticker = str(security_symbol).split(',')[0].strip("Symbol('")
        
        for data_symbol in data_slice.bars.keys():
            data_ticker = str(data_symbol).split(',')[0].strip("Symbol('")
            if security_ticker == data_ticker:
                return data_symbol
        
        return None
    
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
