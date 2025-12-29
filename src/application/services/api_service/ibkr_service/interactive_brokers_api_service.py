"""
DEPRECATED: This InteractiveBrokersApiService is deprecated.
Use src.application.services.misbuffet.brokers.interactive_brokers_broker.InteractiveBrokersBroker instead.

This service has been superseded by the more comprehensive misbuffet broker implementation
which provides better error handling, connection management, and integration with the
existing domain architecture.
"""

from threading import Thread
import time
from typing import Optional
import pandas as pd
import warnings
from ibapi.contract import Contract
from ibapi.order import Order

from application.services.misbuffet.brokers.broker_factory import create_interactive_brokers_broker



class InteractiveBrokersApiService():
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
        
        
        
        
        self.host = host
        self.port = port
        self.client_id = client_id
        self.data = []
        self.order_id = None
        self.connected = False
        
        # Suggest using misbuffet broker instead
        self.ib_config = {
            'host': host,
            'port': port,
            'client_id': client_id,
            'timeout': 60,
            'paper_trading': port == 7497,
            'account_id': 'DEFAULT',
            'enable_logging': True
        }
        self.ib_broker = create_interactive_brokers_broker(**self.ib_config)
   

    def complete_pipeline(self,symbol: str ="ES", exchange: str = "GLOBEX", 
                         currency: str = "USD", duration: int = 2):
        """
        DEPRECATED: Use InteractiveBrokersBroker.get_market_data() instead.
        """
        warnings.warn(
            "complete_pipeline is deprecated. Use InteractiveBrokersBroker instead.",
            DeprecationWarning,
            stacklevel=2
        )
        self.ib_broker.connect()

        df = self.ib_broker.get_market_data(symbol=symbol)

        self.ib_broker._disconnect_impl()

        
    

    

  

    