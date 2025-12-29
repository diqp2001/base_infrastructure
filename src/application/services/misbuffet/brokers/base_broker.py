"""
Base broker implementation following QuantConnect Lean architecture.

This module provides the abstract base class for all broker implementations,
defining the contract that concrete brokers must follow.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
import logging

from application.services.misbuffet.algorithm.order import Order, OrderEvent
from application.services.misbuffet.algorithm.symbol import Symbol
#from application.services.misbuffet.common.symbol import Symbol
from domain.entities.finance.holding.holding import Holding


from ..engine.interfaces import IBrokerage


class BrokerStatus(Enum):
    """Broker connection and operational status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting" 
    CONNECTED = "connected"
    AUTHENTICATED = "authenticated"
    READY = "ready"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class BrokerConnectionState(Enum):
    """Detailed connection state for broker."""
    OFFLINE = "offline"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    LOGGED_IN = "logged_in"
    READY_TO_TRADE = "ready_to_trade"
    CONNECTION_LOST = "connection_lost"
    AUTHENTICATION_FAILED = "authentication_failed"
    ERROR_STATE = "error_state"


class BaseBroker(IBrokerage, ABC):
    """
    Abstract base class for all broker implementations.
    
    This class provides the foundation for broker integrations, implementing
    common functionality and defining the interface that all brokers must follow.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the base broker.
        
        Args:
            config: Broker configuration dictionary
        """
        self.config = config
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Connection state
        self.status = BrokerStatus.DISCONNECTED
        self.connection_state = BrokerConnectionState.OFFLINE
        self.last_heartbeat = None
        
        # Order and position tracking
        self.orders: Dict[int, Order] = {}
        self.holdings: Dict[Symbol, 'Holding'] = {}
        self.cash_balance: Dict[str, Decimal] = {"USD": Decimal("0")}
        
        # Event handlers
        self.order_event_handlers: List[Callable[[OrderEvent], None]] = []
        self.connection_event_handlers: List[Callable[[BrokerConnectionState], None]] = []
        self.error_event_handlers: List[Callable[[str, Exception], None]] = []
        
        # Configuration validation
        self._validate_config()
    
    def _validate_config(self) -> None:
        """Validate broker configuration."""
        required_fields = self.get_required_config_fields()
        missing_fields = [field for field in required_fields if field not in self.config]
        
        if missing_fields:
            raise ValueError(f"Missing required configuration fields: {missing_fields}")
    
    @abstractmethod
    def get_required_config_fields(self) -> List[str]:
        """Return list of required configuration fields for this broker."""
        pass
    
    # IBrokerage interface implementation
    
    def connect(self) -> bool:
        """
        Connect to the broker.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.logger.info(f"Connecting to {self.__class__.__name__}...")
            self.status = BrokerStatus.CONNECTING
            self.connection_state = BrokerConnectionState.CONNECTING
            
            success = self._connect_impl()
            
            if success:
                self.status = BrokerStatus.CONNECTED
                self.connection_state = BrokerConnectionState.CONNECTED
                self.last_heartbeat = datetime.now()
                self.logger.info("Broker connection established")
                self._notify_connection_event(self.connection_state)
            else:
                self.status = BrokerStatus.ERROR
                self.connection_state = BrokerConnectionState.ERROR_STATE
                self.logger.error("Failed to connect to broker")
                
            return success
            
        except Exception as e:
            self.logger.error(f"Error connecting to broker: {e}")
            self.status = BrokerStatus.ERROR
            self.connection_state = BrokerConnectionState.ERROR_STATE
            self._notify_error_event("Connection failed", e)
            return False
    
    def disconnect(self) -> None:
        """Disconnect from the broker."""
        try:
            self.logger.info("Disconnecting from broker...")
            self._disconnect_impl()
            
            self.status = BrokerStatus.DISCONNECTED
            self.connection_state = BrokerConnectionState.OFFLINE
            self.last_heartbeat = None
            
            self.logger.info("Broker disconnected")
            self._notify_connection_event(self.connection_state)
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from broker: {e}")
            self._notify_error_event("Disconnection failed", e)
    
    def is_connected(self) -> bool:
        """Check if connected to the broker."""
        return self.status in [BrokerStatus.CONNECTED, BrokerStatus.AUTHENTICATED, BrokerStatus.READY]
    
    def place_order(self, order: Order) -> bool:
        """
        Place an order with the broker.
        
        Args:
            order: Order to place
            
        Returns:
            True if order placed successfully, False otherwise
        """
        if not self.is_connected():
            self.logger.error("Cannot place order - not connected to broker")
            return False
        
        try:
            self.logger.info(f"Placing order: {order.symbol} {order.quantity} {order.type}")
            
            # Validate order
            if not self._validate_order(order):
                return False
            
            # Store order
            self.orders[order.id] = order
            
            # Place order with broker
            success = self._place_order_impl(order)
            
            if success:
                self.logger.info(f"Order placed successfully: {order.id}")
            else:
                self.logger.error(f"Failed to place order: {order.id}")
                del self.orders[order.id]
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error placing order: {e}")
            self._notify_error_event("Order placement failed", e)
            return False
    
    def update_order(self, order: Order) -> bool:
        """Update an existing order."""
        if not self.is_connected():
            self.logger.error("Cannot update order - not connected to broker")
            return False
        
        if order.id not in self.orders:
            self.logger.error(f"Cannot update order - order not found: {order.id}")
            return False
        
        try:
            success = self._update_order_impl(order)
            
            if success:
                self.orders[order.id] = order
                self.logger.info(f"Order updated successfully: {order.id}")
            else:
                self.logger.error(f"Failed to update order: {order.id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error updating order: {e}")
            self._notify_error_event("Order update failed", e)
            return False
    
    def cancel_order(self, order: Order) -> bool:
        """Cancel an order."""
        if not self.is_connected():
            self.logger.error("Cannot cancel order - not connected to broker")
            return False
        
        if order.id not in self.orders:
            self.logger.error(f"Cannot cancel order - order not found: {order.id}")
            return False
        
        try:
            success = self._cancel_order_impl(order)
            
            if success:
                self.logger.info(f"Order cancelled successfully: {order.id}")
            else:
                self.logger.error(f"Failed to cancel order: {order.id}")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error cancelling order: {e}")
            self._notify_error_event("Order cancellation failed", e)
            return False
    
    def get_cash_balance(self) -> Dict[str, Decimal]:
        """Get cash balances by currency."""
        return self.cash_balance.copy()
    
    def get_holdings(self) -> Dict[Symbol, 'Holding']:
        """Get current holdings.""" 
        return self.holdings.copy()
    
    # Abstract methods that concrete brokers must implement
    
    @abstractmethod
    def _connect_impl(self) -> bool:
        """Broker-specific connection implementation."""
        pass
    
    @abstractmethod
    def _disconnect_impl(self) -> None:
        """Broker-specific disconnection implementation."""
        pass
    
    @abstractmethod
    def _place_order_impl(self, order: Order) -> bool:
        """Broker-specific order placement implementation."""
        pass
    
    @abstractmethod
    def _update_order_impl(self, order: Order) -> bool:
        """Broker-specific order update implementation."""
        pass
    
    @abstractmethod
    def _cancel_order_impl(self, order: Order) -> bool:
        """Broker-specific order cancellation implementation."""
        pass
    
    @abstractmethod
    def _update_account_info(self) -> None:
        """Update account information from broker."""
        pass
    
    # Helper methods
    
    def _validate_order(self, order: Order) -> bool:
        """Validate order before placing."""
        if order.quantity == 0:
            self.logger.error("Invalid order - zero quantity")
            return False
        
        if not order.symbol:
            self.logger.error("Invalid order - missing symbol")
            return False
        
        return True
    
    def _notify_order_event(self, order_event: OrderEvent) -> None:
        """Notify order event handlers."""
        for handler in self.order_event_handlers:
            try:
                handler(order_event)
            except Exception as e:
                self.logger.error(f"Error in order event handler: {e}")
    
    def _notify_connection_event(self, state: BrokerConnectionState) -> None:
        """Notify connection event handlers."""
        for handler in self.connection_event_handlers:
            try:
                handler(state)
            except Exception as e:
                self.logger.error(f"Error in connection event handler: {e}")
    
    def _notify_error_event(self, message: str, exception: Exception) -> None:
        """Notify error event handlers."""
        for handler in self.error_event_handlers:
            try:
                handler(message, exception)
            except Exception as e:
                self.logger.error(f"Error in error event handler: {e}")
    
    # Event handler management
    
    def add_order_event_handler(self, handler: Callable[[OrderEvent], None]) -> None:
        """Add order event handler."""
        self.order_event_handlers.append(handler)
    
    def add_connection_event_handler(self, handler: Callable[[BrokerConnectionState], None]) -> None:
        """Add connection event handler."""
        self.connection_event_handlers.append(handler)
    
    def add_error_event_handler(self, handler: Callable[[str, Exception], None]) -> None:
        """Add error event handler."""
        self.error_event_handlers.append(handler)
    
    def remove_order_event_handler(self, handler: Callable[[OrderEvent], None]) -> None:
        """Remove order event handler."""
        if handler in self.order_event_handlers:
            self.order_event_handlers.remove(handler)
    
    def remove_connection_event_handler(self, handler: Callable[[BrokerConnectionState], None]) -> None:
        """Remove connection event handler."""
        if handler in self.connection_event_handlers:
            self.connection_event_handlers.remove(handler)
    
    def remove_error_event_handler(self, handler: Callable[[str, Exception], None]) -> None:
        """Remove error event handler."""
        if handler in self.error_event_handlers:
            self.error_event_handlers.remove(handler)