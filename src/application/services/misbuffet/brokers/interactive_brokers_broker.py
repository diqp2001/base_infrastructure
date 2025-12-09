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
        self.managed_accounts = []  # Store managed accounts from IB
        self.next_order_id = 1
        
        # Order tracking
        self.order_status = {}
        self.order_fills = {}
        
        # Market data
        self.market_data = {}
        
        # Historical data
        self.historical_data = {}
        
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
    
    def managedAccounts(self, accountsList: str):
        """Managed accounts callback - receives list of managed accounts."""
        accounts = accountsList.split(',') if accountsList else []
        self.managed_accounts = [acc.strip() for acc in accounts if acc.strip()]
        self.logger.info(f"Managed accounts: {self.managed_accounts}")
        
        # Auto-select the first account if we don't have one set
        if self.managed_accounts and not hasattr(self, 'selected_account_id'):
            self.selected_account_id = self.managed_accounts[0]
            self.logger.info(f"Auto-selected account: {self.selected_account_id}")
    
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
            self.market_data[reqId] = {
                'prices': {},
                'sizes': {},
                'generic': {},
                'strings': {},
                'last_update': None
            }
        
        self.market_data[reqId]['prices'][tickType] = price
        self.market_data[reqId]['last_update'] = datetime.now().isoformat()
        
        # Log significant tick types for debugging
        tick_type_names = {
            1: 'BID', 2: 'ASK', 4: 'LAST', 6: 'HIGH', 7: 'LOW', 
            9: 'CLOSE', 14: 'OPEN', 15: 'LOW_13_WEEK', 16: 'HIGH_13_WEEK',
            17: 'LOW_26_WEEK', 18: 'HIGH_26_WEEK', 19: 'LOW_52_WEEK', 20: 'HIGH_52_WEEK'
        }
        
        if tickType in tick_type_names:
            self.logger.debug(f"Market data update - Req {reqId}: {tick_type_names[tickType]} = {price}")
    
    def tickSize(self, reqId: TickerId, tickType: int, size: int):
        """Tick size callback for market data."""
        if reqId not in self.market_data:
            self.market_data[reqId] = {
                'prices': {},
                'sizes': {},
                'generic': {},
                'strings': {},
                'last_update': None
            }
        
        self.market_data[reqId]['sizes'][tickType] = size
        self.market_data[reqId]['last_update'] = datetime.now().isoformat()
        
        # Log significant size tick types
        size_tick_names = {
            0: 'BID_SIZE', 3: 'ASK_SIZE', 5: 'LAST_SIZE', 8: 'VOLUME'
        }
        
        if tickType in size_tick_names:
            self.logger.debug(f"Market data update - Req {reqId}: {size_tick_names[tickType]} = {size}")
    
    def tickGeneric(self, reqId: TickerId, tickType: int, value: float):
        """Tick generic callback for market data."""
        if reqId not in self.market_data:
            self.market_data[reqId] = {
                'prices': {},
                'sizes': {},
                'generic': {},
                'strings': {},
                'last_update': None
            }
        
        self.market_data[reqId]['generic'][tickType] = value
        self.market_data[reqId]['last_update'] = datetime.now().isoformat()
        
        self.logger.debug(f"Generic tick update - Req {reqId}: Type {tickType} = {value}")
    
    def tickString(self, reqId: TickerId, tickType: int, value: str):
        """Tick string callback for market data."""
        if reqId not in self.market_data:
            self.market_data[reqId] = {
                'prices': {},
                'sizes': {},
                'generic': {},
                'strings': {},
                'last_update': None
            }
        
        self.market_data[reqId]['strings'][tickType] = value
        self.market_data[reqId]['last_update'] = datetime.now().isoformat()
        
        self.logger.debug(f"String tick update - Req {reqId}: Type {tickType} = {value}")
    
    def marketDataType(self, reqId: TickerId, marketDataType: int):
        """Market data type callback."""
        data_types = {
            1: 'Real-time', 2: 'Frozen', 3: 'Delayed', 4: 'Delayed-Frozen'
        }
        data_type_name = data_types.get(marketDataType, f'Unknown({marketDataType})')
        self.logger.info(f"Market data type for req {reqId}: {data_type_name}")
    
    def historicalData(self, reqId: int, bar):
        """Historical data callback."""
        if reqId not in self.historical_data:
            self.historical_data[reqId] = []
        
        # Convert bar to dictionary for easier access
        bar_data = {
            'date': bar.date,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume,
            'wap': bar.wap,
            'barCount': bar.barCount
        }
        
        self.historical_data[reqId].append(bar_data)
        self.logger.debug(f"Historical data received - Req {reqId}: {bar.date} OHLC: {bar.open}/{bar.high}/{bar.low}/{bar.close}")
    
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Historical data end callback."""
        data_count = len(self.historical_data.get(reqId, []))
        self.logger.info(f"Historical data complete for req {reqId}: {data_count} bars from {start} to {end}")
    
    def headTimestamp(self, reqId: int, headTimestamp: str):
        """Head timestamp callback for historical data."""
        self.logger.info(f"Head timestamp for req {reqId}: {headTimestamp}")
    
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
    
    def get_managed_accounts(self) -> List[str]:
        """Get list of managed accounts."""
        return getattr(self, 'managed_accounts', [])
    
    def get_selected_account(self) -> str:
        """Get the currently selected account ID."""
        return getattr(self, 'selected_account_id', 'DEFAULT')
    
    def create_stock_contract(self, symbol: str, exchange: str = "SMART") -> Contract:
        """Create a stock contract."""
        contract = Contract()
        contract.symbol = "ES"
        contract.secType = "FUT"
        contract.exchange = "CME"
        # For ETFs like SPY, add primary exchange for better resolution
        if symbol in ['SPY', 'QQQ', 'IWM', 'DIA']:  # Common ETFs
            contract.primaryExchange = "ARCA"  # NYSE Arca is primary for many ETFs
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
        
        # Use the actual managed account if available, otherwise use provided account
        if hasattr(self, 'selected_account_id') and self.selected_account_id and account == "DEFAULT":
            account = "Account:"+self.selected_account_id
            self.logger.info(f"Using managed account ID: {account}")
        
        tags = "TotalCashValue,NetLiquidation,BuyingPower,DayTradesRemaining"
        self.reqAccountSummary(1, account, tags)
    
    def request_positions(self) -> None:
        """Request all positions."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        
        self.reqPositions()
    
    def request_market_data(self, req_id: int, contract: Contract, snapshot: bool = False) -> None:
        """Request market data for a contract."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        
        # Clear any existing market data for this request
        self.market_data.pop(req_id, None)
        
        # Request market data with snapshot for immediate response
        # For paper trading, we often need to use snapshots
        
        self.reqMktData(req_id, contract, "", snapshot, False, [])
        self.logger.info(f"Requested market data for {contract.symbol} (req_id: {req_id}, snapshot: {snapshot})")

    def request_contract_details(self, req_id: int, contract: Contract) -> None:
        """
        Request full contract details for a given contract.

        This will populate:
        - self.contract_details[req_id]  (list[ContractDetails])
        - finish via contractDetailsEnd()
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")

        """# Clear any previous results for this request id
        self.contract_details.pop(req_id, None)

        # Initialize empty list (IB may return multiple matches)
        self.contract_details[req_id] = []"""

        # Send request
        self.reqContractDetails(req_id, contract)

        self.logger.info(
            f"Requested contract details for {contract.symbol} "
            f"(req_id: {req_id}, type={contract.secType}, exch={contract.exchange})"
        )
    
    
    def request_historical_data(self, req_id: int, contract: Contract, end_date_time: str = "",
                               duration_str: str = "1 W", bar_size_setting: str = "1 day",
                               what_to_show: str = "TRADES", use_rth: bool = True,
                               format_date: int = 1) -> None:
        """Request historical data for a contract."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        
        # Clear any existing historical data for this request
        self.historical_data.pop(req_id, None)
        
        # Request historical data
        self.reqHistoricalData(req_id, contract, end_date_time, duration_str,
                              bar_size_setting, what_to_show, use_rth, format_date, False, [])
        
        self.logger.info(f"Requested historical data for {contract.symbol} "
                        f"(req_id: {req_id}, duration: {duration_str}, bars: {bar_size_setting})")
    
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

            except Exception as e:
                self.logger.error(f"Error ib_connection: {e}")
    
    def _process_order_updates(self) -> None:
        """Process order status updates from TWS."""
        
        
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
            # Use the managed account if available, otherwise fall back to configured account_id
            account_to_use = self.ib_connection.get_selected_account() if hasattr(self.ib_connection, 'get_selected_account') else self.account_id
            if account_to_use == 'DEFAULT' and self.ib_connection.get_managed_accounts():
                account_to_use = self.ib_connection.get_managed_accounts()[0]
            
            # Request fresh account data
            self.ib_connection.request_account_summary(account_to_use)
            time.sleep(2)  # Wait for data (increased timeout)
            
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
    
    def get_market_data(self, symbol: str, use_snapshot: bool = False, timeout: int = 10) -> Dict[str, Any]:
        """Get real-time market data for a symbol."""
        if not self.ib_connection or not self.ib_connection.is_connected():
            return {}
        
        try:
            # Create contract with better definition for ETFs
            contract = self.ib_connection.create_stock_contract(symbol)
            
            # Use a more predictable req_id
            req_id = abs(hash(f"{symbol}_{datetime.now().timestamp()}")) % 10000
            
            self.logger.info(f"Requesting market data for {symbol} (req_id: {req_id})")
            
            # Request market data (try snapshot first for paper trading)
            #self.ib_connection.request_market_data(req_id, contract, snapshot=use_snapshot)
            self.ib_connection.request_contract_details(req_id=req_id,contract=contract)
            # Wait for data with progressive checks
            max_wait_time = timeout
            wait_interval = 0.5
            total_waited = 0
            
            while total_waited < max_wait_time:
                time.sleep(wait_interval)
                total_waited += wait_interval
                
                # Check if we have received any market data
                market_data = self.ib_connection.market_data.get(req_id, {})
                if market_data and ('prices' in market_data or 'sizes' in market_data):
                    self.logger.info(f"Received market data for {symbol} after {total_waited:.1f}s")
                    break
                    
                self.logger.debug(f"Waiting for market data... {total_waited:.1f}s elapsed")
            
            # Get final market data
            final_market_data = self.ib_connection.market_data.get(req_id, {})
            
            # Cancel the subscription
            try:
                self.ib_connection.cancelMktData(req_id)
            except Exception:
                pass
            
            # If still no data and using snapshot, try streaming
            if not final_market_data and use_snapshot:
                self.logger.info(f"No snapshot data for {symbol}, trying streaming...")
                return self.get_market_data(symbol, use_snapshot=False, timeout=5)
            
            # Format the response
            if final_market_data:
                # Extract meaningful price data
                prices = final_market_data.get('prices', {})
                sizes = final_market_data.get('sizes', {})
                
                formatted_data = {
                    'bid': prices.get(1, 'N/A'),
                    'ask': prices.get(2, 'N/A'),
                    'last': prices.get(4, 'N/A'),
                    'high': prices.get(6, 'N/A'),
                    'low': prices.get(7, 'N/A'),
                    'close': prices.get(9, 'N/A'),
                    'open': prices.get(14, 'N/A'),
                    'bid_size': sizes.get(0, 'N/A'),
                    'ask_size': sizes.get(3, 'N/A'),
                    'volume': sizes.get(8, 'N/A'),
                    'last_update': final_market_data.get('last_update')
                }
                
                self.logger.info(f"Market data for {symbol}: Last={formatted_data['last']}, Bid={formatted_data['bid']}, Ask={formatted_data['ask']}")
                
                return {
                    'symbol': symbol,
                    'data': formatted_data,
                    'raw_data': final_market_data,
                    'timestamp': datetime.now().isoformat(),
                    'req_id': req_id
                }
            else:
                self.logger.warning(f"No market data received for {symbol} after {timeout}s")
                return {
                    'symbol': symbol,
                    'data': {},
                    'error': 'No market data available',
                    'timestamp': datetime.now().isoformat(),
                    'req_id': req_id
                }
            
        except Exception as e:
            self.logger.error(f"Error getting market data for {symbol}: {e}")
            return {'symbol': symbol, 'error': str(e), 'timestamp': datetime.now().isoformat()}
    
    def get_market_data_snapshot(self, contract: Contract, generic_tick_list: str = "", 
                                snapshot: bool = True, timeout: int = None) -> Dict[str, Any]:
        """
        Get market data snapshot using Interactive Brokers API.
        
        Args:
            contract: Contract object for the security
            generic_tick_list: Comma-separated tick types for additional data  
            snapshot: Whether to get snapshot or streaming data
            timeout: Request timeout (uses default if None)
            
        Returns:
            Dictionary with tick data formatted as {TickType: value}
        """
        if not self.ib_connection or not self.ib_connection.is_connected():
            return {'error': 'Not connected to TWS'}
        
        if timeout is None:
            timeout = self.timeout
        
        try:
            # Generate unique request ID
            req_id = abs(hash(f"{contract.symbol}_{datetime.now().timestamp()}")) % 10000
            
            self.logger.info(f"Requesting market data snapshot for {contract.symbol}")
            
            # Clear any existing data
            self.ib_connection.market_data.pop(req_id, None)
            
            # Request market data with specified tick types
            self.ib_connection.reqMktData(req_id, contract, generic_tick_list, snapshot, False, [])
            
            # Wait for data with progressive checks
            wait_interval = 0.1
            total_waited = 0
            
            while total_waited < timeout:
                time.sleep(wait_interval)
                total_waited += wait_interval
                
                # Check if we have received market data
                market_data = self.ib_connection.market_data.get(req_id, {})
                if market_data and any([market_data.get('prices'), market_data.get('sizes'), 
                                      market_data.get('generic'), market_data.get('strings')]):
                    break
                    
            # Cancel subscription
            try:
                self.ib_connection.cancelMktData(req_id)
            except Exception:
                pass
            
            # Format response according to API specification
            final_data = self.ib_connection.market_data.get(req_id, {})
            
            if not final_data:
                return {'error': f'No market data received for {contract.symbol}'}
            
            # Map tick types to readable names and format response
            result = {}
            
            # Price ticks
            prices = final_data.get('prices', {})
            tick_price_map = {
                1: 'BID',
                2: 'ASK', 
                4: 'LAST',
                6: 'HIGH',
                7: 'LOW',
                9: 'CLOSE',
                14: 'OPEN'
            }
            
            for tick_type, name in tick_price_map.items():
                if tick_type in prices:
                    result[name] = prices[tick_type]
            
            # Size ticks  
            sizes = final_data.get('sizes', {})
            tick_size_map = {
                0: 'BID_SIZE',
                3: 'ASK_SIZE',
                5: 'LAST_SIZE', 
                8: 'VOLUME'
            }
            
            for tick_type, name in tick_size_map.items():
                if tick_type in sizes:
                    result[name] = Decimal(str(sizes[tick_type]))
            
            # String ticks
            strings = final_data.get('strings', {})
            tick_string_map = {
                45: 'LAST_TIMESTAMP'
            }
            
            for tick_type, name in tick_string_map.items():
                if tick_type in strings:
                    result[name] = strings[tick_type]
            
            # Generic ticks (if requested)
            generics = final_data.get('generic', {})
            for tick_type, value in generics.items():
                result[f'GENERIC_{tick_type}'] = value
            
            self.logger.info(f"Market data snapshot complete for {contract.symbol}: {len(result)} fields")
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting market data snapshot for {contract.symbol}: {e}")
            return {'error': str(e)}
    
    def get_historical_data(self, contract: Contract, end_date_time: str = "",
                           duration_str: str = "1 W", bar_size_setting: str = "1 day",
                           what_to_show: str = "TRADES", use_rth: bool = True,
                           format_date: int = 1, timeout: int = 30) -> List[Dict[str, Any]]:
        """
        Get historical data using Interactive Brokers API.
        
        Args:
            contract: Contract object for the security
            end_date_time: End date/time in format "YYYYMMDD HH:mm:ss TMZ" or empty for now
            duration_str: Time span covered (e.g., "1 W", "1 M", "1 Y")
            bar_size_setting: Bar size (e.g., "1 day", "1 hour", "5 mins")
            what_to_show: Data type ("TRADES", "MIDPOINT", "BID", "ASK", etc.)
            use_rth: Whether to use regular trading hours only
            format_date: 1 for datetime string, 2 for Unix timestamp
            timeout: Request timeout in seconds
            
        Returns:
            List of bar objects with OHLCV data
        """
        if not self.ib_connection or not self.ib_connection.is_connected():
            return []
        
        try:
            # Generate unique request ID
            req_id = abs(hash(f"hist_{contract.symbol}_{datetime.now().timestamp()}")) % 10000
            
            self.logger.info(f"Requesting historical data for {contract.symbol} "
                           f"({duration_str}, {bar_size_setting})")
            
            # Request historical data
            self.ib_connection.request_historical_data(
                req_id=req_id,
                contract=contract,
                end_date_time=end_date_time,
                duration_str=duration_str,
                bar_size_setting=bar_size_setting,
                what_to_show=what_to_show,
                use_rth=use_rth,
                format_date=format_date
            )
            
            # Wait for data completion
            wait_interval = 0.5
            total_waited = 0
            data_complete = False
            
            while total_waited < timeout:
                time.sleep(wait_interval)
                total_waited += wait_interval
                
                # Check if historical data is complete
                # Data is complete when we have bars and haven't received new ones recently
                hist_data = self.ib_connection.historical_data.get(req_id, [])
                
                if hist_data:
                    # If we have data, wait a bit more to ensure completion
                    if total_waited > 2:  # Give at least 2 seconds for completion
                        data_complete = True
                        break
                        
                self.logger.debug(f"Waiting for historical data... {total_waited:.1f}s")
            
            # Get final historical data
            historical_bars = self.ib_connection.historical_data.get(req_id, [])
            
            if not historical_bars:
                self.logger.warning(f"No historical data received for {contract.symbol}")
                return []
            
            # Format bars according to IB Bar format
            formatted_bars = []
            for bar in historical_bars:
                formatted_bar = {
                    'date': bar['date'],
                    'open': bar['open'],
                    'high': bar['high'], 
                    'low': bar['low'],
                    'close': bar['close'],
                    'volume': bar['volume'],
                    'wap': bar['wap'],  # Weighted average price
                    'barCount': bar['barCount']
                }
                formatted_bars.append(formatted_bar)
            
            self.logger.info(f"Historical data complete for {contract.symbol}: {len(formatted_bars)} bars")
            
            # Clean up stored data
            self.ib_connection.historical_data.pop(req_id, None)
            
            return formatted_bars
            
        except Exception as e:
            self.logger.error(f"Error getting historical data for {contract.symbol}: {e}")
            return []