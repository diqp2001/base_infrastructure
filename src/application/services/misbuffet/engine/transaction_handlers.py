"""
Transaction handler implementations for QuantConnect Lean Engine Python implementation.
Handles order processing and execution for backtesting and live trading.

Enhanced with domain entity integration for Account, Order, and Transaction persistence.
Provides hybrid approach maintaining legacy trading engine compatibility while adding
proper business logic and data persistence through repository pattern.
"""

import logging
import threading
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Set, TYPE_CHECKING
from decimal import Decimal
from enum import Enum

from .interfaces import ITransactionHandler, IAlgorithm, IBrokerage
from .enums import ComponentState

# Import from common module (for trading engine compatibility)
from ..common import (
    Order as LegacyOrder, OrderTicket, OrderEvent, OrderFill, OrderStatus, OrderType,
    OrderDirection, Symbol, Security
)

# Import new domain entities for persistence
from src.domain.entities.finance.account import Account, AccountType, AccountStatus
from src.domain.entities.finance.order.order import (
    Order as DomainOrder, OrderType as DomainOrderType, 
    OrderSide, OrderStatus as DomainOrderStatus
)
from src.domain.entities.finance.transaction.transaction import (
    Transaction, TransactionType, TransactionStatus
)

# Import repository ports for dependency injection
if TYPE_CHECKING:
    from src.domain.ports.finance.account_port import AccountPort
    from src.domain.ports.finance.order.order_port import OrderPort
    from src.domain.ports.finance.transaction.transaction_port import TransactionPort


class TransactionHandlerMode(Enum):
    """Transaction handler operating modes."""
    BACKTESTING = "Backtesting"
    LIVE = "Live"
    PAPER_TRADING = "PaperTrading"


class BaseTransactionHandler(ITransactionHandler, ABC):
    """Base class for all transaction handler implementations."""
    
    def __init__(self, account_repo=None, order_repo=None, transaction_repo=None, default_account_id: str = "DEFAULT_ACCOUNT"):
        """Initialize the base transaction handler with repository dependencies."""
        self._algorithm: Optional[IAlgorithm] = None
        self._brokerage: Optional[IBrokerage] = None
        self._state = ComponentState.CREATED
        self._lock = threading.RLock()
        self._logger = logging.getLogger(self.__class__.__name__)
        
        # Repository dependencies (injected)
        self._account_repo: Optional['AccountPort'] = account_repo
        self._order_repo: Optional['OrderPort'] = order_repo
        self._transaction_repo: Optional['TransactionPort'] = transaction_repo
        
        # Default account configuration
        self._default_account_id = default_account_id
        self._default_account: Optional[Account] = None
        
        # Legacy order tracking (for trading engine compatibility)
        self._orders: Dict[int, LegacyOrder] = {}
        self._order_tickets: Dict[int, OrderTicket] = {}
        self._order_events: List[OrderEvent] = []
        self._next_order_id = 1
        
        # Domain entity tracking
        self._domain_orders: Dict[int, DomainOrder] = {}
        self._domain_order_to_legacy_id_mapping: Dict[int, int] = {}  # domain_id -> legacy_id
        self._legacy_to_domain_id_mapping: Dict[int, int] = {}  # legacy_id -> domain_id
        
        # Processing queues
        self._pending_orders: List[LegacyOrder] = []
        self._order_fills: List[OrderEvent] = []
        
        # Metrics
        self._total_orders = 0
        self._filled_orders = 0
        self._cancelled_orders = 0
        self._rejected_orders = 0
        
        self._logger.info(f"Initialized {self.__class__.__name__} with repository support")
    
    def initialize(self, algorithm: IAlgorithm, brokerage: Optional[IBrokerage]) -> None:
        """Initialize the transaction handler with algorithm and brokerage."""
        try:
            with self._lock:
                if self._state != ComponentState.CREATED:
                    self._logger.warning(f"Transaction handler already initialized with state: {self._state}")
                    return
                
                self._state = ComponentState.INITIALIZING
                self._algorithm = algorithm
                self._brokerage = brokerage
                
                self._logger.info("Initializing transaction handler")
                
                # Initialize default account if repositories are available
                self._initialize_default_account()
                
                # Initialize specific components
                self._initialize_specific()
                
                self._state = ComponentState.INITIALIZED
                self._logger.info("Transaction handler initialization completed")
                
        except Exception as e:
            self._logger.error(f"Error during transaction handler initialization: {e}")
            self._state = ComponentState.ERROR
            raise
    
    def process_order(self, order: LegacyOrder) -> bool:
        """Process an order for execution."""
        try:
            with self._lock:
                if self._state != ComponentState.INITIALIZED:
                    self._logger.error(f"Transaction handler not initialized: {self._state}")
                    return False
                
                # Assign order ID if not set
                if order.id == 0:
                    order.id = self._get_next_order_id()
                
                # Validate order
                if not self._validate_order(order):
                    self._reject_order(order, "Order validation failed")
                    return False
                
                # Store order
                self._orders[order.id] = order
                self._total_orders += 1
                
                # Persist order as domain entity if repositories available
                self._persist_order(order)
                
                # Create order ticket
                ticket = self._create_order_ticket(order)
                self._order_tickets[order.id] = ticket
                
                # Add to pending queue
                self._pending_orders.append(order)
                
                # Process order specific to implementation
                return self._process_order_specific(order)
                
        except Exception as e:
            self._logger.error(f"Error processing order {order.id}: {e}")
            return False
    
    def get_open_orders(self, symbol: Optional[Symbol] = None) -> List[LegacyOrder]:
        """Get all open orders, optionally filtered by symbol."""
        try:
            with self._lock:
                open_orders = []
                
                for order in self._orders.values():
                    if order.status in [OrderStatus.NEW, OrderStatus.SUBMITTED, OrderStatus.PARTIAL_FILL]:
                        if symbol is None or order.symbol == symbol:
                            open_orders.append(order)
                
                return open_orders
                
        except Exception as e:
            self._logger.error(f"Error getting open orders: {e}")
            return []
    
    def get_order_tickets(self) -> List[OrderTicket]:
        """Get all order tickets."""
        try:
            with self._lock:
                return list(self._order_tickets.values())
                
        except Exception as e:
            self._logger.error(f"Error getting order tickets: {e}")  
            return []
    
    def cancel_order(self, order_id: int) -> bool:
        """Cancel an existing order."""
        try:
            with self._lock:
                if order_id not in self._orders:
                    self._logger.warning(f"Order not found for cancellation: {order_id}")
                    return False
                
                order = self._orders[order_id]
                
                # Check if order can be cancelled
                if order.status not in [OrderStatus.NEW, OrderStatus.SUBMITTED, OrderStatus.PARTIAL_FILL]:
                    self._logger.warning(f"Cannot cancel order in status: {order.status}")
                    return False
                
                # Update domain order status before cancellation
                order.status = OrderStatus.CANCEL_PENDING
                self._update_domain_order_status(order)
                
                # Cancel order specific to implementation
                return self._cancel_order_specific(order)
                
        except Exception as e:
            self._logger.error(f"Error cancelling order {order_id}: {e}")
            return False
    
    def update_order(self, order: LegacyOrder) -> bool:
        """Update an existing order."""
        try:
            with self._lock:
                if order.id not in self._orders:
                    self._logger.warning(f"Order not found for update: {order.id}")
                    return False
                
                existing_order = self._orders[order.id]
                
                # Check if order can be updated
                if existing_order.status not in [OrderStatus.NEW, OrderStatus.SUBMITTED]:
                    self._logger.warning(f"Cannot update order in status: {existing_order.status}")
                    return False
                
                # Update domain order status
                self._update_domain_order_status(order)
                
                # Update order specific to implementation
                return self._update_order_specific(order)
                
        except Exception as e:
            self._logger.error(f"Error updating order {order.id}: {e}")
            return False
    
    def handle_fills(self, fills: List[OrderEvent]) -> None:
        """Handle order fill events."""
        try:
            with self._lock:
                for fill in fills:
                    self._process_fill(fill)
                    
        except Exception as e:
            self._logger.error(f"Error handling fills: {e}")
    
    def get_order_by_id(self, order_id: int) -> Optional[LegacyOrder]:
        """Get an order by its ID."""
        with self._lock:
            return self._orders.get(order_id)
    
    def get_order_ticket_by_id(self, order_id: int) -> Optional[OrderTicket]:
        """Get an order ticket by order ID."""
        with self._lock:
            return self._order_tickets.get(order_id)
    
    def get_metrics(self) -> Dict[str, int]:
        """Get transaction handler metrics."""
        with self._lock:
            return {
                'total_orders': self._total_orders,
                'filled_orders': self._filled_orders,
                'cancelled_orders': self._cancelled_orders,
                'rejected_orders': self._rejected_orders,
                'open_orders': len(self.get_open_orders())
            }
    
    # Abstract methods for specific implementations
    
    @abstractmethod
    def _initialize_specific(self) -> None:
        """Perform specific initialization. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _process_order_specific(self, order: LegacyOrder) -> bool:
        """Process order specific to implementation. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _cancel_order_specific(self, order: LegacyOrder) -> bool:
        """Cancel order specific to implementation. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def _update_order_specific(self, order: LegacyOrder) -> bool:
        """Update order specific to implementation. Must be implemented by subclasses."""
        pass
    
    # Protected helper methods
    
    def _get_next_order_id(self) -> int:
        """Get the next available order ID."""
        order_id = self._next_order_id
        self._next_order_id += 1
        return order_id
    
    def _validate_order(self, order: LegacyOrder) -> bool:
        """Validate an order before processing."""
        try:
            # Basic validation
            if not order.symbol:
                self._logger.error("Order must have a symbol")
                return False
            
            if order.quantity == 0:
                self._logger.error("Order quantity cannot be zero")
                return False
            
            if order.order_type == OrderType.LIMIT and order.limit_price <= 0:
                self._logger.error("Limit orders must have a positive limit price")
                return False
            
            if order.order_type == OrderType.STOP_MARKET and order.stop_price <= 0:
                self._logger.error("Stop orders must have a positive stop price")
                return False
            
            # Additional validation can be added here
            return True
            
        except Exception as e:
            self._logger.error(f"Error validating order: {e}")
            return False
    
    def _create_order_ticket(self, order: LegacyOrder) -> OrderTicket:
        """Create an order ticket for the order."""
        try:
            ticket = OrderTicket(
                order_id=order.id,
                symbol=order.symbol,
                quantity=order.quantity,
                order_type=order.order_type,
                status=order.status,
                time=order.time,
                tag=order.tag
            )
            
            return ticket
            
        except Exception as e:
            self._logger.error(f"Error creating order ticket: {e}")
            raise
    
    def _reject_order(self, order: LegacyOrder, reason: str) -> None:
        """Reject an order with the given reason."""
        try:
            order.status = OrderStatus.INVALID
            
            # Create rejection event
            rejection_event = OrderEvent(
                order_id=order.id,
                symbol=order.symbol,
                time=datetime.utcnow(),
                status=OrderStatus.INVALID,
                direction=order.direction,
                fill_quantity=0,
                fill_price=0,
                message=reason
            )
            
            self._order_events.append(rejection_event)
            self._rejected_orders += 1
            
            # Notify algorithm
            if self._algorithm:
                self._algorithm.on_order_event(rejection_event)
            
            self._logger.warning(f"Order {order.id} rejected: {reason}")
            
        except Exception as e:
            self._logger.error(f"Error rejecting order: {e}")
    
    def _process_fill(self, fill_event: OrderEvent) -> None:
        """Process an order fill event with domain entity integration."""
        try:
            order = self._orders.get(fill_event.order_id)
            if not order:
                self._logger.warning(f"Order not found for fill: {fill_event.order_id}")
                return
            
            # Update legacy order status
            order.status = fill_event.status
            
            # Track fills
            if fill_event.status == OrderStatus.FILLED:
                self._filled_orders += 1
            elif fill_event.status == OrderStatus.CANCELED:
                self._cancelled_orders += 1
            
            # Store fill event
            self._order_events.append(fill_event)
            
            # Integrate with domain entities if repositories available
            self._integrate_fill_with_entities(order, fill_event)
            
            # Notify algorithm
            if self._algorithm:
                self._algorithm.on_order_event(fill_event)
            
            self._logger.info(f"Processed fill for order {fill_event.order_id}: {fill_event.status}")
            
        except Exception as e:
            self._logger.error(f"Error processing fill: {e}")
    
    def _create_fill_event(self, order: LegacyOrder, fill_price: Decimal, 
                          fill_quantity: int, message: str = "") -> OrderEvent:
        """Create a fill event for an order."""
        try:
            status = OrderStatus.FILLED if abs(fill_quantity) == abs(order.quantity) else OrderStatus.PARTIAL_FILL
            
            fill_event = OrderEvent(
                order_id=order.id,
                symbol=order.symbol,
                time=datetime.utcnow(),
                status=status,
                direction=order.direction,
                fill_quantity=fill_quantity,
                fill_price=fill_price,
                message=message
            )
            
            return fill_event
            
        except Exception as e:
            self._logger.error(f"Error creating fill event: {e}")
            raise
    
    # New methods for entity integration
    
    def _initialize_default_account(self) -> None:
        """Initialize or retrieve the default trading account."""
        try:
            if not self._account_repo:
                self._logger.warning("No account repository available - using in-memory account tracking")
                return
            
            # Try to get existing account
            self._default_account = self._account_repo.get_by_account_id(self._default_account_id)
            
            if not self._default_account:
                # Create default account
                self._default_account = Account(
                    id=0,  # Will be set by repository
                    account_id=self._default_account_id,
                    account_type=AccountType.MARGIN,
                    status=AccountStatus.ACTIVE,
                    base_currency_id=1,  # USD
                    created_at=datetime.now()
                )
                
                # Add to repository
                self._default_account = self._account_repo.add(self._default_account)
                self._logger.info(f"Created default account: {self._default_account_id}")
            else:
                self._logger.info(f"Using existing default account: {self._default_account_id}")
                
        except Exception as e:
            self._logger.error(f"Error initializing default account: {e}")
    
    def _create_domain_order_from_legacy(self, legacy_order: LegacyOrder) -> Optional[DomainOrder]:
        """Convert legacy order to domain order entity."""
        try:
            if not self._order_repo:
                return None
            
            # Map order types
            order_type_mapping = {
                OrderType.MARKET: DomainOrderType.MARKET,
                OrderType.LIMIT: DomainOrderType.LIMIT,
                OrderType.STOP_MARKET: DomainOrderType.STOP,
                OrderType.STOP_LIMIT: DomainOrderType.STOP_LIMIT
            }
            
            # Map order sides
            side_mapping = {
                OrderDirection.BUY: OrderSide.BUY,
                OrderDirection.SELL: OrderSide.SELL
            }
            
            # Map order status
            status_mapping = {
                OrderStatus.NEW: DomainOrderStatus.PENDING,
                OrderStatus.SUBMITTED: DomainOrderStatus.SUBMITTED,
                OrderStatus.PARTIAL_FILLED: DomainOrderStatus.PARTIALLY_FILLED,
                OrderStatus.FILLED: DomainOrderStatus.FILLED,
                OrderStatus.CANCELED: DomainOrderStatus.CANCELLED,
                OrderStatus.INVALID: DomainOrderStatus.REJECTED
            }
            
            domain_order = DomainOrder(
                id=0,  # Will be set by repository
                portfolio_id=1,  # Default portfolio
                holding_id=1,  # Default holding
                order_type=order_type_mapping.get(legacy_order.order_type, DomainOrderType.MARKET),
                side=side_mapping.get(legacy_order.direction, OrderSide.BUY),
                quantity=float(abs(legacy_order.quantity)),
                created_at=legacy_order.created_time,
                status=status_mapping.get(legacy_order.status, DomainOrderStatus.PENDING),
                account_id=self._default_account_id,
                price=legacy_order.limit_price,
                stop_price=legacy_order.stop_price,
                filled_quantity=float(legacy_order.quantity_filled),
                average_fill_price=legacy_order.average_fill_price if legacy_order.average_fill_price > 0 else None,
                time_in_force="GTC",
                external_order_id=legacy_order.id
            )
            
            return domain_order
            
        except Exception as e:
            self._logger.error(f"Error creating domain order: {e}")
            return None
    
    def _persist_order(self, legacy_order: LegacyOrder) -> Optional[DomainOrder]:
        """Persist legacy order as domain entity."""
        try:
            if not self._order_repo:
                return None
            
            domain_order = self._create_domain_order_from_legacy(legacy_order)
            if not domain_order:
                return None
            
            # Save to repository
            persisted_order = self._order_repo.add(domain_order)
            if persisted_order:
                # Update mappings
                self._domain_orders[persisted_order.id] = persisted_order
                self._domain_order_to_legacy_id_mapping[persisted_order.id] = legacy_order.id
                self._legacy_to_domain_id_mapping[legacy_order.id] = persisted_order.id
                
                self._logger.debug(f"Persisted order {legacy_order.id} as domain entity {persisted_order.id}")
            
            return persisted_order
            
        except Exception as e:
            self._logger.error(f"Error persisting order: {e}")
            return None
    
    def _create_transaction_from_fill(self, legacy_order: LegacyOrder, fill_event: OrderEvent) -> Optional[Transaction]:
        """Create transaction entity from order fill."""
        try:
            if not self._transaction_repo or not fill_event.is_fill():
                return None
            
            # Get corresponding domain order
            domain_order_id = self._legacy_to_domain_id_mapping.get(legacy_order.id)
            if not domain_order_id:
                # Try to persist the order first
                domain_order = self._persist_order(legacy_order)
                domain_order_id = domain_order.id if domain_order else 1
            
            # Map transaction type from order type
            transaction_type_mapping = {
                OrderType.MARKET: TransactionType.MARKET_ORDER,
                OrderType.LIMIT: TransactionType.LIMIT_ORDER,
                OrderType.STOP_MARKET: TransactionType.STOP_ORDER,
                OrderType.STOP_LIMIT: TransactionType.STOP_LIMIT_ORDER
            }
            
            transaction_id = f"{legacy_order.id}_{fill_event.time.strftime('%Y%m%d_%H%M%S')}"
            
            transaction = Transaction(
                id=0,  # Will be set by repository
                portfolio_id=1,  # Default portfolio
                holding_id=1,  # Default holding  
                order_id=domain_order_id,
                date=fill_event.time,
                transaction_type=transaction_type_mapping.get(legacy_order.order_type, TransactionType.MARKET_ORDER),
                transaction_id=transaction_id,
                account_id=self._default_account_id,
                trade_date=fill_event.time.date(),
                value_date=fill_event.time.date(),
                settlement_date=fill_event.time.date(),
                status=TransactionStatus.EXECUTED if fill_event.status == OrderStatus.FILLED else TransactionStatus.PARTIALLY_FILLED,
                spread=0.0,  # Could be calculated from slippage
                currency_id=1,  # USD
                exchange_id=1,  # Default exchange
                external_transaction_id=f"FILL_{fill_event.order_id}_{fill_event.time.timestamp()}"
            )
            
            return transaction
            
        except Exception as e:
            self._logger.error(f"Error creating transaction: {e}")
            return None
    
    def _persist_transaction(self, transaction: Transaction) -> Optional[Transaction]:
        """Persist transaction entity."""
        try:
            if not self._transaction_repo:
                return None
            
            persisted_transaction = self._transaction_repo.add(transaction)
            if persisted_transaction:
                self._logger.debug(f"Persisted transaction {transaction.transaction_id}")
            
            return persisted_transaction
            
        except Exception as e:
            self._logger.error(f"Error persisting transaction: {e}")
            return None
    
    def _update_domain_order_status(self, legacy_order: LegacyOrder) -> None:
        """Update domain order status to match legacy order."""
        try:
            if not self._order_repo:
                return
            
            domain_order_id = self._legacy_to_domain_id_mapping.get(legacy_order.id)
            if not domain_order_id:
                return
            
            domain_order = self._domain_orders.get(domain_order_id)
            if not domain_order:
                domain_order = self._order_repo.get_by_id(domain_order_id)
                if not domain_order:
                    return
            
            # Map status
            status_mapping = {
                OrderStatus.NEW: DomainOrderStatus.PENDING,
                OrderStatus.SUBMITTED: DomainOrderStatus.SUBMITTED,
                OrderStatus.PARTIAL_FILLED: DomainOrderStatus.PARTIALLY_FILLED,
                OrderStatus.FILLED: DomainOrderStatus.FILLED,
                OrderStatus.CANCELED: DomainOrderStatus.CANCELLED,
                OrderStatus.INVALID: DomainOrderStatus.REJECTED
            }
            
            new_status = status_mapping.get(legacy_order.status)
            if new_status and domain_order.status != new_status:
                # Update domain order
                domain_order.status = new_status
                domain_order.filled_quantity = float(legacy_order.quantity_filled)
                domain_order.average_fill_price = legacy_order.average_fill_price if legacy_order.average_fill_price > 0 else None
                
                # Persist changes
                updated_order = self._order_repo.update(domain_order)
                if updated_order:
                    self._domain_orders[domain_order_id] = updated_order
                    self._logger.debug(f"Updated domain order {domain_order_id} status to {new_status}")
            
        except Exception as e:
            self._logger.error(f"Error updating domain order status: {e}")
    
    def _integrate_fill_with_entities(self, legacy_order: LegacyOrder, fill_event: OrderEvent) -> None:
        """Integrate order fill with domain entities."""
        try:
            # Update domain order status
            self._update_domain_order_status(legacy_order)
            
            # Create and persist transaction for the fill
            if fill_event.is_fill():
                transaction = self._create_transaction_from_fill(legacy_order, fill_event)
                if transaction:
                    persisted_transaction = self._persist_transaction(transaction)
                    if persisted_transaction:
                        self._logger.debug(f"Created transaction {persisted_transaction.transaction_id} for fill")
                        
        except Exception as e:
            self._logger.error(f"Error integrating fill with entities: {e}")


class BacktestingTransactionHandler(BaseTransactionHandler):
    """Transaction handler for backtesting with simulated execution."""
    
    def __init__(self, account_repo=None, order_repo=None, transaction_repo=None, default_account_id: str = "BACKTEST_ACCOUNT"):
        """Initialize the backtesting transaction handler."""
        super().__init__(account_repo, order_repo, transaction_repo, default_account_id)
        self._simulation_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._market_prices: Dict[Symbol, Decimal] = {}
        
        # Backtesting configuration
        self._slippage_percent = Decimal('0.001')  # 0.1% slippage
        self._commission_per_share = Decimal('0.01')  # $0.01 per share
        self._fill_delay_seconds = 0.1  # Simulation delay
    
    def _initialize_specific(self) -> None:
        """Initialize backtesting specific components."""
        try:
            self._logger.info("Initializing backtesting transaction handler")
            
            # Start order simulation thread
            self._start_simulation()
            
        except Exception as e:
            self._logger.error(f"Backtesting transaction handler initialization failed: {e}")
            raise
    
    def _process_order_specific(self, order: Order) -> bool:
        """Process order in backtesting mode."""
        try:
            # Set order status to submitted
            order.status = OrderStatus.SUBMITTED
            
            # Create submission event
            submission_event = OrderEvent(
                order_id=order.id,
                symbol=order.symbol,
                time=datetime.utcnow(),
                status=OrderStatus.SUBMITTED,
                direction=order.direction,
                fill_quantity=0,
                fill_price=0,
                message="Order submitted for backtesting"
            )
            
            self._order_events.append(submission_event)
            
            # Notify algorithm
            if self._algorithm:
                self._algorithm.on_order_event(submission_event)
            
            self._logger.info(f"Order {order.id} submitted for backtesting")
            return True
            
        except Exception as e:
            self._logger.error(f"Error processing backtesting order: {e}")
            return False
    
    def _cancel_order_specific(self, order: Order) -> bool:
        """Cancel order in backtesting mode."""
        try:
            order.status = OrderStatus.CANCELED
            
            # Create cancellation event
            cancellation_event = OrderEvent(
                order_id=order.id,
                symbol=order.symbol,
                time=datetime.utcnow(),
                status=OrderStatus.CANCELED,
                direction=order.direction,
                fill_quantity=0,
                fill_price=0,
                message="Order cancelled"
            )
            
            self._process_fill(cancellation_event)
            
            self._logger.info(f"Order {order.id} cancelled in backtesting")
            return True
            
        except Exception as e:
            self._logger.error(f"Error cancelling backtesting order: {e}")
            return False
    
    def _update_order_specific(self, order: Order) -> bool:
        """Update order in backtesting mode."""
        try:
            # Update the stored order
            self._orders[order.id] = order
            
            self._logger.info(f"Order {order.id} updated in backtesting")
            return True
            
        except Exception as e:
            self._logger.error(f"Error updating backtesting order: {e}")
            return False
    
    def update_market_price(self, symbol: Symbol, price: Decimal) -> None:
        """Update market price for a symbol."""
        with self._lock:
            self._market_prices[symbol] = price
    
    def _start_simulation(self) -> None:
        """Start the order simulation thread."""
        try:
            self._shutdown_event.clear()
            self._simulation_thread = threading.Thread(
                target=self._simulation_loop,
                name="OrderSimulationThread"
            )
            self._simulation_thread.daemon = True
            self._simulation_thread.start()
            
        except Exception as e:
            self._logger.error(f"Error starting simulation: {e}")
    
    def _stop_simulation(self) -> None:
        """Stop the order simulation thread."""
        try:
            self._shutdown_event.set()
            
            if self._simulation_thread and self._simulation_thread.is_alive():
                self._simulation_thread.join(timeout=5.0)
            
        except Exception as e:
            self._logger.error(f"Error stopping simulation: {e}")
    
    def _simulation_loop(self) -> None:
        """Main simulation loop for order execution."""
        try:
            self._logger.info("Order simulation loop started")
            
            while not self._shutdown_event.is_set():
                try:
                    # Process pending orders
                    with self._lock:
                        pending_orders = self._pending_orders.copy()
                        self._pending_orders.clear()
                    
                    for order in pending_orders:
                        if self._shutdown_event.is_set():
                            break
                        
                        self._simulate_order_execution(order)
                    
                    # Sleep briefly
                    time.sleep(0.1)
                    
                except Exception as e:
                    self._logger.error(f"Error in simulation loop: {e}")
                    time.sleep(1.0)
            
            self._logger.info("Order simulation loop stopped")
            
        except Exception as e:
            self._logger.error(f"Fatal error in simulation loop: {e}")
    
    def _simulate_order_execution(self, order: Order) -> None:
        """Simulate execution of an order."""
        try:
            # Skip if order is no longer open
            if order.status not in [OrderStatus.NEW, OrderStatus.SUBMITTED]:
                return
            
            # Get market price
            market_price = self._market_prices.get(order.symbol)
            if market_price is None:
                # Use a default price for simulation
                market_price = Decimal('100.0')
            
            # Determine if order should fill
            should_fill = self._should_fill_order(order, market_price)
            
            if should_fill:
                fill_price = self._calculate_fill_price(order, market_price)
                self._execute_order_fill(order, fill_price, order.quantity)
            
        except Exception as e:
            self._logger.error(f"Error simulating order execution: {e}")
    
    def _should_fill_order(self, order: Order, market_price: Decimal) -> bool:
        """Determine if an order should be filled at the current market price."""
        try:
            if order.order_type == OrderType.MARKET:
                return True
            elif order.order_type == OrderType.LIMIT:
                if order.direction == OrderDirection.BUY:
                    return market_price <= order.limit_price
                else:
                    return market_price >= order.limit_price
            elif order.order_type == OrderType.STOP_MARKET:
                if order.direction == OrderDirection.BUY:
                    return market_price >= order.stop_price
                else:
                    return market_price <= order.stop_price
            
            return False
            
        except Exception as e:
            self._logger.error(f"Error determining order fill: {e}")
            return False
    
    def _calculate_fill_price(self, order: Order, market_price: Decimal) -> Decimal:
        """Calculate the fill price including slippage."""
        try:
            slippage_adjustment = market_price * self._slippage_percent
            
            if order.direction == OrderDirection.BUY:
                # Buy orders pay slippage
                fill_price = market_price + slippage_adjustment
            else:
                # Sell orders receive slippage reduction
                fill_price = market_price - slippage_adjustment
            
            # Apply order type constraints
            if order.order_type == OrderType.LIMIT:
                if order.direction == OrderDirection.BUY:
                    fill_price = min(fill_price, order.limit_price)
                else:
                    fill_price = max(fill_price, order.limit_price)
            
            return fill_price
            
        except Exception as e:
            self._logger.error(f"Error calculating fill price: {e}")
            return market_price
    
    def _execute_order_fill(self, order: Order, fill_price: Decimal, fill_quantity: int) -> None:
        """Execute an order fill."""
        try:
            # Add simulation delay
            time.sleep(self._fill_delay_seconds)
            
            # Create fill event
            fill_event = self._create_fill_event(order, fill_price, fill_quantity, "Backtesting fill")
            
            # Process the fill
            self._process_fill(fill_event)
            
        except Exception as e:
            self._logger.error(f"Error executing order fill: {e}")
    
    def dispose(self) -> None:
        """Dispose of backtesting transaction handler resources."""
        try:
            self._stop_simulation()
            
        except Exception as e:
            self._logger.error(f"Error disposing backtesting transaction handler: {e}")


class BrokerageTransactionHandler(BaseTransactionHandler):
    """Transaction handler for live trading with brokerage integration."""
    
    def __init__(self, account_repo=None, order_repo=None, transaction_repo=None, default_account_id: str = "LIVE_ACCOUNT"):
        """Initialize the brokerage transaction handler."""
        super().__init__(account_repo, order_repo, transaction_repo, default_account_id)
        self._order_monitoring_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        
        # Live trading configuration
        self._order_timeout_minutes = 5
        self._max_retries = 3
    
    def _initialize_specific(self) -> None:
        """Initialize brokerage specific components."""
        try:
            self._logger.info("Initializing brokerage transaction handler")
            
            # Verify brokerage connection
            if self._brokerage and not self._brokerage.is_connected():
                if not self._brokerage.connect():
                    raise RuntimeError("Failed to connect to brokerage")
            
            # Start order monitoring
            self._start_monitoring()
            
        except Exception as e:
            self._logger.error(f"Brokerage transaction handler initialization failed: {e}")
            raise
    
    def _process_order_specific(self, order: Order) -> bool:
        """Process order with live brokerage."""
        try:
            if not self._brokerage:
                self._logger.error("No brokerage configured for live trading")
                return False
            
            # Place order with brokerage
            success = self._brokerage.place_order(order)
            
            if success:
                order.status = OrderStatus.SUBMITTED
                self._logger.info(f"Order {order.id} submitted to brokerage")
            else:
                self._reject_order(order, "Brokerage rejected order")
            
            return success
            
        except Exception as e:
            self._logger.error(f"Error processing brokerage order: {e}")
            return False
    
    def _cancel_order_specific(self, order: Order) -> bool:
        """Cancel order with live brokerage."""
        try:
            if not self._brokerage:
                return False
            
            success = self._brokerage.cancel_order(order)
            
            if success:
                order.status = OrderStatus.CANCELED
                self._logger.info(f"Order {order.id} cancelled with brokerage")
            
            return success
            
        except Exception as e:
            self._logger.error(f"Error cancelling brokerage order: {e}")
            return False
    
    def _update_order_specific(self, order: Order) -> bool:
        """Update order with live brokerage."""
        try:
            if not self._brokerage:
                return False
            
            success = self._brokerage.update_order(order)
            
            if success:
                self._orders[order.id] = order
                self._logger.info(f"Order {order.id} updated with brokerage")
            
            return success
            
        except Exception as e:
            self._logger.error(f"Error updating brokerage order: {e}")
            return False
    
    def _start_monitoring(self) -> None:
        """Start order monitoring thread."""
        try:
            self._shutdown_event.clear()
            self._order_monitoring_thread = threading.Thread(
                target=self._monitoring_loop,
                name="OrderMonitoringThread"
            )
            self._order_monitoring_thread.daemon = True
            self._order_monitoring_thread.start()
            
        except Exception as e:
            self._logger.error(f"Error starting monitoring: {e}")
    
    def _stop_monitoring(self) -> None:
        """Stop order monitoring thread."""
        try:
            self._shutdown_event.set()
            
            if self._order_monitoring_thread and self._order_monitoring_thread.is_alive():
                self._order_monitoring_thread.join(timeout=5.0)
            
        except Exception as e:
            self._logger.error(f"Error stopping monitoring: {e}")
    
    def _monitoring_loop(self) -> None:
        """Monitor orders with the brokerage."""
        try:
            self._logger.info("Order monitoring loop started")
            
            while not self._shutdown_event.is_set():
                try:
                    # Check order status with brokerage
                    # This would typically poll the brokerage for order updates
                    time.sleep(5.0)  # Check every 5 seconds
                    
                except Exception as e:
                    self._logger.error(f"Error in monitoring loop: {e}")
                    time.sleep(10.0)
            
            self._logger.info("Order monitoring loop stopped")
            
        except Exception as e:
            self._logger.error(f"Fatal error in monitoring loop: {e}")
    
    def dispose(self) -> None:
        """Dispose of brokerage transaction handler resources."""
        try:
            self._stop_monitoring()
            
            if self._brokerage:
                self._brokerage.disconnect()
            
        except Exception as e:
            self._logger.error(f"Error disposing brokerage transaction handler: {e}")


class TransactionHandlerFactory:
    """Factory for creating transaction handlers with repository dependencies."""
    
    @staticmethod
    def create_backtesting_handler(account_repo=None, order_repo=None, transaction_repo=None, 
                                 account_id: str = "BACKTEST_ACCOUNT") -> BacktestingTransactionHandler:
        """Create a backtesting transaction handler with repository dependencies."""
        return BacktestingTransactionHandler(account_repo, order_repo, transaction_repo, account_id)
    
    @staticmethod
    def create_brokerage_handler(account_repo=None, order_repo=None, transaction_repo=None,
                               account_id: str = "LIVE_ACCOUNT") -> BrokerageTransactionHandler:
        """Create a brokerage transaction handler with repository dependencies."""
        return BrokerageTransactionHandler(account_repo, order_repo, transaction_repo, account_id)
    
    @staticmethod
    def create_handler_with_local_repositories(handler_type: str = "backtesting", 
                                             session=None, factory=None) -> BaseTransactionHandler:
        """
        Create a transaction handler with local repository implementations.
        
        Args:
            handler_type: Type of handler ("backtesting" or "brokerage")
            session: SQLAlchemy session for repositories
            factory: Repository factory instance
            
        Returns:
            Configured transaction handler
        """
        if not session or not factory:
            # Return handler without repository integration
            if handler_type == "backtesting":
                return BacktestingTransactionHandler()
            else:
                return BrokerageTransactionHandler()
        
        try:
            # Import repository classes
            from src.infrastructure.repositories.local_repo.finance.account_repository import AccountRepository
            from src.infrastructure.repositories.local_repo.finance.order.order_repository import OrderRepository  
            from src.infrastructure.repositories.local_repo.finance.transaction.transaction_repository import TransactionRepository
            
            # Create repository instances
            account_repo = AccountRepository(session, factory)
            order_repo = OrderRepository(session, factory)
            transaction_repo = TransactionRepository(session, factory)
            
            # Create handler with repositories
            if handler_type == "backtesting":
                return BacktestingTransactionHandler(account_repo, order_repo, transaction_repo)
            else:
                return BrokerageTransactionHandler(account_repo, order_repo, transaction_repo)
                
        except ImportError as e:
            # Fallback to handler without repositories
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Could not import repositories, creating handler without entity integration: {e}")
            
            if handler_type == "backtesting":
                return BacktestingTransactionHandler()
            else:
                return BrokerageTransactionHandler()