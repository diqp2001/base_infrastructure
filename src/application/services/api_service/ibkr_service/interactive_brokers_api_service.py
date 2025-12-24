"""
DEPRECATED: This InteractiveBrokersApiService is deprecated.
Use src.application.services.misbuffet.brokers.interactive_brokers_broker.InteractiveBrokersBroker instead.

This service has been superseded by the more comprehensive misbuffet broker implementation
which provides better error handling, connection management, and integration with the
existing domain architecture.
"""

import os
from threading import Thread
import time
from typing import Optional, List, Dict, Any
import pandas as pd
import warnings
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ..api_service import ApiService

# Import the preferred misbuffet broker
from src.application.services.misbuffet.brokers.interactive_brokers_broker import InteractiveBrokersBroker


class InteractiveBrokersApiService(EWrapper, EClient, ApiService):
    """
    DEPRECATED: Service for managing interactions with the Interactive Brokers official API.
    
    This class is deprecated. Use InteractiveBrokersBroker from the misbuffet services instead,
    which provides better connection management, error handling, and architecture integration.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1):
        """
        Initialize the IBKR API service.
        
        DEPRECATED: Use InteractiveBrokersBroker instead.

        Args:
            host: TWS/Gateway host (default: '127.0.0.1')
            port: TWS/Gateway port (default: 7497 for paper trading, 7496 for live trading)
            client_id: Unique client ID for the session (default: 1)
        """
        warnings.warn(
            "InteractiveBrokersApiService is deprecated. Use "
            "InteractiveBrokersBroker from misbuffet.brokers instead.",
            DeprecationWarning,
            stacklevel=2
        )
        
        EClient.__init__(self, self)
        EWrapper.__init__(self)
        ApiService.__init__(self, f"http://{host}:{port}")
        
        self.host = host
        self.port = port
        self.client_id = client_id
        self.data = []
        self.order_id = None
        self.connected = False
        
        # Suggest using misbuffet broker instead
        self._recommended_broker_config = {
            'host': host,
            'port': port,
            'client_id': client_id,
            'timeout': 60,
            'paper_trading': port == 7497,
            'account_id': 'DEFAULT',
            'enable_logging': True
        }
    def get_recommended_broker(self) -> InteractiveBrokersBroker:
        """
        Get a properly configured InteractiveBrokersBroker instance.
        
        Returns:
            InteractiveBrokersBroker instance configured with the same parameters.
        """
        return InteractiveBrokersBroker(self._recommended_broker_config)

    def complete_pipeline(self,symbol: str ="ES", exchange: str = "SMART", 
                         currency: str = "USD", duration: int = 2):
        """
        DEPRECATED: Use InteractiveBrokersBroker.get_market_data() instead.
        """
        warnings.warn(
            "complete_pipeline is deprecated. Use InteractiveBrokersBroker instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.connect_api()

        df = self.fetch_market_data(symbol, exchange, currency, duration)

        self.disconnect_api()
    

    def connect_api(self):
        """
        Connect to the Interactive Brokers TWS or IB Gateway API.
        """
        try:
            self.connect(self.host, self.port, self.client_id)
            self.run_thread = Thread(target=self.run, daemon=True)
            self.run_thread.start()
            self.connected = True
            print(f"Connected to IBKR on {self.host}:{self.port} with client ID {self.client_id}")
        except Exception as e:
            print(f"Failed to connect to IBKR: {e}")
            self.connected = False

    def disconnect_api(self):
        """
        Disconnect from the IBKR API.
        """
        try:
            self.disconnect()
            self.connected = False
            print("Disconnected from IBKR")
        except Exception as e:
            print(f"Error disconnecting from IBKR: {e}")

    def is_connected(self) -> bool:
        """
        Check if the service is connected to IBKR.
        
        Returns:
            True if connected, False otherwise
        """
        return self.connected

    def fetch_market_data(self, symbol: str, exchange: str = "CME", 
                         currency: str = "USD", duration: int = 2) -> pd.DataFrame:
        """
        Fetch real-time market data for a specific instrument.

        Args:
            symbol: The ticker symbol (e.g., 'AAPL')
            exchange: The exchange for the instrument (default: 'SMART')
            currency: The currency of the instrument (default: 'USD')
            duration: Time to wait for data collection in seconds

        Returns:
            DataFrame with real-time market data
        """
        if not self.connected:
            raise ConnectionError("Not connected to IBKR API")
            
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "FUT"
        contract.exchange = exchange
        contract.currency = currency

        self.data.clear()  # Clear previous data
        self.reqMarketDataType(1)  # Live data
        self.reqMktData(1, contract, "", False, False, [])

        # Allow time for data to be populated
        time.sleep(duration)
        
        # Cancel market data request
        self.cancelMktData(1)

        df = pd.DataFrame(self.data, columns=["timestamp", "symbol", "price", "volume"])
        return df

    def place_market_order(self, symbol: str, action: str, quantity: int) -> Optional[str]:
        """
        Place a market order for a specific stock.

        Args:
            symbol: The stock symbol (e.g., 'AAPL')
            action: 'BUY' or 'SELL'
            quantity: Number of shares to trade

        Returns:
            Order ID if successful, None otherwise
        """
        return self.place_order(symbol, action, quantity, "MKT")

    def place_limit_order(self, symbol: str, action: str, quantity: int, 
                         limit_price: float) -> Optional[str]:
        """
        Place a limit order for a specific stock.

        Args:
            symbol: The stock symbol (e.g., 'AAPL')
            action: 'BUY' or 'SELL'
            quantity: Number of shares to trade
            limit_price: Limit price for the order

        Returns:
            Order ID if successful, None otherwise
        """
        return self.place_order(symbol, action, quantity, "LMT", limit_price)

    def place_order(self, symbol: str, action: str, quantity: int, 
                   order_type: str = "MKT", limit_price: float = None) -> Optional[str]:
        """
        Place an order for a specific stock.

        Args:
            symbol: The stock symbol (e.g., 'AAPL')
            action: 'BUY' or 'SELL'
            quantity: Number of shares to trade
            order_type: Order type ('MKT', 'LMT', etc.)
            limit_price: Limit price (required for limit orders)

        Returns:
            Order ID if successful, None otherwise
        """
        if not self.connected:
            raise ConnectionError("Not connected to IBKR API")
            
        try:
            contract = Contract()
            contract.symbol = symbol
            contract.secType = "STK"
            contract.exchange = "SMART"
            contract.currency = "USD"

            order = Order()
            order.action = action.upper()
            order.orderType = order_type
            order.totalQuantity = quantity
            
            if order_type == "LMT" and limit_price is not None:
                order.lmtPrice = limit_price

            self.reqIds(-1)
            time.sleep(1)  # Wait for the next valid order ID
            
            if self.order_id is None:
                print("Failed to get valid order ID")
                return None
                
            order_id = self.order_id
            self.placeOrder(order_id, contract, order)
            print(f"Order {order_id} placed: {action} {quantity} {symbol}")
            return str(order_id)
            
        except Exception as e:
            print(f"Error placing order: {e}")
            return None

    def fetch_account_summary(self) -> pd.DataFrame:
        """
        Fetch account summary, including balances and net liquidation value.

        Returns:
            DataFrame with account summary information
        """
        if not self.connected:
            raise ConnectionError("Not connected to IBKR API")
            
        self.data.clear()  # Clear previous data
        self.reqAccountSummary(9001, "All", "NetLiquidation,TotalCashValue,BuyingPower")
        time.sleep(2)
        
        account_data = [item for item in self.data if isinstance(item, dict) and 'account' in item]
        return pd.DataFrame(account_data)

    def get_positions(self) -> pd.DataFrame:
        """
        Get current positions in the account.
        
        Returns:
            DataFrame with position information
        """
        if not self.connected:
            raise ConnectionError("Not connected to IBKR API")
            
        self.data.clear()
        self.reqPositions()
        time.sleep(2)
        self.cancelPositions()
        
        positions_data = [item for item in self.data if isinstance(item, dict) and 'position' in item]
        return pd.DataFrame(positions_data)

    # Callbacks and helpers
    def nextValidId(self, orderId: int):
        """Callback for receiving the next valid order ID."""
        super().nextValidId(orderId)
        self.order_id = orderId

    def accountSummary(self, reqId: int, account: str, tag: str, value: str, currency: str):
        """Callback for account summary data."""
        self.data.append({
            "account": account, 
            "tag": tag, 
            "value": value, 
            "currency": currency
        })

    def position(self, account: str, contract: Contract, position: float, avgCost: float):
        """Callback for position data."""
        self.data.append({
            "account": account,
            "symbol": contract.symbol,
            "position": position,
            "avgCost": avgCost,
            "secType": contract.secType,
            "currency": contract.currency
        })

    def tickPrice(self, reqId: int, tickType: int, price: float, attrib):
        """Callback for tick price updates."""
        timestamp = time.time()
        self.data.append({
            "timestamp": timestamp,
            "tickType": tickType, 
            "price": price
        })

    def error(self, reqId: int, errorCode: int, errorString: str):
        """Callback for error messages."""
        print(f"Error {errorCode}: {errorString}")