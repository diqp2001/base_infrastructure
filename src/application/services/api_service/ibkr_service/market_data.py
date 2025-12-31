"""
Comprehensive Interactive Brokers Market Data Examples

This module demonstrates all the enhanced market data capabilities of the
Interactive Brokers integration, including live data, historical data, 
market depth, scanner, contract details, and news data.

The examples show how to use the InteractiveBrokersApiService wrapper to
access the full range of IB API features through the misbuffet broker infrastructure.

USAGE:
    python comprehensive_market_data_examples.py          # Run all examples
    python comprehensive_market_data_examples.py test     # Run access level test pipeline only

ACCESS LEVEL TEST PIPELINE:
The test pipeline systematically checks what IB API functionality is available
with your current account setup, market data subscriptions, and permissions.
It provides a detailed report showing:
- What's working (✅)
- What's limited or requires subscriptions (⚠️)  
- What's not available (❌)
- Specific recommendations for upgrades

This is especially useful for:
- Debugging connection issues
- Understanding account limitations
- Planning market data subscription upgrades
- Verifying paper vs live trading capabilities
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from ibapi.contract import Contract
from ibapi.scanner import ScannerSubscription

from src.application.services.api_service.ibkr_service.interactive_brokers_api_service import InteractiveBrokersApiService


# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MarketData(InteractiveBrokersApiService):
    """
    Comprehensive examples demonstrating all Interactive Brokers market data capabilities.
    """
    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = 1):
        """
        Initialize the examples class.
        
        Args:
            host: IB Gateway/TWS host
            port: IB Gateway/TWS port (7497 for paper, 7496 for live)
            client_id: Unique client ID
        """
        super().__init__(host=host,port=port,client_id=client_id)
    

    def get_future_historical_data(
            self,
            symbol: str = "ES",
            exchange: str = "CME",
            currency: str = "USD",
            duration_str: str = "6 M",
            bar_size_setting: str = "5 mins",
        ):
        """
        Example: Front-Month Futures Historical Data

        Pulls:
        - Front-month futures contract
        - 5-minute bars
        - Last N duration
        """

        if not self.connected:
            self.ib_broker.connect()
            self.connected = True

        logger.info("\n=== Futures Historical Data ===")

        if not self.connected:
            logger.error("Not connected to IB. Cannot fetch futures historical data.")
            return

        try:
            # =========================================================
            # Create futures contract shell (front month resolved later)
            # =========================================================
            contract = self.ib_broker.create_stock_contract(
                symbol=symbol,
                secType="FUT",
                exchange=exchange
            )
            contract.currency = currency

            logger.info("📊 Fetching futures data ...")
            logger.info(
                f"Contract shell: symbol={contract.symbol}, "
                f"secType={contract.secType}, "
                f"exchange={contract.exchange}, "
                f"currency={contract.currency}"
            )

            bars = self.ib_broker.get_historical_data(
                contract=contract,
                end_date_time="",          # now
                duration_str=duration_str,
                bar_size_setting=bar_size_setting,
                what_to_show="TRADES",
                use_rth=False,             # Futures trade nearly 24h
                timeout=30
            )

            if not bars:
                logger.warning("No futures historical data returned.")
                return

            logger.info(
                f"✅ Received {len(bars)} bars"
            )

            first_bar = bars[0]
            last_bar = bars[-1]

            logger.info(
                f"📈 Date range: {first_bar['date']} → {last_bar['date']}"
            )

            logger.info(
                f"Latest bar | "
                f"Open={last_bar['open']} "
                f"High={last_bar['high']} "
                f"Low={last_bar['low']} "
                f"Close={last_bar['close']} "
                f"Volume={last_bar.get('volume')}"
            )

            return bars

        except Exception as e:
            logger.error(f"Error fetching futures historical data: {e}")


    def get_index_historical_data(self,symbol:str="SPX",exchange:str="CBOE", currency:str="USD",duration_str:str="6 M", bar_size_setting:str="5 mins"):
        """
        Example: S&P 500 Index (SPX) Historical Data

        Pulls:
        - SPX Index (cash index, not futures)
        - 5-minute bars
        - Last 6 months
        """
        
        if not self.connected:
            self.ib_broker.connect()
            self.connected = True
        logger.info("\n=== Index Historical Data ===")

        if not self.connected:
            logger.error("Not connected to IB. Cannot fetch SPX historical data.")
            return

        try:
            # =========================================================
            # Create  index contract
            # =========================================================
            contract = self.ib_broker.create_index_contract(
                symbol=symbol,
                exchange=exchange,
                currency=currency
            )

            logger.info("📊 Fetching index data ...")
            logger.info(
                f"Contract details: symbol={contract.symbol}, "
                f"secType={contract.secType}, "
                f"exchange={contract.exchange}, "
                f"currency={contract.currency}"
            )

            bars = self.ib_broker.get_historical_data(
                contract=contract,
                end_date_time="",          # now
                duration_str=duration_str,
                bar_size_setting=bar_size_setting,
                what_to_show="TRADES",      # 🔴 REQUIRED for indices
                use_rth=True,              # SPX only trades during RTH
                timeout=30
            )

            if not bars:
                logger.warning("No historical data returned.")
                return

            logger.info(
                f"✅ Received {len(bars)}  bars "
            )

            first_bar = bars[0]
            last_bar = bars[-1]

            logger.info(
                f"📈 Date range: {first_bar['date']} → {last_bar['date']}"
            )

            logger.info(
                f"Latest bar | "
                f"Open={last_bar['open']} "
                f"High={last_bar['high']} "
                f"Low={last_bar['low']} "
                f"Close={last_bar['close']}"
            )
            return bars

        except Exception as e:
            logger.error(f"Error fetching index historical data: {e}")

    