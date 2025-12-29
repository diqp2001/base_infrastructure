from ibapi.client import EClient
from ibapi.common import OrderId, TickerId
from ibapi.contract import Contract
from ibapi.order import Order as IBOrder
from ibapi.wrapper import EWrapper


import logging
import threading
from datetime import datetime
from typing import List


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

    def create_contract(self, symbol: str, secType: str = "FUT", exchange: str = "CME") -> Contract:
        """Create a stock contract."""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = secType
        contract.exchange = exchange
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