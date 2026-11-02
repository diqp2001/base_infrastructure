from ibapi.client import EClient
from ibapi.common import OrderId, TickerId
from ibapi.contract import Contract
from ibapi.order import Order as IBOrder
from ibapi.wrapper import EWrapper


import logging
import threading
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Tuple

from src.application.services.misbuffet.brokers.ibkr.ibkr_settings import verify_connected_accounts


CONNECTIVITY_LOST, CONNECTIVITY_RESTORED_DATA_LOST, CONNECTIVITY_RESTORED = 1100, 1101, 1102
CONNECTIVITY_CODES = (CONNECTIVITY_LOST, CONNECTIVITY_RESTORED_DATA_LOST, CONNECTIVITY_RESTORED)
ACCOUNT_SUMMARY_FIRST_REQ_ID = 90_002         # reqAccountSummary ids: 90_002 .. 90_901, one per snapshot
ACCOUNT_SUMMARY_REQ_IDS = 900
ACCOUNT_UPDATES_REQ_ID = 89_001               # request_account_summary (broker's account refresh): one subscription
POSITIONS_FIRST_REQ_ID = 91_002               # reqPositionsMulti ids: 91_002 .. 91_901, one per positions snapshot
POSITIONS_REQ_IDS = 900


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
        self.commissions = {}                   # execId -> {commission, currency}
        self.last_send_attempt_order_id = None  # order id of the last placeOrder attempt (P.03)
        self.placed_order_ids = set()           # order ids this client sent: their errors are order events (P.06)
        # P.03: callables(event: dict) told of every orderStatus / execDetails / commissionReport (on the API
        # thread: a listener must only queue the event, never touch the database)
        self.order_listeners: List = []

        # Reconciliation snapshots (request_positions_snapshot / request_open_orders_snapshot):
        # contract-level rows (conId / localSymbol), filled between the request and its *End callback
        self.positions_snapshot: List[dict] = []
        self.open_orders_snapshot: List[dict] = []
        self.executions_snapshot: List[dict] = []    # request_executions_snapshot (P.04)
        self.account_values_snapshot: Dict[str, Dict[str, tuple]] = {}   # account -> tag -> (value, currency) (P.05)
        self._account_summary_collecting = False
        self._account_summary_end_event = threading.Event()
        self._account_summary_req_id: Optional[int] = None          # the snapshot request being collected
        self._account_summary_next_id = ACCOUNT_SUMMARY_FIRST_REQ_ID
        self._executions_req_id = None
        self._executions_end_event = threading.Event()
        self._snapshot_lock = threading.Lock()
        self._positions_collecting = False
        self._positions_req_id: Optional[int] = None                # the positions snapshot being collected
        self._positions_next_id = POSITIONS_FIRST_REQ_ID
        self._account_updates_active = False
        self._open_orders_collecting = False
        self._positions_end_event = threading.Event()
        self._open_orders_end_event = threading.Event()

        # Market data
        self.market_data = {}
        
        # Market depth data (Level 2)
        self.market_depth = {}
        
        # Contract details storage
        self.contract_details = {}
        
        # Market scanner results
        self.scanner_results = {}
        
        # Market data subscriptions tracking
        self.market_data_subscriptions = set()
        # P.02 streaming state: reqId -> IBKR marketDataType (1 live, 2 frozen, 3 delayed, 4 delayed-frozen), the error
        # IBKR returned for that market-data request (entitlement, unknown contract ...), tick-by-tick events
        self.market_data_type: Dict[int, int] = {}
        self.market_data_errors: Dict[int, Tuple[int, str]] = {}
        self.tick_by_tick: Dict[int, dict] = {}
        # called (no argument) when the connection closes: streaming subscribers resubscribe after a reconnect
        self.connection_listeners: List[Callable[[], None]] = []
        # called with the code when TWS loses / regains its link to IBKR while the API socket stays open:
        # 1100 lost, 1101 restored with market data lost (resubscribe), 1102 restored with data kept (P.04.07)
        self.connectivity_listeners: List[Callable[[int], None]] = []
        
        # News data storage
        self.news_data = {}

        # Historical data
        self.historical_data = {}
        # reqId -> Event set by historicalDataEnd or by an error for that request
        self.historical_data_done = {}
        self.historical_data_errors = {}

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
        for listener in list(getattr(self, "connection_listeners", [])):
            try:
                listener()
            except Exception as e:                        # a listener never breaks the API thread
                self.logger.warning(f"connection listener failed: {e}")

    def nextValidId(self, orderId: int):
        """Next valid order ID callback."""
        self.logger.info(f"Next valid order ID: {orderId}")
        # never move backwards: an id this session already used must not be reused after a reconnect
        self.next_order_id = max(orderId, getattr(self, "_highest_used_order_id", 0) + 1)
        self.connected_flag = True
        self.authenticated_flag = True
        self.connection_event.set()

    def error(self, reqId: TickerId, errorCode: int, errorString: str, advancedOrderRejectJson=""):
        """Error callback."""
        done = getattr(self, "historical_data_done", {}).get(reqId)
        from .history_result import is_warning
        if done is not None and not is_warning(errorCode):     # notices (21xx, 10167) do not end a request
            # e.g. 162 "no historical data", 200 "no security definition": the request is over
            self.historical_data_errors[reqId] = (errorCode, errorString)
            done.set()
        # P.02: an error for a market-data request belongs to that subscription (entitlement 354 / 10089 / 10090 /
        # 10091 / 10168 / 10197, no security definition 200 ...); 10167 only says delayed data is displayed
        if reqId in getattr(self, "market_data_subscriptions", ()) or reqId in getattr(self, "market_data", {}) \
                or reqId in getattr(self, "tick_by_tick", {}):
            if errorCode not in (2104, 2106, 2158, 10167, 2119):
                self.market_data_errors[reqId] = (errorCode, errorString)
        # P.06: an error for an order this client sent is an order event (e.g. 321 API read-only, 201 rejected):
        # the order ledger decides whether it rejects the order
        if reqId in getattr(self, "placed_order_ids", ()):
            self._tell_order_listeners({"kind": "order_error", "order_id": reqId, "code": int(errorCode),
                                        "message": str(errorString), "client_id": self.client_id})
        if errorCode in CONNECTIVITY_CODES:
            self.logger.warning(f"TWS connectivity {errorCode}: {errorString}")
            for listener in list(getattr(self, "connectivity_listeners", [])):
                try:
                    listener(int(errorCode))
                except Exception as e:                    # a listener never breaks the API thread
                    self.logger.warning(f"connectivity listener failed: {e}")
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
        self._tell_order_listeners({"kind": "status", "order_id": orderId, "status": status, "filled": filled,
                                    "remaining": remaining, "avg_fill_price": avgFillPrice, "perm_id": permId,
                                    "client_id": clientId, "why_held": whyHeld})

    def _tell_order_listeners(self, event: dict) -> None:
        event["received_at"] = datetime.now(timezone.utc)
        for listener in list(getattr(self, "order_listeners", [])):
            try:
                listener(event)
            except Exception as e:
                self.logger.error(f"order listener failed on {event.get('kind')}: {e}")

    def commissionReport(self, commissionReport):
        """Commission of one execution (IBKR sends it after execDetails, keyed by execId)."""
        self.commissions[commissionReport.execId] = {"commission": commissionReport.commission,
                                                     "currency": commissionReport.currency}
        self._tell_order_listeners({"kind": "commission", "exec_id": commissionReport.execId,
                                    "commission": commissionReport.commission,
                                    "currency": commissionReport.currency})

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
        self._tell_order_listeners({
            "kind": "execution", "req_id": reqId, "exec_id": execution.execId, "order_id": order_id,
            "perm_id": getattr(execution, "permId", None), "client_id": getattr(execution, "clientId", None),
            "account": getattr(execution, "acctNumber", None), "time": execution.time,
            "shares": float(execution.shares), "price": float(execution.price), "side": execution.side,
            "symbol": getattr(contract, "localSymbol", "") or getattr(contract, "symbol", ""),
            "sec_type": getattr(contract, "secType", ""), "con_id": getattr(contract, "conId", None),
            "order_ref": getattr(execution, "orderRef", "") or ""})
        with self._snapshot_lock:
            if reqId is not None and reqId == self._executions_req_id:
                self.executions_snapshot.append({"execId": execution.execId, "orderId": order_id,
                                                 "permId": getattr(execution, "permId", None),
                                                 "orderRef": getattr(execution, "orderRef", "") or "",
                                                 "shares": float(execution.shares), "side": execution.side,
                                                 "symbol": getattr(contract, "symbol", ""),
                                                 "localSymbol": getattr(contract, "localSymbol", ""),
                                                 "secType": getattr(contract, "secType", "")})
        self.logger.info(f"Execution: Order {order_id}, {execution.shares} @ {execution.price}")

    def execDetailsEnd(self, reqId: int):
        """End of a reqExecutions answer."""
        if reqId == self._executions_req_id:
            self._executions_end_event.set()

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        """Account summary callback."""
        self.account_summary[tag] = {
            'value': value,
            'currency': currency,
            'account': account
        }
        with self._snapshot_lock:
            if self._account_summary_collecting and reqId == self._account_summary_req_id:
                self.account_values_snapshot.setdefault(account, {})[tag] = (value, currency)

    def accountSummaryEnd(self, reqId: int):
        """End of a reqAccountSummary answer. The end of an earlier, cancelled request (same connection, snapshots
        taken back to back by the pre-trade gate) must not complete the current one with no values (P.06.11)."""
        with self._snapshot_lock:
            if reqId != self._account_summary_req_id:
                return
            self._account_summary_collecting = False
        self._account_summary_end_event.set()

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

    def positionEnd(self):
        """End of the reqPositions list (request_positions: the broker's own position refresh, not a snapshot)."""

    def positionMulti(self, reqId: int, account: str, modelCode: str, contract: Contract, pos: float,
                      avgCost: float):
        """A row of a positions snapshot (reqPositionsMulti). Rows of any other request are ignored."""
        with self._snapshot_lock:
            if not self._positions_collecting or reqId != self._positions_req_id:
                return
            self.positions_snapshot.append({
                'account': account, 'symbol': contract.symbol, 'secType': contract.secType,
                'exchange': contract.exchange, 'position': pos, 'avgCost': avgCost,
                'conId': getattr(contract, 'conId', None),
                'localSymbol': getattr(contract, 'localSymbol', ''),
                'currency': getattr(contract, 'currency', ''),
            })

    def positionMultiEnd(self, reqId: int):
        """End of a positions snapshot. The end of an earlier, timed-out request must not complete the current one
        (same race as the account snapshots, P.06.11)."""
        with self._snapshot_lock:
            if reqId != self._positions_req_id:
                return
            self._positions_collecting = False
        self._positions_end_event.set()

    def openOrder(self, orderId: OrderId, contract: Contract, order: IBOrder, orderState):
        """Open order callback (reqAllOpenOrders / reqOpenOrders / order updates)."""
        row = {
            'orderId': orderId,
            'permId': getattr(order, 'permId', None),
            'clientId': getattr(order, 'clientId', None),
            'account': getattr(order, 'account', ''),
            'symbol': contract.symbol,
            'localSymbol': getattr(contract, 'localSymbol', ''),
            'secType': contract.secType,
            'conId': getattr(contract, 'conId', None),
            'action': getattr(order, 'action', ''),
            'totalQuantity': float(getattr(order, 'totalQuantity', 0) or 0),
            'orderType': getattr(order, 'orderType', ''),
            'orderRef': getattr(order, 'orderRef', '') or '',
            'status': getattr(orderState, 'status', ''),
            'remaining': None,
        }
        status = self.order_status.get(orderId)
        if status:
            row['remaining'] = status.get('remaining')
        with self._snapshot_lock:
            if self._open_orders_collecting:
                self.open_orders_snapshot.append(row)

    def openOrderEnd(self):
        """End of the open orders list."""
        with self._snapshot_lock:
            self._open_orders_collecting = False
        self._open_orders_end_event.set()

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
        self.market_data[reqId].setdefault('received', {})[tickType] = datetime.now(timezone.utc)

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
        self.market_data[reqId].setdefault('received_sizes', {})[tickType] = datetime.now(timezone.utc)

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
        if tickType in (45, 88):                          # LAST_TIMESTAMP / DELAYED_LAST_TIMESTAMP: epoch seconds
            try:
                self.market_data[reqId]['last_trade_time'] = datetime.fromtimestamp(int(value), tz=timezone.utc)
            except (TypeError, ValueError, OSError):
                pass

        self.logger.debug(f"String tick update - Req {reqId}: Type {tickType} = {value}")

    def marketDataType(self, reqId: TickerId, marketDataType: int):
        """Market data type callback."""
        data_types = {
            1: 'Real-time', 2: 'Frozen', 3: 'Delayed', 4: 'Delayed-Frozen'
        }
        data_type_name = data_types.get(marketDataType, f'Unknown({marketDataType})')
        self.logger.info(f"Market data type for req {reqId}: {data_type_name}")
        self.market_data_type[reqId] = int(marketDataType)

    def tickByTickBidAsk(self, reqId: int, time: int, bidPrice: float, askPrice: float, bidSize, askSize,
                         tickAttribBidAsk):
        """Tick-by-tick quote: IBKR stamps the event time (epoch seconds)."""
        now = datetime.now(timezone.utc)
        entry = self.tick_by_tick.setdefault(reqId, {})
        entry.update(bid=bidPrice, ask=askPrice, bid_size=float(bidSize), ask_size=float(askSize),
                     quote_event_time=datetime.fromtimestamp(int(time), tz=timezone.utc), quote_received=now)

    def tickByTickAllLast(self, reqId: int, tickType: int, time: int, price: float, size, tickAttribLast,
                          exchange: str, specialConditions: str):
        """Tick-by-tick trade (tickType 1 Last, 2 AllLast)."""
        now = datetime.now(timezone.utc)
        entry = self.tick_by_tick.setdefault(reqId, {})
        entry.update(last=price, last_size=float(size), trade_event_time=datetime.fromtimestamp(int(time), tz=timezone.utc),
                     trade_received=now, exchange=exchange)

    def historicalData(self, reqId: int, bar):
        """Historical data callback. Bars of a request that is no longer active (finished, timed out) are ignored."""
        if reqId not in getattr(self, "historical_data_done", {}):
            return
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
            'barCount': bar.barCount
        }

        self.historical_data[reqId].append(bar_data)
        self.logger.debug(f"Historical data received - Req {reqId}: {bar.date} OHLC: {bar.open}/{bar.high}/{bar.low}/{bar.close}")

    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Historical data end callback."""
        done = self.historical_data_done.get(reqId)
        if done is not None:
            done.set()
        data_count = len(self.historical_data.get(reqId, []))
        self.logger.info(f"Historical data complete for req {reqId}: {data_count} bars from {start} to {end}")

    def headTimestamp(self, reqId: int, headTimestamp: str):
        """Head timestamp callback for historical data."""
        self.logger.info(f"Head timestamp for req {reqId}: {headTimestamp}")
    
    def updateMktDepth(self, reqId: TickerId, position: int, operation: int, side: int,
                       price: float, size: int):
        """Market depth (Level 2) callback."""
        if reqId not in self.market_depth:
            self.market_depth[reqId] = {
                'bids': {},  # position -> {price, size}
                'asks': {},
                'last_update': None
            }
        
        side_name = 'asks' if side == 0 else 'bids'  # 0=ask, 1=bid
        
        if operation == 0:  # Insert
            self.market_depth[reqId][side_name][position] = {'price': price, 'size': size}
        elif operation == 1:  # Update
            if position in self.market_depth[reqId][side_name]:
                self.market_depth[reqId][side_name][position]['size'] = size
        elif operation == 2:  # Delete
            self.market_depth[reqId][side_name].pop(position, None)
        
        self.market_depth[reqId]['last_update'] = datetime.now().isoformat()
        self.logger.debug(f"Market depth update - Req {reqId}: {side_name} pos {position}, price {price}, size {size}")
    
    def updateMktDepthL2(self, reqId: TickerId, position: int, marketMaker: str, operation: int,
                         side: int, price: float, size: int, isSmartDepth: bool):
        """Market depth L2 callback with market maker information."""
        if reqId not in self.market_depth:
            self.market_depth[reqId] = {
                'bids': {},
                'asks': {},
                'last_update': None
            }
        
        side_name = 'asks' if side == 0 else 'bids'
        
        if operation == 0:  # Insert
            self.market_depth[reqId][side_name][position] = {
                'price': price, 'size': size, 'market_maker': marketMaker
            }
        elif operation == 1:  # Update
            if position in self.market_depth[reqId][side_name]:
                self.market_depth[reqId][side_name][position].update({
                    'size': size, 'market_maker': marketMaker
                })
        elif operation == 2:  # Delete
            self.market_depth[reqId][side_name].pop(position, None)
        
        self.market_depth[reqId]['last_update'] = datetime.now().isoformat()
        self.logger.debug(f"L2 depth update - Req {reqId}: {side_name} pos {position}, MM {marketMaker}")
    
    def contractDetails(self, reqId: int, contractDetails):
        """Contract details callback."""
        if reqId not in self.contract_details:
            self.contract_details[reqId] = []
        
        # Store contract details with key information
        contract_info = {
            'contract_id': contractDetails.contract.conId,
            'symbol': contractDetails.contract.symbol,
            'sec_type': contractDetails.contract.secType,
            'exchange': contractDetails.contract.exchange,
            'primary_exchange': contractDetails.contract.primaryExchange,
            'currency': contractDetails.contract.currency,
            'local_symbol': contractDetails.contract.localSymbol,
            'trading_class': contractDetails.contract.tradingClass,
            'market_name': contractDetails.marketName,
            'min_tick': contractDetails.minTick,
            'price_magnifier': contractDetails.priceMagnifier,
            'order_types': contractDetails.orderTypes,
            'valid_exchanges': contractDetails.validExchanges,
            'time_zone_id': contractDetails.timeZoneId,
            'trading_hours': contractDetails.tradingHours,
            'liquid_hours': contractDetails.liquidHours
        }
        
        self.contract_details[reqId].append(contract_info)
        self.logger.info(f"Contract details received - Req {reqId}: {contractDetails.contract.symbol} ({contractDetails.contract.conId})")
    
    def contractDetailsEnd(self, reqId: int):
        """Contract details end callback."""
        details_count = len(self.contract_details.get(reqId, []))
        self.logger.info(f"Contract details complete for req {reqId}: {details_count} contracts")
    
    def scannerData(self, reqId: int, rank: int, contractDetails, distance: str, 
                    benchmark: str, projection: str, legsStr: str):
        """Scanner data callback."""
        if reqId not in self.scanner_results:
            self.scanner_results[reqId] = []
        
        scanner_result = {
            'rank': rank,
            'contract': {
                'symbol': contractDetails.contract.symbol,
                'sec_type': contractDetails.contract.secType,
                'exchange': contractDetails.contract.exchange,
                'currency': contractDetails.contract.currency,
                'local_symbol': contractDetails.contract.localSymbol
            },
            'distance': distance,
            'benchmark': benchmark,
            'projection': projection,
            'legs': legsStr
        }
        
        self.scanner_results[reqId].append(scanner_result)
        self.logger.debug(f"Scanner result - Req {reqId}: Rank {rank}, {contractDetails.contract.symbol}")
    
    def scannerDataEnd(self, reqId: int):
        """Scanner data end callback."""
        results_count = len(self.scanner_results.get(reqId, []))
        self.logger.info(f"Scanner data complete for req {reqId}: {results_count} results")
    
    def tickNews(self, tickerId: int, timeStamp: int, providerCode: str, articleId: str,
                 headline: str, extraData: str):
        """Tick news callback."""
        if tickerId not in self.news_data:
            self.news_data[tickerId] = []
        
        news_item = {
            'timestamp': timeStamp,
            'provider_code': providerCode,
            'article_id': articleId,
            'headline': headline,
            'extra_data': extraData,
            'received_at': datetime.now().isoformat()
        }
        
        self.news_data[tickerId].append(news_item)
        self.logger.debug(f"News received - Ticker {tickerId}: {headline[:50]}...")
    
    def tickReqParams(self, tickerId: int, minTick: float, bboExchange: str, snapshotPermissions: int):
        """Tick request parameters callback."""
        self.logger.debug(f"Tick params - Ticker {tickerId}: MinTick {minTick}, BBO Exchange {bboExchange}")
    
    def mktDepthExchanges(self, depthMktDataDescriptions):
        """Market depth exchanges callback."""
        self.logger.info(f"Market depth exchanges: {len(depthMktDataDescriptions)} available")
        for desc in depthMktDataDescriptions:
            self.logger.debug(f"Depth exchange: {desc.exchange} - {desc.secType} (Max depth: {desc.maxDepth})")

    # Custom methods

    def connect_to_tws(self) -> bool:
        """Connect to TWS/Gateway."""
        try:
            self.logger.info(f"Connecting to TWS at {self.host}:{self.port} (client {self.client_id})")
            self.connect(self.host, self.port, self.client_id)
            self._release_at_exit()

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

    def _release_at_exit(self) -> None:
        """BI-020: a finished run always releases its client id. ibapi's EReader is a non-daemon thread that
        only ends when the socket closes, and the interpreter joins non-daemon threads BEFORE atexit handlers run:
        a run that never disconnected hung at exit and kept the client id, so the next run with that id failed
        ("TWS is not connected"). threading._register_atexit hooks run before that join (Python >= 3.9, as
        concurrent.futures uses it); plain atexit is the fallback."""
        if getattr(self, "_exit_hook_registered", False):
            return
        self._exit_hook_registered = True

        def release():
            if self.isConnected():
                self.logger.info(f"Process exit: disconnecting client {self.client_id} from TWS")
                self.disconnect_from_tws()

        register = getattr(threading, "_register_atexit", None)
        try:
            if register is None:
                raise RuntimeError("no threading._register_atexit")
            register(release)
        except RuntimeError:
            import atexit
            atexit.register(release)

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
        contract.tradingClass = symbol

        return contract

    def place_order(self, contract: Contract, order: IBOrder) -> int:
        """Place an order with TWS."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        # BI-005: the account TWS is logged into must match IBKR_ACCOUNT_MODE (paper DU… vs live)
        order_account = getattr(order, "account", "")
        verify_connected_accounts(self.get_managed_accounts(), order_account if isinstance(order_account, str) else "")

        order_id = self.next_order_id
        self.next_order_id += 1
        self._highest_used_order_id = max(order_id, getattr(self, "_highest_used_order_id", 0))

        # P.03: from here the order may have left (placeOrder writes to the socket); an exception after this line
        # leaves its outcome UNKNOWN — the caller must never resend it, the broker's state decides
        self.last_send_attempt_order_id = order_id
        self.placed_order_ids.add(order_id)
        self.placeOrder(order_id, contract, order)
        self.logger.info(f"Placed order {order_id}: {contract.symbol} {order.action} {order.totalQuantity}")

        return order_id

    def cancel_order(self, order_id: int) -> None:
        """Cancel an order."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")

        # ibapi 9.81 takes cancelOrder(orderId); 10.x adds manualCancelOrderTime (P.06: the 2-argument call raised
        # TypeError with the installed 9.81, so no API cancel ever reached IBKR)
        try:
            self.cancelOrder(order_id)
        except TypeError:
            self.cancelOrder(order_id, "")
        self.logger.info(f"Cancel requested for order {order_id}")

    def request_account_summary(self, account: str = "All") -> None:
        """Request account summary."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")

        # Fix Issue #1: IBKR does not accept account IDs in reqAccountSummary groupName
        # Always use "All" as groupName instead of account-specific names
        group_name = "All"
        
        tags = "TotalCashValue,NetLiquidation,BuyingPower,DayTradesRemaining"
        # one subscription with its own id: re-requesting an active id (it was 1, never cancelled) is refused by TWS
        # and shared ids let its answers mix with other requests
        with self._snapshot_lock:
            if self._account_updates_active:
                self.cancelAccountSummary(ACCOUNT_UPDATES_REQ_ID)
            self._account_updates_active = True
        self.reqAccountSummary(ACCOUNT_UPDATES_REQ_ID, group_name, tags)
        self.logger.info(f"Requesting account summary with groupName: {group_name}")

    def request_account_values_snapshot(self, timeout: float = 10.0, req_id: Optional[int] = None,
                                        tags: str = "NetLiquidation,TotalCashValue,BuyingPower,AvailableFunds,"
                                                    "GrossPositionValue") -> bool:
        """Account values of every managed account into ``account_values_snapshot`` (P.05 risk). Read-only.
        Each snapshot has its own request id; answers to any other id are ignored."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        with self._snapshot_lock:
            if req_id is None:
                req_id = self._account_summary_next_id
                self._account_summary_next_id = ACCOUNT_SUMMARY_FIRST_REQ_ID +                     (req_id - ACCOUNT_SUMMARY_FIRST_REQ_ID + 1) % ACCOUNT_SUMMARY_REQ_IDS
            self._account_summary_req_id = req_id
            self.account_values_snapshot = {}
            self._account_summary_collecting = True
            self._account_summary_end_event.clear()
        self.reqAccountSummary(req_id, "All", tags)
        complete = self._account_summary_end_event.wait(timeout)
        try:
            self.cancelAccountSummary(req_id)
        except Exception as e:
            self.logger.warning(f"cancelAccountSummary failed: {e}")
        with self._snapshot_lock:
            self._account_summary_collecting = False
            self._account_summary_req_id = None
        if not complete:
            self.logger.error(f"accountSummaryEnd not received within {timeout}s")
        return complete

    def request_positions(self) -> None:
        """Request all positions."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")

        self.reqPositions()

    def request_positions_snapshot(self, timeout: float = 10.0, account: str = "") -> bool:
        """Fresh list of the positions of ``account`` ("" = every managed account) into ``positions_snapshot``.
        True when the end arrived in time. Each snapshot is its own reqPositionsMulti with its own request id: rows
        of the broker's position refresh (reqPositions) or of an earlier snapshot never land in this one."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        with self._snapshot_lock:
            req_id = self._positions_next_id
            self._positions_next_id = POSITIONS_FIRST_REQ_ID + (req_id - POSITIONS_FIRST_REQ_ID + 1) % POSITIONS_REQ_IDS
            self._positions_req_id = req_id
            self.positions_snapshot = []
            self._positions_collecting = True
            self._positions_end_event.clear()
        self.reqPositionsMulti(req_id, account or "", "")
        complete = self._positions_end_event.wait(timeout)
        try:
            self.cancelPositionsMulti(req_id)
        except Exception as e:
            self.logger.warning(f"cancelPositionsMulti failed: {e}")
        with self._snapshot_lock:
            self._positions_collecting = False
            self._positions_req_id = None
        if not complete:
            self.logger.error(f"positions end not received within {timeout}s")
        return complete

    def request_open_orders_snapshot(self, timeout: float = 10.0) -> bool:
        """Fresh list of all working orders of the account (every client id, incl. TWS) into
        ``open_orders_snapshot``. Read-only: reqAllOpenOrders never binds or modifies orders."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        with self._snapshot_lock:
            self.open_orders_snapshot = []
            self._open_orders_collecting = True
        self._open_orders_end_event.clear()
        self.reqAllOpenOrders()
        complete = self._open_orders_end_event.wait(timeout)
        with self._snapshot_lock:
            self._open_orders_collecting = False
        if not complete:
            self.logger.error(f"openOrderEnd not received within {timeout}s")
        return complete

    def request_executions_snapshot(self, timeout: float = 10.0, req_id: int = 90_001) -> bool:
        """Today's executions of the account (IBKR returns the current day only) into ``executions_snapshot``; every
        execution and its commission report also reach the order listeners (P.04 recovery). Read-only."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        from ibapi.execution import ExecutionFilter
        with self._snapshot_lock:
            self.executions_snapshot = []
            self._executions_req_id = req_id
        self._executions_end_event.clear()
        self.reqExecutions(req_id, ExecutionFilter())
        complete = self._executions_end_event.wait(timeout)
        if not complete:
            self.logger.error(f"execDetailsEnd not received within {timeout}s")
        return complete

    def request_market_data(self, req_id: int, contract: Contract, snapshot: bool = False, generic_tick_list: str = "") -> None:
        """Request market data for a contract."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")

        # Clear any existing market data for this request
        self.market_data.pop(req_id, None)

        # Fix Issue #2: snapshot=True cannot be used with genericTickList
        # IBKR rule: Generic ticks require streaming mode
        if snapshot and generic_tick_list:
            self.logger.warning(f"Snapshot mode cannot use generic tick list '{generic_tick_list}'. Using snapshot with no ticks.")
            generic_tick_list = ""

        self.reqMktData(req_id, contract, generic_tick_list, snapshot, False, [])
        
        # Track subscription if not snapshot
        if not snapshot:
            self.market_data_subscriptions.add(req_id)
            
        self.logger.info(f"Requested market data for {contract.symbol} (req_id: {req_id}, snapshot: {snapshot}, ticks: '{generic_tick_list}')")

    def request_contract_details(self, req_id: int, contract: Contract) -> None:
        """
        Request full contract details for a given contract.

        This will populate:
        - self.contract_details[req_id]  (list[ContractDetails])
        - finish via contractDetailsEnd()
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")

        # Clear any previous results for this request id
        self.contract_details.pop(req_id, None)

        # Send request
        self.reqContractDetails(req_id, contract)

        self.logger.info(
            f"Requested contract details for {contract.symbol} "
            f"(req_id: {req_id}, type={contract.secType}, exch={contract.exchange})"
        )
    
    def request_market_depth(self, req_id: int, contract: Contract, num_rows: int = 5, 
                            is_smart_depth: bool = False) -> None:
        """
        Request market depth (Level 2) data for a contract.
        
        Args:
            req_id: Request identifier
            contract: Contract to get depth for
            num_rows: Number of depth rows to request (max 20)
            is_smart_depth: Whether to use smart depth routing
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        
        # Clear any existing depth data for this request
        self.market_depth.pop(req_id, None)
        
        # Request market depth
        self.reqMktDepth(req_id, contract, num_rows, is_smart_depth, [])
        self.logger.info(f"Requested market depth for {contract.symbol} (req_id: {req_id}, rows: {num_rows})")
    
    def cancel_market_depth(self, req_id: int, is_smart_depth: bool = False) -> None:
        """
        Cancel market depth subscription.
        
        Args:
            req_id: Request identifier to cancel
            is_smart_depth: Whether this was smart depth
        """
        if not self.is_connected():
            return
        
        self.cancelMktDepth(req_id, is_smart_depth)
        self.market_depth.pop(req_id, None)
        self.logger.info(f"Cancelled market depth subscription {req_id}")
    
    def request_scanner_subscription(self, req_id: int, scanner_subscription, scanner_subscription_options=None,
                                   scanner_subscription_filter_options=None) -> None:
        """
        Request market scanner subscription.
        
        Args:
            req_id: Request identifier
            scanner_subscription: Scanner subscription parameters
            scanner_subscription_options: Optional scanner options
            scanner_subscription_filter_options: Optional filter options
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        
        # Clear any existing scanner results
        self.scanner_results.pop(req_id, None)
        
        # Request scanner data
        opts = scanner_subscription_options or []
        filter_opts = scanner_subscription_filter_options or []
        
        self.reqScannerSubscription(req_id, scanner_subscription, opts, filter_opts)
        self.logger.info(f"Requested scanner subscription (req_id: {req_id})")
    
    def cancel_scanner_subscription(self, req_id: int) -> None:
        """
        Cancel market scanner subscription.
        
        Args:
            req_id: Request identifier to cancel
        """
        if not self.is_connected():
            return
        
        self.cancelScannerSubscription(req_id)
        self.scanner_results.pop(req_id, None)
        self.logger.info(f"Cancelled scanner subscription {req_id}")
    
    def request_scanner_parameters(self) -> None:
        """
        Request available scanner parameters.
        This will trigger scannerParameters() callback with XML data.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        
        self.reqScannerParameters()
        self.logger.info("Requested scanner parameters")
    
    def request_market_data_type(self, market_data_type: int) -> None:
        """
        Request market data type.
        
        Args:
            market_data_type: 1=Live, 2=Frozen, 3=Delayed, 4=Delayed-Frozen
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        
        self.reqMarketDataType(market_data_type)
        data_types = {1: 'Live', 2: 'Frozen', 3: 'Delayed', 4: 'Delayed-Frozen'}
        self.logger.info(f"Requested market data type: {data_types.get(market_data_type, market_data_type)}")
    
    def request_tick_by_tick(self, req_id: int, contract: Contract, tick_type: str = "BidAsk") -> None:
        """Tick-by-tick stream ('BidAsk', 'Last', 'AllLast', 'MidPoint'): events stamped by IBKR."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")
        self.tick_by_tick.pop(req_id, None)
        self.reqTickByTickData(req_id, contract, tick_type, 0, False)
        self.logger.info(f"Requested tick-by-tick {tick_type} for {contract.symbol} (req_id: {req_id})")

    def cancel_tick_by_tick(self, req_id: int) -> None:
        if self.is_connected():
            try:
                self.cancelTickByTickData(req_id)
            except Exception as e:
                self.logger.debug(f"tick-by-tick cancellation warning for {req_id}: {e}")
        self.tick_by_tick.pop(req_id, None)
        self.market_data_errors.pop(req_id, None)

    def cancel_market_data(self, req_id: int) -> None:
        """
        Cancel market data subscription.
        
        Args:
            req_id: Request identifier to cancel
        """
        if not self.is_connected():
            # nothing to send: the subscription ended with the connection; its local state must not linger
            for table in (self.market_data, self.market_data_type, self.market_data_errors):
                table.pop(req_id, None)
            self.market_data_subscriptions.discard(req_id)
            return

        # Fix Issue #4: Only cancel if subscription is active to avoid Error 300
        if req_id in self.market_data_subscriptions or req_id in self.market_data:
            try:
                self.cancelMktData(req_id)
                self.logger.info(f"Cancelled market data subscription {req_id}")
            except Exception as e:
                # Log but don't fail on cancellation errors (often harmless)
                self.logger.debug(f"Cancellation warning for req_id {req_id}: {e}")
        else:
            self.logger.debug(f"No active subscription found for req_id {req_id}, skipping cancellation")
        
        self.market_data.pop(req_id, None)
        self.market_data_subscriptions.discard(req_id)
        self.market_data_type.pop(req_id, None)
        self.market_data_errors.pop(req_id, None)


    def request_historical_data(self, req_id: int, contract: Contract, end_date_time: str = "",
                               duration_str: str = "1 W", bar_size_setting: str = "1 day",
                               what_to_show: str = "TRADES", use_rth: bool = True,
                               format_date: int = 1) -> None:
        """Request historical data for a contract."""
        if not self.is_connected():
            raise ConnectionError("Not connected to TWS")

        # Clear any existing historical data for this request
        self.historical_data.pop(req_id, None)
        self.historical_data_errors.pop(req_id, None)
        self.historical_data_done[req_id] = threading.Event()

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
        return self._without_legacy_flags(order)

    def create_market_order(self, action: str, quantity: int) -> IBOrder:
        """Create a market order."""
        order = IBOrder()
        order.action = action
        order.totalQuantity = quantity
        order.orderType = "MKT"
        return self._without_legacy_flags(order)

    @staticmethod
    def _without_legacy_flags(order: IBOrder) -> IBOrder:
        """ibapi 9.81 sends eTradeOnly / firmQuoteOnly = True by default; current TWS rejects such an order with
        10268 "The 'EtradeOnly' order attribute is not supported" (P.06 paper finding): send them False."""
        order.eTradeOnly = False
        order.firmQuoteOnly = False
        return order