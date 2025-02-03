import os
from threading import Thread
import time
from typing import Optional, List, Dict, Any
import pandas as pd
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order


class InteractiveBrokersApiManager(EWrapper, EClient):
    """
    Manages interactions with the Interactive Brokers official API for connection, data, trading, and account management.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1):
        """
        Initialize the IBKR API manager.

        Args:
        - host: TWS/Gateway host (default: '127.0.0.1').
        - port: TWS/Gateway port (default: 7497 for paper trading, 7496 for live trading).
        - client_id: Unique client ID for the session (default: 1).
        """
        EClient.__init__(self, self)
        EWrapper.__init__(self)
        self.host = host
        self.port = port
        self.client_id = client_id
        self.data = []
        self.order_id = None

    def connect_api(self):
        """
        Connect to the Interactive Brokers TWS or IB Gateway API.
        """
        self.connect(self.host, self.port, self.client_id)
        self.run_thread = Thread(target=self.run, daemon=True)
        self.run_thread.start()
        print(f"Connected to IBKR on {self.host}:{self.port} with client ID {self.client_id}")

    def disconnect_api(self):
        """
        Disconnect from the IBKR API.
        """
        self.disconnect()
        print("Disconnected from IBKR")

    def fetch_market_data(self, symbol: str, exchange: str = "SMART", currency: str = "USD") -> pd.DataFrame:
        """
        Fetch real-time market data for a specific instrument.

        Args:
        - symbol: The ticker symbol (e.g., 'AAPL').
        - exchange: The exchange for the instrument (default: 'SMART').
        - currency: The currency of the instrument (default: 'USD').

        Returns:
        - DataFrame: Real-time market data as a Pandas DataFrame.
        """
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = exchange
        contract.currency = currency

        self.reqMarketDataType(1)  # Live data
        self.reqMktData(1, contract, "", False, False, [])

        # Allow time for data to be populated
        time.sleep(2)

        df = pd.DataFrame(self.data, columns=["timestamp", "symbol", "price", "volume"])
        return df

    def place_order(self, symbol: str, action: str, quantity: int, order_type: str = "MKT") -> str:
        """
        Place a market or limit order for a specific stock.

        Args:
        - symbol: The stock symbol (e.g., 'AAPL').
        - action: Buy or Sell.
        - quantity: Number of shares to trade.
        - order_type: Order type (default: 'MKT' for market order).

        Returns:
        - str: Order ID.
        """
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"

        order = Order()
        order.action = action.upper()  # BUY or SELL
        order.orderType = order_type
        order.totalQuantity = quantity

        self.reqIds(-1)
        time.sleep(1)  # Wait for the next valid order ID
        order_id = self.order_id
        self.placeOrder(order_id, contract, order)
        print(f"Order {order_id} placed: {action} {quantity} {symbol}")
        return order_id

    def fetch_account_summary(self) -> pd.DataFrame:
        """
        Fetch account summary, including balances and net liquidation value.

        Returns:
        - DataFrame: Account summary as a Pandas DataFrame.
        """
        self.reqAccountSummary(9001, "All", "NetLiquidation,TotalCashValue")
        time.sleep(2)
        return pd.DataFrame(self.data)

    # Callbacks and helpers
    def nextValidId(self, orderId: int):
        """
        Callback for receiving the next valid order ID.
        """
        super().nextValidId(orderId)
        self.order_id = orderId

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        """
        Callback for account summary data.
        """
        self.data.append({"account": account, "tag": tag, "value": value, "currency": currency})

    def tickPrice(self, reqId: int, tickType: int, price: float, attrib):
        """
        Callback for tick price updates.
        """
        self.data.append({"tickType": tickType, "price": price})
