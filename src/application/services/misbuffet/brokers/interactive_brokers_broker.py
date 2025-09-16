"""
Interactive Brokers broker implementation for the Misbuffet trading framework.

This module provides the Interactive Brokers brokerage integration following
the QuantConnect Lean architecture pattern, enabling live trading through IB TWS or Gateway.
"""

import time
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any, Callable
import logging

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order as IBOrder
from ibapi.common import OrderId, TickerId

from .base_broker import BaseBroker, BrokerStatus, BrokerConnectionState
from ..common import Symbol, Order, OrderEvent
from ..common.enums import OrderType, OrderStatus, OrderDirection


class IBTWSClient(EWrapper, EClient):
    """
    Interactive Brokers TWS API client implementation.
    
    This class implements the IB TWS API using the official ibapi library,
    providing real connection and trading functionality.
    """
    
    def __init__(self, host: str, port: int, client_id: int):
        EClient.__init__(self, self)
        EWrapper.__init__(self)
        
        self.host = host
        self.port = port
        self.client_id = client_id
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        
        # Connection state
        self.connected_flag = False
        self.authenticated_flag = False
        self.error_occurred = False
        
        # Account data
        self.account_summary = {}
        self.positions = []
        self.next_order_id = 1
        
        # Order tracking
        self.order_status = {}
        self.order_fills = {}
        
        # Market data
        self.market_data = {}
        
        # Threading for message processing
        self.msg_queue_lock = threading.Lock()
        self.connection_event = threading.Event()
    
    # EWrapper callback methods
    
    def connectAck(self):
        """Connection acknowledgement callback."""
        self.logger.info("TWS connection acknowledged")
    
    def connectionClosed(self):
        """Connection closed callback."""
        self.logger.info("TWS connection closed")
        self.connected_flag = False
        self.authenticated_flag = False
    
    def nextValidId(self, orderId: int):
        """Next valid order ID callback."""
        self.logger.info(f"Next valid order ID: {orderId}")
        self.next_order_id = orderId
        self.connected_flag = True
        self.authenticated_flag = True
        self.connection_event.set()
    
    def error(self, reqId: TickerId, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        """Error callback."""
        if errorCode in [2104, 2106, 2158]:  # Market data warnings
            self.logger.info(f"Market data info ({errorCode}): {errorString}")
        elif errorCode < 1000:  # System errors
            self.logger.error(f"TWS Error {errorCode}: {errorString}")
            self.error_occurred = True
        else:
            self.logger.warning(f"TWS Warning {errorCode}: {errorString}")
    
    def orderStatus(self, orderId: OrderId, status: str, filled: float, remaining: float,
                   avgFillPrice: float, permId: int, parentId: int, lastFillPrice: float,
                   clientId: int, whyHeld: str, mktCapPrice: float):
        """Order status callback."""
        self.order_status[orderId] = {
            'status': status,
            'filled': filled,
            'remaining': remaining,
            'avgFillPrice': avgFillPrice,
            'permId': permId
        }
        self.logger.info(f"Order {orderId} status: {status}, filled: {filled}, remaining: {remaining}")
    
    def execDetails(self, reqId: int, contract: Contract, execution):
        """Execution details callback."""
        order_id = execution.orderId
        if order_id not in self.order_fills:
            self.order_fills[order_id] = []
        
        self.order_fills[order_id].append({
            'execId': execution.execId,
            'time': execution.time,
            'shares': execution.shares,
            'price': execution.price,
            'side': execution.side
        })
        
        self.logger.info(f"Execution: Order {order_id}, {execution.shares} @ {execution.price}")
    
    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        """Account summary callback."""
        self.account_summary[tag] = {
            'value': value,
            'currency': currency,
            'account': account
        }
    
    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        """Position callback."""
        position_data = {
            'account': account,
            'symbol': contract.symbol,
            'secType': contract.secType,
            'exchange': contract.exchange,
            'position': position,
            'avgCost': avgCost
        }
        
        # Update or add position
        existing_pos = next((p for p in self.positions 
                           if p['symbol'] == contract.symbol and p['account'] == account), None)
        if existing_pos:
            existing_pos.update(position_data)
        else:
            self.positions.append(position_data)
    
    def tickPrice(self, reqId: TickerId, tickType: int, price: float, attrib):
        """Tick price callback for market data."""
        if reqId not in self.market_data:
            self.market_data[reqId] = {}
        self.market_data[reqId][f'tickType_{tickType}'] = price
    
    # Custom methods
    
    def connect_to_tws(self) -> bool:
        """Connect to TWS/Gateway."""
        try:
            self.logger.info(f"Connecting to TWS at {self.host}:{self.port} (client {self.client_id})")
            self.connect(self.host, self.port, self.client_id)
            
            # Start message processing thread
            api_thread = threading.Thread(target=self.run, daemon=True)
            api_thread.start()
            
            # Wait for connection confirmation
            if self.connection_event.wait(timeout=10):
                self.logger.info("Successfully connected to TWS")
                return True
            else:
                self.logger.error("Timeout waiting for TWS connection")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to connect to TWS: {e}")
            return False
    
    def disconnect_from_tws(self) -> None:
        """Disconnect from TWS."""
        try:
            self.logger.info("Disconnecting from TWS")
            self.disconnect()
            self.connected_flag = False
            self.authenticated_flag = False
        except Exception as e:
            self.logger.error(f"Error disconnecting from TWS: {e}")
    
    def is_connected(self) -> bool:
        """Check if connected to TWS."""
        return self.connected_flag and self.authenticated_flag and self.isConnected()
    
    def create_stock_contract(self, symbol: str, exchange: str = "SMART") -> Contract:
        """Create a stock contract."""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = exchange
        contract.currency = "USD"
        return contract
    
    def place_order(self, contract: Contract, order: IBOrder) -> int:
        """Place an order with TWS."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        
        order_id = self.next_order_id
        self.next_order_id += 1
        
        self.placeOrder(order_id, contract, order)
        self.logger.info(f"Placed order {order_id}: {contract.symbol} {order.action} {order.totalQuantity}")
        
        return order_id
    
    def cancel_order(self, order_id: int) -> None:
        """Cancel an order."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        
        self.cancelOrder(order_id, "")
        self.logger.info(f"Cancelled order {order_id}")
    
    def request_account_summary(self, account: str = "All") -> None:
        """Request account summary."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        
        tags = "TotalCashValue,NetLiquidation,BuyingPower,DayTradesRemaining"
        self.reqAccountSummary(1, account, tags)
    
    def request_positions(self) -> None:
        """Request all positions."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        
        self.reqPositions()
    
    def request_market_data(self, req_id: int, contract: Contract) -> None:
        """Request market data for a contract."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        
        self.reqMktData(req_id, contract, "", False, False, [])
    
    def create_limit_order(self, action: str, quantity: int, limit_price: float) -> IBOrder:
        """Create a limit order."""
        order = IBOrder()
        order.action = action
        order.totalQuantity = quantity
        order.orderType = "LMT"
        order.lmtPrice = limit_price
        return order
    
    def create_market_order(self, action: str, quantity: int) -> IBOrder:
        """Create a market order."""
        order = IBOrder()
        order.action = action
        order.totalQuantity = quantity
        order.orderType = "MKT"
        return order


class InteractiveBrokersBroker(BaseBroker):
    """
    Interactive Brokers broker implementation.
    
    This class provides integration with Interactive Brokers TWS or Gateway
    for live trading operations. It follows the QuantConnect Lean architecture
    and implements the IBrokerage interface.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Interactive Brokers broker.
        
        Args:
            config: Configuration dictionary with IB connection details
        """
        super().__init__(config)
        
        # IB-specific configuration
        self.host = config.get('host', '127.0.0.1')
        self.port = config.get('port', 7497)  # 7497 for paper, 7496 for live
        self.client_id = config.get('client_id', 1)
        self.timeout = config.get('timeout', 60)
        
        # Connection and monitoring
        self.ib_connection: Optional[IBTWSClient] = None
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_monitoring = threading.Event()
        
        # Order tracking
        self.next_order_id = 1
        self.pending_orders: Dict[int, Order] = {}
        
        # Account information
        self.account_id = config.get('account_id', 'DEFAULT')
        self.paper_trading = config.get('paper_trading', True)
        
        self.logger.info(f"Initialized IB Broker - Host: {self.host}:{self.port}, "
                        f"Client ID: {self.client_id}, Paper: {self.paper_trading}")
    
    def get_required_config_fields(self) -> List[str]:
        """Return required configuration fields for IB."""
        return ['host', 'port', 'client_id']
    
    def _connect_impl(self) -> bool:
        """Connect to Interactive Brokers TWS/Gateway."""
        try:
            # Create TWS API client
            self.ib_connection = IBTWSClient(self.host, self.port, self.client_id)
            
            # Establish connection
            if not self.ib_connection.connect_to_tws():
                return False
            
            # Wait a moment for connection to stabilize
            time.sleep(2)
            
            # Request initial account and position data
            self._update_account_info()
            
            # Start monitoring threads
            self._start_monitoring()
            
            self.connection_state = BrokerConnectionState.READY_TO_TRADE
            self.status = BrokerStatus.READY
            
            self.logger.info("Successfully connected to Interactive Brokers TWS")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to connect to Interactive Brokers: {e}")
            return False
    
    def _disconnect_impl(self) -> None:
        """Disconnect from Interactive Brokers."""
        try:
            # Stop monitoring
            self._stop_monitoring()
            
            # Disconnect from TWS
            if self.ib_connection:
                self.ib_connection.disconnect_from_tws()
                self.ib_connection = None
            
            self.logger.info("Disconnected from Interactive Brokers TWS")
            
        except Exception as e:
            self.logger.error(f"Error disconnecting from Interactive Brokers: {e}")
    
    def _place_order_impl(self, order: Order) -> bool:
        """Place order with Interactive Brokers."""
        if not self.ib_connection or not self.ib_connection.is_connected():
            self.logger.error("Cannot place order - not connected to TWS")
            return False
        
        try:
            # Create contract
            contract = self.ib_connection.create_stock_contract(order.symbol.value)
            
            # Convert order to IB format
            ib_action = "BUY" if order.direction == OrderDirection.BUY else "SELL"
            quantity = abs(order.quantity)
            
            # Create IB order based on type
            if order.type == OrderType.MARKET:
                ib_order = self.ib_connection.create_market_order(ib_action, quantity)
            elif order.type == OrderType.LIMIT:
                if not hasattr(order, 'limit_price') or order.limit_price is None:
                    self.logger.error("Limit price required for limit order")
                    return False
                ib_order = self.ib_connection.create_limit_order(ib_action, quantity, float(order.limit_price))
            else:
                self.logger.error(f"Unsupported order type: {order.type}")
                return False
            
            # Place order with TWS
            ib_order_id = self.ib_connection.place_order(contract, ib_order)
            
            # Track pending order
            self.pending_orders[ib_order_id] = order
            
            self.logger.info(f"Order placed with TWS: {order.id} -> TWS Order {ib_order_id}")
            return True
                
        except Exception as e:
            self.logger.error(f"Error placing order with TWS: {e}")
            return False
    
    def _update_order_impl(self, order: Order) -> bool:
        """Update order with Interactive Brokers."""
        # IB typically requires cancelling and re-placing for most updates
        self.logger.warning("Order updates not implemented - use cancel and re-place")
        return False
    
    def _cancel_order_impl(self, order: Order) -> bool:
        """Cancel order with Interactive Brokers."""
        if not self.ib_connection or not self.ib_connection.is_connected():
            return False
        
        try:
            # Find TWS order ID
            ib_order_id = None
            for pending_id, pending_order in self.pending_orders.items():
                if pending_order.id == order.id:
                    ib_order_id = pending_id
                    break
            
            if ib_order_id is None:
                self.logger.error(f"Cannot cancel order - TWS order ID not found: {order.id}")
                return False
            
            # Cancel with TWS
            self.ib_connection.cancel_order(ib_order_id)
            
            # Remove from pending orders
            del self.pending_orders[ib_order_id]
            
            self.logger.info(f"Order cancellation requested: {order.id} -> TWS Order {ib_order_id}")
            return True
                
        except Exception as e:
            self.logger.error(f"Error cancelling order with TWS: {e}")
            return False
    
    def _update_account_info(self) -> None:
        """Update account information from Interactive Brokers."""
        if not self.ib_connection or not self.ib_connection.is_connected():
            return
        
        try:
            # Request account summary from TWS
            self.ib_connection.request_account_summary(self.account_id)
            
            # Request positions from TWS
            self.ib_connection.request_positions()
            
            # Give time for data to arrive
            time.sleep(1)
            
            # Update cash balance from account summary
            if 'TotalCashValue' in self.ib_connection.account_summary:
                cash_value = self.ib_connection.account_summary['TotalCashValue']['value']
                self.cash_balance['USD'] = Decimal(cash_value)
                
                # Log account info
                account_summary = self.ib_connection.account_summary
                net_liq = account_summary.get('NetLiquidation', {}).get('value', '0')
                buying_power = account_summary.get('BuyingPower', {}).get('value', '0')
                
                self.logger.info(f"Account updated - Cash: ${cash_value}, "
                               f"Net Liquidation: ${net_liq}, "
                               f"Buying Power: ${buying_power}")
            
            # Clear and update holdings from positions
            self.holdings.clear()
            
            for position in self.ib_connection.positions:
                if position['position'] != 0:  # Only include non-zero positions
                    symbol = Symbol(position['symbol'])
                    # In real implementation, convert TWS position to Holding object
                    # self.holdings[symbol] = Holding(...)
                    self.logger.info(f"Position: {position['symbol']} {position['position']} @ {position['avgCost']}")
            
        except Exception as e:
            self.logger.error(f"Error updating account info: {e}")
    
    def _convert_order_type(self, order_type: OrderType) -> str:
        """Convert framework order type to TWS order type."""
        type_mapping = {
            OrderType.MARKET: "MKT",
            OrderType.LIMIT: "LMT", 
            OrderType.STOP: "STP",
            OrderType.STOP_LIMIT: "STP LMT",
        }
        return type_mapping.get(order_type, "MKT")
    
    def _start_monitoring(self) -> None:
        """Start monitoring threads for IB connection."""
        self.stop_monitoring.clear()
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(
            target=self._heartbeat_worker,
            name="IB-Heartbeat",
            daemon=True
        )
        self.heartbeat_thread.start()
        
        # Start monitoring thread
        self.monitor_thread = threading.Thread(
            target=self._monitor_worker,
            name="IB-Monitor", 
            daemon=True
        )
        self.monitor_thread.start()
        
        self.logger.info("Started IB monitoring threads")
    
    def _stop_monitoring(self) -> None:
        """Stop monitoring threads."""
        self.stop_monitoring.set()
        
        # Wait for threads to stop
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=5)
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        self.logger.info("Stopped IB monitoring threads")
    
    def _heartbeat_worker(self) -> None:
        """Worker thread for maintaining heartbeat with IB."""
        while not self.stop_monitoring.is_set():
            try:
                if self.ib_connection and self.ib_connection.is_connected():
                    self.last_heartbeat = datetime.now()
                    
                    # Check TWS connection status
                    if not self.ib_connection.isConnected():
                        self.logger.warning("TWS connection lost in heartbeat check")
                        self.connection_state = BrokerConnectionState.CONNECTION_LOST
                    
                else:
                    self.logger.warning("TWS connection lost in heartbeat check")
                    self.connection_state = BrokerConnectionState.CONNECTION_LOST
                    
            except Exception as e:
                self.logger.error(f"Error in heartbeat worker: {e}")
            
            # Wait for next heartbeat
            if not self.stop_monitoring.wait(timeout=30):  # 30 second intervals
                continue
    
    def _monitor_worker(self) -> None:
        """Worker thread for monitoring IB events and updates."""
        while not self.stop_monitoring.is_set():
            try:
                # Process TWS API callbacks and updates
                # Order status updates are handled by the IBTWSClient callbacks
                
                # Periodic account updates
                if self.ib_connection and self.ib_connection.is_connected():
                    # Process any pending order status updates
                    self._process_order_updates()
                    
                    # Update account info less frequently
                    if datetime.now().second % 30 == 0:  # Every 30 seconds
                        self._update_account_info()
    
    def _process_order_updates(self) -> None:
        """Process order status updates from TWS."""
        if not self.ib_connection:
            return
        
        try:
            # Check order status updates from TWS client
            for ib_order_id, status_info in self.ib_connection.order_status.items():
                if ib_order_id in self.pending_orders:
                    order = self.pending_orders[ib_order_id]
                    
                    # Create order event based on status
                    status = status_info['status']
                    if status in ['Filled', 'Cancelled', 'Submitted']:
                        from ..common.enums import OrderStatus as FrameworkOrderStatus
                        
                        # Map TWS status to framework status
                        status_mapping = {
                            'Submitted': FrameworkOrderStatus.SUBMITTED,
                            'Filled': FrameworkOrderStatus.FILLED,
                            'Cancelled': FrameworkOrderStatus.CANCELLED
                        }
                        
                        framework_status = status_mapping.get(status, FrameworkOrderStatus.PENDING)
                        
                        order_event = OrderEvent(
                            order_id=order.id,
                            symbol=order.symbol,
                            status=framework_status,
                            quantity=order.quantity,
                            fill_price=Decimal(str(status_info.get('avgFillPrice', 0))),
                            fill_quantity=int(status_info.get('filled', 0)),
                            timestamp=datetime.now()
                        )
                        
                        self._notify_order_event(order_event)
                        
                        # Remove from pending if filled or cancelled
                        if status in ['Filled', 'Cancelled']:
                            del self.pending_orders[ib_order_id]
        
        except Exception as e:
            self.logger.error(f"Error processing order updates: {e}")
                    
            except Exception as e:
                self.logger.error(f"Error in monitor worker: {e}")
            
            # Wait before next update
            if not self.stop_monitoring.wait(timeout=5):  # 5 second intervals
                continue
    
    
    def get_broker_specific_info(self) -> Dict[str, Any]:
        """Get IB-specific broker information."""
        return {
            'broker_name': 'Interactive Brokers (TWS API)',
            'host': self.host,
            'port': self.port,
            'client_id': self.client_id,
            'paper_trading': self.paper_trading,
            'account_id': self.account_id,
            'connection_state': self.connection_state.value,
            'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            'pending_orders': len(self.pending_orders),
        }
    
    def get_market_hours(self) -> Dict[str, Any]:
        """Get market hours information from TWS."""
        # TODO: Implement market hours request from TWS API
        return {
            'market_open': '09:30:00 EST',
            'market_close': '16:00:00 EST', 
            'pre_market_open': '04:00:00 EST',
            'after_market_close': '20:00:00 EST',
            'timezone': 'America/New_York'
        }
    
    def is_market_open(self) -> bool:
        """Check if market is currently open."""
        # TODO: Use TWS API to get real-time market status
        now = datetime.now()
        
        # Simple check for weekdays 9:30 AM - 4:00 PM ET
        if now.weekday() >= 5:  # Weekend
            return False
        
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return market_open <= now <= market_close
    
    def get_order_book(self, symbol: str, depth: int = 5) -> Dict[str, Any]:
        """Get order book (Level 2) data for a symbol."""
        if not self.ib_connection or not self.ib_connection.is_connected():
            self.logger.error("Cannot get order book - not connected to TWS")
            return {}
        
        try:
            # Create contract for the symbol
            contract = self.ib_connection.create_stock_contract(symbol)
            
            # Request Level 2 market data
            req_id = hash(symbol) % 10000  # Simple req_id generation
            self.ib_connection.reqMktDepth(req_id, contract, depth, False, [])
            
            # Wait for data (in real implementation, this would be callback-based)
            time.sleep(2)
            
            # TODO: Implement proper order book data structure
            # For now, return placeholder structure
            return {
                'symbol': symbol,
                'bids': [],  # List of [price, size] pairs
                'asks': [],  # List of [price, size] pairs
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting order book for {symbol}: {e}")
            return {}
    
    def get_account_summary(self) -> Dict[str, Any]:
        """Get comprehensive account summary."""
        if not self.ib_connection or not self.ib_connection.is_connected():
            return {}
        
        try:
            # Request fresh account data
            self.ib_connection.request_account_summary(self.account_id)
            time.sleep(1)  # Wait for data
            
            account_data = {}
            for tag, data in self.ib_connection.account_summary.items():
                account_data[tag] = {
                    'value': data['value'],
                    'currency': data['currency']
                }
            
            return account_data
            
        except Exception as e:
            self.logger.error(f"Error getting account summary: {e}")
            return {}
    
    def get_positions_summary(self) -> List[Dict[str, Any]]:
        """Get detailed positions summary."""
        if not self.ib_connection or not self.ib_connection.is_connected():
            return []
        
        try:
            # Request fresh position data
            self.ib_connection.request_positions()
            time.sleep(1)  # Wait for data
            
            return [pos.copy() for pos in self.ib_connection.positions]
            
        except Exception as e:
            self.logger.error(f"Error getting positions summary: {e}")
            return []
    
    def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get real-time market data for a symbol."""
        if not self.ib_connection or not self.ib_connection.is_connected():
            return {}
        
        try:
            # Create contract
            contract = self.ib_connection.create_stock_contract(symbol)
            
            # Request market data
            req_id = hash(symbol) % 10000
            self.ib_connection.request_market_data(req_id, contract)
            
            # Wait for data
            time.sleep(2)
            
            # Get market data from client
            market_data = self.ib_connection.market_data.get(req_id, {})
            
            return {
                'symbol': symbol,
                'data': market_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting market data for {symbol}: {e}")
            return {}