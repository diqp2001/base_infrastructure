"""
Comprehensive Interactive Brokers Market Data Examples

This module demonstrates all the enhanced market data capabilities of the
Interactive Brokers integration, including live data, historical data, 
market depth, scanner, contract details, and news data.

The examples show how to use both the low-level IBTWSClient and high-level
InteractiveBrokersBroker interfaces to access the full range of IB API features.
"""

import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from ibapi.contract import Contract
from ibapi.scanner import ScannerSubscription

from application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker
from application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ComprehensiveIBMarketDataExamples:
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
        self.config = {
            'host': host,
            'port': port,
            'client_id': client_id,
            'paper_trading': True,
            'timeout': 60,
            'account_id': 'DEFAULT'
        }
        
        self.broker: Optional[InteractiveBrokersBroker] = None
        self.connected = False
    
    def connect_to_ib(self) -> bool:
        """
        Establish connection to Interactive Brokers.
        
        Returns:
            True if connection successful
        """
        try:
            logger.info("Connecting to Interactive Brokers...")
            self.broker = InteractiveBrokersBroker(self.config)
            self.connected = self.broker.connect()
            
            if self.connected:
                logger.info("✅ Successfully connected to Interactive Brokers")
                return True
            else:
                logger.error("❌ Failed to connect to Interactive Brokers")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error connecting to IB: {e}")
            return False
    
    def disconnect_from_ib(self):
        """Disconnect from Interactive Brokers."""
        if self.broker and self.connected:
            self.broker.disconnect()
            self.connected = False
            logger.info("Disconnected from Interactive Brokers")
    
    def example_live_market_data(self):
        """
        Example 1: Live Market Data - Real-time quotes and streaming data
        
        Demonstrates:
        - Market data snapshots
        - Streaming market data subscriptions
        - Various tick types (price, size, generic)
        """
        logger.info("\\n=== Example 1: Live Market Data ===")
        
        if not self.connected:
            logger.error("Not connected to IB. Cannot run live market data example.")
            return
        
        try:
            # Create contracts for different asset types
            spy_contract = self.broker.create_stock_contract("SPY", "STK", "SMART")
            spy_contract.primaryExchange = "ARCA"
            
            es_contract = self.broker.create_stock_contract("ES", "FUT", "CME")
            
            # Example 1a: Market Data Snapshots
            logger.info("📊 Getting market data snapshots...")
            
            spy_snapshot = self.broker.get_market_data_snapshot(
                contract=spy_contract,
                generic_tick_list="225,232",  # Bid/Ask size, Auction data
                snapshot=True,
                timeout=10
            )
            
            if spy_snapshot and not spy_snapshot.get('error'):
                logger.info(f"SPY Snapshot: Bid={spy_snapshot.get('BID', 'N/A')}, Ask={spy_snapshot.get('ASK', 'N/A')}, Last={spy_snapshot.get('LAST', 'N/A')}")
                logger.info(f"SPY Volume: {spy_snapshot.get('VOLUME', 'N/A')}, Bid Size: {spy_snapshot.get('BID_SIZE', 'N/A')}")
            else:
                logger.warning(f"SPY snapshot failed: {spy_snapshot.get('error', 'Unknown error')}")
            
            # Example 1b: Streaming Market Data
            logger.info("📈 Subscribing to streaming market data...")
            
            subscription_id = self.broker.subscribe_market_data(es_contract, "225,232,236")
            
            if subscription_id > 0:
                logger.info(f"Subscribed to ES futures streaming data (ID: {subscription_id})")
                
                # Monitor streaming data for 30 seconds
                start_time = time.time()
                while time.time() - start_time < 30:
                    time.sleep(5)
                    
                    # Check for updated market data
                    if hasattr(self.broker.ib_connection, 'market_data') and subscription_id in self.broker.ib_connection.market_data:
                        data = self.broker.ib_connection.market_data[subscription_id]
                        prices = data.get('prices', {})
                        if prices:
                            logger.info(f"ES Streaming - Last: {prices.get(4, 'N/A')}, Bid: {prices.get(1, 'N/A')}, Ask: {prices.get(2, 'N/A')}")
                
                # Unsubscribe
                self.broker.unsubscribe_market_data(subscription_id)
                logger.info("Unsubscribed from streaming data")
            
        except Exception as e:
            logger.error(f"Error in live market data example: {e}")
    
    def example_historical_data(self):
        """
        Example 2: Historical Market Data - OHLCV bars and various timeframes
        
        Demonstrates:
        - Historical data requests
        - Different bar sizes and durations
        - Various data types (TRADES, BID, ASK, MIDPOINT)
        """
        logger.info("\\n=== Example 2: Historical Market Data ===")
        
        if not self.connected:
            logger.error("Not connected to IB. Cannot run historical data example.")
            return
        
        try:
            # Create contract for Apple stock
            aapl_contract = self.broker.create_stock_contract("AAPL", "STK", "SMART")
            aapl_contract.primaryExchange = "NASDAQ"
            
            # Example 2a: Daily bars for 1 month
            logger.info("📊 Fetching daily historical data for AAPL (1 month)...")
            
            daily_bars = self.broker.get_historical_data(
                contract=aapl_contract,
                end_date_time="",  # Current time
                duration_str="1 M",
                bar_size_setting="1 day",
                what_to_show="TRADES",
                use_rth=True
            )
            
            if daily_bars:
                logger.info(f"Received {len(daily_bars)} daily bars for AAPL")
                if len(daily_bars) > 0:
                    latest = daily_bars[-1]
                    logger.info(f"Latest bar: Date={latest['date']}, OHLC={latest['open']}/{latest['high']}/{latest['low']}/{latest['close']}, Volume={latest['volume']}")
                    
                    # Calculate some basic statistics
                    closes = [float(bar['close']) for bar in daily_bars[-10:]]  # Last 10 days
                    avg_close = sum(closes) / len(closes)
                    logger.info(f"Average close (last 10 days): ${avg_close:.2f}")
            else:
                logger.warning("No daily bars received for AAPL")
            
            # Example 2b: Intraday 5-minute bars
            logger.info("📊 Fetching 5-minute historical data for AAPL (1 day)...")
            
            minute_bars = self.broker.get_historical_data(
                contract=aapl_contract,
                duration_str="1 D",
                bar_size_setting="5 mins",
                what_to_show="TRADES",
                use_rth=True
            )
            
            if minute_bars:
                logger.info(f"Received {len(minute_bars)} 5-minute bars for AAPL")
                if len(minute_bars) > 0:
                    latest = minute_bars[-1]
                    logger.info(f"Latest 5-min bar: {latest['date']}, Close=${latest['close']}, Volume={latest['volume']}")
            
            # Example 2c: Futures historical data
            es_contract = self.broker.create_stock_contract("ES", "FUT", "CME")
            
            logger.info("📊 Fetching weekly historical data for ES futures...")
            
            weekly_bars = self.broker.get_historical_data(
                contract=es_contract,
                duration_str="3 M",  # 3 months
                bar_size_setting="1 week",
                what_to_show="TRADES"
            )
            
            if weekly_bars:
                logger.info(f"Received {len(weekly_bars)} weekly bars for ES")
                
        except Exception as e:
            logger.error(f"Error in historical data example: {e}")
    
    def example_market_depth(self):
        """
        Example 3: Market Depth (Level 2) - Order book data
        
        Demonstrates:
        - Level 2 market depth
        - Bid/ask order book
        - Market maker information
        """
        logger.info("\\n=== Example 3: Market Depth (Level 2) ===")
        
        if not self.connected:
            logger.error("Not connected to IB. Cannot run market depth example.")
            return
        
        try:
            # Create contract for a liquid stock
            spy_contract = self.broker.create_stock_contract("SPY", "STK", "SMART")
            spy_contract.primaryExchange = "ARCA"
            
            # Get market depth data
            logger.info("📊 Fetching market depth for SPY...")
            
            depth_data = self.broker.get_market_depth(spy_contract, num_rows=10, timeout=15)
            
            if depth_data and not depth_data.get('error'):
                logger.info(f"Market depth for {depth_data['symbol']}:")
                
                # Display bid side
                bids = depth_data.get('bids', [])
                if bids:
                    logger.info("BID SIDE:")
                    for i, bid in enumerate(bids[:5]):  # Top 5 bids
                        mm = f" ({bid['market_maker']})" if bid.get('market_maker') else ""
                        logger.info(f"  {i+1:2d}. ${bid['price']:<8.2f} x {bid['size']:<6d}{mm}")
                
                # Display ask side
                asks = depth_data.get('asks', [])
                if asks:
                    logger.info("ASK SIDE:")
                    for i, ask in enumerate(asks[:5]):  # Top 5 asks
                        mm = f" ({ask['market_maker']})" if ask.get('market_maker') else ""
                        logger.info(f"  {i+1:2d}. ${ask['price']:<8.2f} x {ask['size']:<6d}{mm}")
                
                # Calculate spread
                if bids and asks:
                    best_bid = bids[0]['price']
                    best_ask = asks[0]['price']
                    spread = best_ask - best_bid
                    logger.info(f"Best Bid/Ask: ${best_bid:.2f} / ${best_ask:.2f}, Spread: ${spread:.2f}")
                
            else:
                logger.warning(f"Market depth failed: {depth_data.get('error', 'No data received')}")
                
        except Exception as e:
            logger.error(f"Error in market depth example: {e}")
    
    def example_contract_details(self):
        """
        Example 4: Contract Details - Comprehensive contract information
        
        Demonstrates:
        - Contract details requests
        - Trading hours and exchange information
        - Contract specifications
        """
        logger.info("\\n=== Example 4: Contract Details ===")
        
        if not self.connected:
            logger.error("Not connected to IB. Cannot run contract details example.")
            return
        
        try:
            # Example 4a: Stock contract details
            aapl_contract = self.broker.create_stock_contract("AAPL", "STK", "SMART")
            
            logger.info("📊 Fetching contract details for AAPL...")
            
            aapl_details = self.broker.get_contract_details(aapl_contract, timeout=15)
            
            if aapl_details:
                logger.info(f"Found {len(aapl_details)} contract matches for AAPL")
                for i, detail in enumerate(aapl_details[:3]):  # Show first 3 matches
                    logger.info(f"  Contract {i+1}:")
                    logger.info(f"    Symbol: {detail['symbol']} ({detail['local_symbol']})")
                    logger.info(f"    Exchange: {detail['exchange']} / {detail['primary_exchange']}")
                    logger.info(f"    Currency: {detail['currency']}")
                    logger.info(f"    Market: {detail['market_name']}")
                    logger.info(f"    Min Tick: {detail['min_tick']}")
                    logger.info(f"    Trading Hours: {detail.get('trading_hours', 'N/A')[:50]}...")
            else:
                logger.warning("No contract details received for AAPL")
            
            # Example 4b: Futures contract details
            es_contract = self.broker.create_stock_contract("ES", "FUT", "CME")
            
            logger.info("📊 Fetching contract details for ES futures...")
            
            es_details = self.broker.get_contract_details(es_contract, timeout=15)
            
            if es_details:
                logger.info(f"Found {len(es_details)} ES futures contracts")
                for i, detail in enumerate(es_details[:2]):  # Show first 2 contracts
                    logger.info(f"  ES Contract {i+1}:")
                    logger.info(f"    Local Symbol: {detail['local_symbol']}")
                    logger.info(f"    Contract ID: {detail['contract_id']}")
                    logger.info(f"    Trading Class: {detail['trading_class']}")
                    logger.info(f"    Time Zone: {detail['time_zone_id']}")
            
        except Exception as e:
            logger.error(f"Error in contract details example: {e}")
    
    def example_market_scanner(self):
        """
        Example 5: Market Scanner - Find securities based on criteria
        
        Demonstrates:
        - Market scanner subscriptions
        - Custom screening criteria
        - Top movers, volume leaders, etc.
        """
        logger.info("\\n=== Example 5: Market Scanner ===")
        
        if not self.connected:
            logger.error("Not connected to IB. Cannot run market scanner example.")
            return
        
        try:
            # Create scanner subscription for top volume stocks
            scanner_sub = ScannerSubscription()
            scanner_sub.instrument = "STK"
            scanner_sub.locationCode = "STK.US.MAJOR"  # US major exchanges
            scanner_sub.scanCode = "TOP_VOLUME"  # Top volume stocks
            scanner_sub.numberOfRows = 20  # Get top 20 results
            scanner_sub.aboveVolume = 1000000  # Above 1M volume
            
            logger.info("📊 Running market scanner for top volume stocks...")
            
            scanner_results = self.broker.get_market_scanner_results(scanner_sub, timeout=30)
            
            if scanner_results:
                logger.info(f"Scanner found {len(scanner_results)} results:")
                
                for i, result in enumerate(scanner_results[:10]):  # Show top 10
                    contract = result['contract']
                    logger.info(f"  {result['rank']:2d}. {contract['symbol']:<6s} "
                              f"({contract['exchange']:<8s}) - {result['distance']}")
            else:
                logger.warning("No scanner results received")
                
        except Exception as e:
            logger.error(f"Error in market scanner example: {e}")
    
    def example_delayed_market_data(self):
        """
        Example 6: Delayed Market Data - 15-minute delayed quotes
        
        Demonstrates:
        - Delayed market data requests
        - Different delay types
        - Free market data options
        """
        logger.info("\\n=== Example 6: Delayed Market Data ===")
        
        if not self.connected:
            logger.error("Not connected to IB. Cannot run delayed market data example.")
            return
        
        try:
            # Create contract for delayed data test
            msft_contract = self.broker.create_stock_contract("MSFT", "STK", "SMART")
            msft_contract.primaryExchange = "NASDAQ"
            
            # Request delayed market data (15-minute delay)
            logger.info("📊 Requesting delayed market data for MSFT...")
            
            success = self.broker.request_delayed_market_data(msft_contract, delay_type=3)
            
            if success:
                logger.info("Delayed market data request sent successfully")
                
                # Wait for data and check subscription
                time.sleep(5)
                
                # Note: In a real application, you would handle this through callbacks
                # or by checking the market_data dictionary periodically
                logger.info("Delayed market data is now streaming (check callbacks for updates)")
                
            else:
                logger.warning("Failed to request delayed market data")
                
        except Exception as e:
            logger.error(f"Error in delayed market data example: {e}")
    
    def example_news_data(self):
        """
        Example 7: News Data - Real-time news feeds
        
        Demonstrates:
        - News tick subscriptions
        - News article retrieval
        - Symbol-specific news
        """
        logger.info("\\n=== Example 7: News Data ===")
        
        if not self.connected:
            logger.error("Not connected to IB. Cannot run news data example.")
            return
        
        try:
            # Create contract for news data
            tsla_contract = self.broker.create_stock_contract("TSLA", "STK", "SMART")
            tsla_contract.primaryExchange = "NASDAQ"
            
            logger.info("📊 Requesting news data for TSLA...")
            
            news_items = self.broker.get_news_data(tsla_contract, timeout=15)
            
            if news_items:
                logger.info(f"Received {len(news_items)} news items for TSLA:")
                
                for i, news in enumerate(news_items[:5]):  # Show first 5 news items
                    timestamp = datetime.fromtimestamp(int(news['timestamp']))
                    logger.info(f"  {i+1}. [{timestamp.strftime('%H:%M:%S')}] {news['headline'][:60]}...")
                    logger.info(f"     Provider: {news['provider_code']}, ID: {news['article_id']}")
            else:
                logger.warning("No news data received for TSLA")
                logger.info("Note: News data requires appropriate market data subscriptions")
                
        except Exception as e:
            logger.error(f"Error in news data example: {e}")
    
    def run_all_examples(self):
        """
        Run all market data examples in sequence.
        """
        logger.info("🚀 Starting Comprehensive IB Market Data Examples")
        logger.info("=" * 60)
        
        # Connect to IB
        if not self.connect_to_ib():
            logger.error("Cannot run examples - failed to connect to Interactive Brokers")
            return
        
        try:
            # Run all examples
            self.example_live_market_data()
            time.sleep(2)  # Brief pause between examples
            
            self.example_historical_data()
            time.sleep(2)
            
            self.example_market_depth()
            time.sleep(2)
            
            self.example_contract_details()
            time.sleep(2)
            
            self.example_market_scanner()
            time.sleep(2)
            
            self.example_delayed_market_data()
            time.sleep(2)
            
            self.example_news_data()
            
            logger.info("\\n✅ All examples completed successfully!")
            
        except KeyboardInterrupt:
            logger.info("Examples interrupted by user")
        except Exception as e:
            logger.error(f"Error running examples: {e}")
        finally:
            # Cleanup
            self.disconnect_from_ib()
            logger.info("\\n🏁 Examples session finished")


def main():
    """
    Main function to run the examples.
    
    Modify the connection parameters below to match your IB Gateway/TWS setup.
    """
    # Configuration - modify as needed
    HOST = "127.0.0.1"      # IB Gateway/TWS host
    PORT = 7497             # 7497 for paper trading, 7496 for live
    CLIENT_ID = 1           # Unique client ID
    
    # Create examples instance
    examples = ComprehensiveIBMarketDataExamples(
        host=HOST,
        port=PORT,
        client_id=CLIENT_ID
    )
    
    # Run all examples
    examples.run_all_examples()


if __name__ == "__main__":
    main()


# Additional utility functions for testing specific features

def test_single_feature():
    """
    Function to test a single feature quickly.
    Useful for development and debugging.
    """
    examples = ComprehensiveIBMarketDataExamples()
    
    if examples.connect_to_ib():
        try:
            # Test a specific feature here
            # examples.example_live_market_data()
            # examples.example_historical_data()
            # examples.example_market_depth()
            examples.example_contract_details()
            
        finally:
            examples.disconnect_from_ib()


def performance_test():
    """
    Performance test for market data retrieval.
    Tests speed and reliability of various data requests.
    """
    examples = ComprehensiveIBMarketDataExamples()
    
    if examples.connect_to_ib():
        try:
            symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
            start_time = time.time()
            
            logger.info(f"Performance test: fetching data for {len(symbols)} symbols...")
            
            for symbol in symbols:
                contract = examples.broker.create_stock_contract(symbol, "STK", "SMART")
                contract.primaryExchange = "NASDAQ"
                
                # Test snapshot speed
                snapshot = examples.broker.get_market_data_snapshot(contract, timeout=5)
                if snapshot and not snapshot.get('error'):
                    logger.info(f"{symbol}: Last={snapshot.get('LAST', 'N/A')}")
                
                time.sleep(0.5)  # Rate limiting
            
            elapsed = time.time() - start_time
            logger.info(f"Performance test completed in {elapsed:.2f} seconds")
            
        finally:
            examples.disconnect_from_ib()


# Example configurations for different use cases

TRADING_CONFIG = {
    'host': '127.0.0.1',
    'port': 7496,  # Live trading port
    'client_id': 1,
    'paper_trading': False
}

PAPER_TRADING_CONFIG = {
    'host': '127.0.0.1', 
    'port': 7497,  # Paper trading port
    'client_id': 1,
    'paper_trading': True
}

DEVELOPMENT_CONFIG = {
    'host': '127.0.0.1',
    'port': 7497,
    'client_id': 999,  # High client ID for development
    'paper_trading': True
}