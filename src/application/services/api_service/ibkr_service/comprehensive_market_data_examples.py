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
from application.services.misbuffet.brokers.ibkr.interactive_brokers_broker import InteractiveBrokersBroker
from application.services.misbuffet.brokers.ibkr.IBTWSClient import IBTWSClient

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ComprehensiveIBMarketDataExamples(InteractiveBrokersApiService):
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
            spy_contract = self.ib_broker.create_stock_contract("SPY", "STK", "SMART")
            spy_contract.primaryExchange = "ARCA"
            
            es_contract = self.ib_broker.create_stock_contract("ES", "FUT", "CME")
            
            # Example 1a: Market Data Snapshots
            logger.info("📊 Getting market data snapshots...")
            
            spy_snapshot = self.ib_broker.get_market_data_snapshot(
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
            
            subscription_id = self.ib_broker.subscribe_market_data(es_contract, "225,232,236")
            
            if subscription_id > 0:
                logger.info(f"Subscribed to ES futures streaming data (ID: {subscription_id})")
                
                # Monitor streaming data for 30 seconds
                start_time = time.time()
                while time.time() - start_time < 30:
                    time.sleep(5)
                    
                    # Check for updated market data
                    if hasattr(self.ib_broker.ib_connection, 'market_data') and subscription_id in self.ib_broker.ib_connection.market_data:
                        data = self.ib_broker.ib_connection.market_data[subscription_id]
                        prices = data.get('prices', {})
                        if prices:
                            logger.info(f"ES Streaming - Last: {prices.get(4, 'N/A')}, Bid: {prices.get(1, 'N/A')}, Ask: {prices.get(2, 'N/A')}")
                
                # Unsubscribe
                self.ib_broker.unsubscribe_market_data(subscription_id)
                logger.info("Unsubscribed from streaming data")
            
            
        except Exception as e:
            logger.error(f"Error in live market data example: {e}")
    
    def example_sp500_future_historical_data(self):
        """
        Example: S&P 500 (ES) Front-Month Futures Historical Data

        Pulls:
        - ES (S&P 500 E-mini)
        - Front-month maturity (nearest active contract)
        - 5-minute bars
        - Last 6 months
        """

        logger.info("\n=== Example: S&P 500 Front-Month Futures Historical Data ===")

        if not self.connected:
            logger.error("Not connected to IB. Cannot fetch ES historical data.")
            return

        try:
            # =========================================================
            # Create ES futures contract (front month)
            # =========================================================
            es_contract = self.ib_broker.create_stock_contract(
                symbol="ES",
                secType="FUT",
                exchange="CME"
            )
            es_contract.currency = "USD"
            # IMPORTANT:
            # No lastTradeDateOrContractMonth specified → IB returns front month

            logger.info("📊 Fetching 5-minute ES futures data (last 6 months)...")
            logger.info(f"Contract details: symbol={es_contract.symbol}, secType={es_contract.secType}, "
                       f"exchange={es_contract.exchange}, currency={es_contract.currency}")

            es_bars = self.ib_broker.get_historical_data(
                contract=es_contract,
                end_date_time="",          # now
                duration_str="6 M",
                bar_size_setting="5 mins",
                what_to_show="TRADES",
                use_rth=False,             # Futures trade nearly 24h
                timeout=30                 # Increased timeout for debugging
            )

            if not es_bars:
                logger.warning("No ES historical data returned.")
                return

            logger.info(
                f"✅ Received {len(es_bars)} 5-minute bars for ES (front month)"
            )

            first_bar = es_bars[0]
            last_bar = es_bars[-1]

            logger.info(
                f"📈 Date range: {first_bar['date']} → {last_bar['date']}"
            )

            logger.info(
                f"Latest bar | "
                f"Open={last_bar['open']} "
                f"High={last_bar['high']} "
                f"Low={last_bar['low']} "
                f"Close={last_bar['close']} "
                f"Volume={last_bar['volume']}"
            )

        except Exception as e:
            logger.error(f"Error fetching ES futures historical data: {e}")

    def example_sp500_index_historical_data(self):
        """
        Example: S&P 500 Index (SPX) Historical Data

        Pulls:
        - SPX Index (cash index, not futures)
        - 5-minute bars
        - Last 6 months
        """

        logger.info("\n=== Example: S&P 500 Index (SPX) Historical Data ===")

        if not self.connected:
            logger.error("Not connected to IB. Cannot fetch SPX historical data.")
            return

        try:
            # =========================================================
            # Create SPX index contract
            # =========================================================
            spx_contract = self.ib_broker.create_index_contract(
                symbol="SPX",
                exchange="CBOE",
                currency="USD"
            )

            logger.info("📊 Fetching 5-minute SPX index data (last 6 months)...")
            logger.info(
                f"Contract details: symbol={spx_contract.symbol}, "
                f"secType={spx_contract.secType}, "
                f"exchange={spx_contract.exchange}, "
                f"currency={spx_contract.currency}"
            )

            spx_bars = self.ib_broker.get_historical_data(
                contract=spx_contract,
                end_date_time="",          # now
                duration_str="6 M",
                bar_size_setting="5 mins",
                what_to_show="TRADES",      # 🔴 REQUIRED for indices
                use_rth=True,              # SPX only trades during RTH
                timeout=30
            )

            if not spx_bars:
                logger.warning("No SPX historical data returned.")
                return

            logger.info(
                f"✅ Received {len(spx_bars)} 5-minute bars for SPX"
            )

            first_bar = spx_bars[0]
            last_bar = spx_bars[-1]

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

        except Exception as e:
            logger.error(f"Error fetching SPX index historical data: {e}")

    def example_TR_10_YR_future_historical_data(self):
        """
        Example: US Treasury 10-Year (ZN) Front-Month Futures Historical Data

        Pulls:
        - ZN (10-Year U.S. Treasury Note futures)
        - Front-month maturity (nearest active contract)
        - 5-minute bars
        - Last 6 months
        """

        logger.info("\n=== Example: US Treasury 10-Year Front-Month Futures Historical Data ===")

        if not self.connected:
            logger.error("Not connected to IB. Cannot fetch ZN historical data.")
            return

        try:
            # =========================================================
            # Create ZN futures contract (front month)
            # =========================================================
            zn_contract = self.ib_broker.create_stock_contract(
                symbol="ZN",
                secType="FUT",
                exchange="CBOT"
            )
            zn_contract.currency = "USD"
            # IMPORTANT:
            # No lastTradeDateOrContractMonth specified → IB returns front month

            logger.info("📊 Fetching 5-minute ZN futures data (last 6 months)...")
            logger.info(f"Contract details: symbol={zn_contract.symbol}, secType={zn_contract.secType}, "
                       f"exchange={zn_contract.exchange}, currency={zn_contract.currency}")

            zn_bars = self.ib_broker.get_historical_data(
                contract=zn_contract,
                end_date_time="",          # now
                duration_str="6 M",
                bar_size_setting="5 mins",
                what_to_show="TRADES",
                use_rth=False,             # Treasury futures trade nearly 24h
                timeout=30                 # Increased timeout for debugging
            )

            if not zn_bars:
                logger.warning("No ZN historical data returned.")
                return

            logger.info(
                f"✅ Received {len(zn_bars)} 5-minute bars for ZN (front month)"
            )

            first_bar = zn_bars[0]
            last_bar = zn_bars[-1]

            logger.info(
                f"📈 Date range: {first_bar['date']} → {last_bar['date']}"
            )

            logger.info(
                f"Latest bar | "
                f"Open={last_bar['open']} "
                f"High={last_bar['high']} "
                f"Low={last_bar['low']} "
                f"Close={last_bar['close']} "
                f"Volume={last_bar['volume']}"
            )

        except Exception as e:
            logger.error(f"Error fetching ZN futures historical data: {e}")

    def example_historical_data(self):
        """
        Example 2: Historical Market Data (Combined)

        Demonstrates:
        - Standard historical data usage (stocks + futures)
        - Multiple bar sizes and durations
        - OHLCV inspection and simple statistics
        - Discovery of IBKR historical lookback limits for:
            * Daily
            * Hourly
            * 10-minute
            * 5-minute
            * 1-minute
        """

        logger.info("\n=== Example 2: Historical Market Data ===")

        if not self.connected:
            logger.error("Not connected to IB. Cannot run historical data example.")
            return

        try:
            # =========================================================
            # Base contract: AAPL
            # =========================================================
            aapl_contract = self.ib_broker.create_stock_contract("AAPL", "STK", "SMART")
            aapl_contract.primaryExchange = "NASDAQ"

            # =========================================================
            # 2a — Daily bars (1 month)
            # =========================================================
            logger.info("📊 Fetching daily historical data for AAPL (1 month)...")

            daily_bars = self.ib_broker.get_historical_data(
                contract=aapl_contract,
                end_date_time="",
                duration_str="1 M",
                bar_size_setting="1 day",
                what_to_show="TRADES",
                use_rth=True
            )

            if daily_bars:
                logger.info(f"Received {len(daily_bars)} daily bars for AAPL")

                latest = daily_bars[-1]
                logger.info(
                    f"Latest bar: Date={latest['date']}, "
                    f"OHLC={latest['open']}/{latest['high']}/{latest['low']}/{latest['close']}, "
                    f"Volume={latest['volume']}"
                )

                closes = [float(bar["close"]) for bar in daily_bars[-10:]]
                avg_close = sum(closes) / len(closes)
                logger.info(f"Average close (last 10 days): ${avg_close:.2f}")
            else:
                logger.warning("No daily bars received for AAPL")

            # =========================================================
            # 2b — Intraday 5-minute bars (1 day)
            # =========================================================
            logger.info("📊 Fetching 5-minute historical data for AAPL (1 day)...")

            minute_bars = self.ib_broker.get_historical_data(
                contract=aapl_contract,
                duration_str="1 D",
                bar_size_setting="5 mins",
                what_to_show="TRADES",
                use_rth=True
            )

            if minute_bars:
                logger.info(f"Received {len(minute_bars)} 5-minute bars for AAPL")
                latest = minute_bars[-1]
                logger.info(
                    f"Latest 5-min bar: {latest['date']}, "
                    f"Close=${latest['close']}, Volume={latest['volume']}"
                )
            else:
                logger.warning("No 5-minute bars received for AAPL")

            # =========================================================
            # 2c — Futures historical data (ES weekly)
            # =========================================================
            logger.info("📊 Fetching weekly historical data for ES futures...")

            es_contract = self.ib_broker.create_stock_contract("ES", "FUT", "CME")

            weekly_bars = self.ib_broker.get_historical_data(
                contract=es_contract,
                duration_str="3 M",
                bar_size_setting="1 week",
                what_to_show="TRADES"
            )

            if weekly_bars:
                logger.info(f"Received {len(weekly_bars)} weekly bars for ES")
            else:
                logger.warning("No weekly bars received for ES")

            # =========================================================
            # Lookback discovery helper
            # =========================================================
            def probe_lookback(bar_size: str, duration: str, label: str):
                logger.info(f"🔎 Probing {label} lookback "
                            f"(bar={bar_size}, duration={duration})")

                bars = self.ib_broker.get_historical_data(
                    contract=aapl_contract,
                    end_date_time="",
                    duration_str=duration,
                    bar_size_setting=bar_size,
                    what_to_show="TRADES",
                    use_rth=True
                )

                if not bars:
                    logger.warning(f"No data returned for {label}")
                    return

                first_bar = bars[0]["date"]
                last_bar = bars[-1]["date"]

                logger.info(
                    f"✅ {label}: {len(bars)} bars | "
                    f"From {first_bar} → {last_bar}"
                )

            # =========================================================
            # Lookback discovery (AAPL)
            # =========================================================
            logger.info("\n📐 Discovering IB historical lookback limits...")

            probe_lookback("1 day", "20 Y", "Daily bars")
            """probe_lookback("1 hour", "2 Y", "Hourly bars")
            probe_lookback("10 mins", "6 M", "10-minute bars")
            probe_lookback("5 mins", "6 M", "5-minute bars")
            probe_lookback("1 min", "2 M", "1-minute bars")"""

            logger.info("📊 Historical lookback discovery complete")

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
            spy_contract = self.ib_broker.create_stock_contract("SPY", "STK", "SMART")
            spy_contract.primaryExchange = "ARCA"
            
            # Get market depth data
            logger.info("📊 Fetching market depth for SPY...")
            
            depth_data = self.ib_broker.get_market_depth(spy_contract, num_rows=10, timeout=15)
            
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
            aapl_contract = self.ib_broker.create_stock_contract("AAPL", "STK", "SMART")
            
            logger.info("📊 Fetching contract details for AAPL...")
            
            aapl_details = self.ib_broker.get_contract_details(aapl_contract, timeout=15)
            
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
            es_contract = self.ib_broker.create_stock_contract("ES", "FUT", "CME")
            
            logger.info("📊 Fetching contract details for ES futures...")
            
            es_details = self.ib_broker.get_contract_details(es_contract, timeout=15)
            
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
            
            scanner_results = self.ib_broker.get_market_scanner_results(scanner_sub, timeout=30)
            
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
            msft_contract = self.ib_broker.create_stock_contract("MSFT", "STK", "SMART")
            msft_contract.primaryExchange = "NASDAQ"
            
            # Request delayed market data (15-minute delay)
            logger.info("📊 Requesting delayed market data for MSFT...")
            
            success = self.ib_broker.request_delayed_market_data(msft_contract, delay_type=3)
            
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
            tsla_contract = self.ib_broker.create_stock_contract("TSLA", "STK", "SMART")
            tsla_contract.primaryExchange = "NASDAQ"
            
            logger.info("📊 Requesting news data for TSLA...")
            
            news_items = self.ib_broker.get_news_data(tsla_contract, timeout=15)
            
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
        if not self.connected:
            self.ib_broker.connect()
            self.connected = True

        
        
        try:
            # Run all examples

            """self.example_TR_10_YR_future_historical_data()
            time.sleep(2)"""
            self.example_sp500_index_historical_data()
            time.sleep(2)

            self.example_sp500_future_historical_data()
            time.sleep(2)

            self.example_live_market_data()
            time.sleep(2)  # Brief pause between examples
            
            self.example_historical_data()
            time.sleep(2)
            
            self.example_contract_details()
            time.sleep(2)
            
            self.example_delayed_market_data()
            time.sleep(2)
            
            
            logger.info("\\n✅ All examples completed successfully!")
            
        except KeyboardInterrupt:
            logger.info("Examples interrupted by user")
        except Exception as e:
            logger.error(f"Error running examples: {e}")
        finally:
            # Cleanup
            self.ib_broker._disconnect_impl()
            logger.info("\\n🏁 Examples session finished")
    
    def test_access_level_pipeline(self):
        """
        Comprehensive test pipeline to determine what functionality is available
        with the current access level (paper trading vs live, market data subscriptions, etc.).
        
        This pipeline systematically tests each capability and provides a detailed
        report of what is working and what requires additional subscriptions or permissions.
        """
        logger.info("\\n🧪 === Access Level Test Pipeline ===")
        logger.info("=" * 60)
        
        # Connect to IB
        if not self.ib_broker.connect():
            logger.error("❌ Cannot run access level tests - failed to connect to Interactive Brokers")
            return
        
        test_results = {
            'connection': {'status': 'success', 'details': 'Successfully connected to IB'},
            'live_market_data': {'status': 'unknown', 'details': ''},
            'historical_data': {'status': 'unknown', 'details': ''},
            'market_depth': {'status': 'unknown', 'details': ''},
            'contract_details': {'status': 'unknown', 'details': ''},
            'market_scanner': {'status': 'unknown', 'details': ''},
            'delayed_market_data': {'status': 'unknown', 'details': ''},
            'news_data': {'status': 'unknown', 'details': ''},
            'streaming_data': {'status': 'unknown', 'details': ''},
            'futures_data': {'status': 'unknown', 'details': ''},
            'account_info': {'status': 'unknown', 'details': ''}
        }
        
        try:
            # Test 1: Basic Account Information
            logger.info("\\n🔍 Test 1: Account Information Access")
            try:
                if hasattr(self.broker, 'get_broker_specific_info'):
                    account_info = self.ib_broker.get_broker_specific_info()
                    if account_info and not account_info.get('error'):
                        test_results['account_info'] = {
                            'status': 'success', 
                            'details': f"Account accessible - Connection: {account_info.get('connection_state', 'unknown')}"
                        }
                        logger.info(f"  ✅ Account Info: {account_info.get('connection_state', 'Connected')}")
                    else:
                        test_results['account_info'] = {'status': 'limited', 'details': 'Account info access limited'}
                        logger.warning("  ⚠️  Account info access limited")
                else:
                    test_results['account_info'] = {'status': 'unavailable', 'details': 'Account info method not available'}
                    logger.warning("  ❌ Account info method not available")
            except Exception as e:
                test_results['account_info'] = {'status': 'error', 'details': f'Error: {str(e)[:100]}'}
                logger.error(f"  ❌ Account info error: {e}")
            
            # Test 2: Live Market Data Snapshots
            logger.info("\\n🔍 Test 2: Live Market Data Snapshots")
            try:
                spy_contract = self.ib_broker.create_stock_contract("SPY", "STK", "SMART")
                spy_contract.primaryExchange = "ARCA"
                
                snapshot = self.ib_broker.get_market_data_snapshot(spy_contract, timeout=5)
                
                if snapshot and not snapshot.get('error') and snapshot.get('LAST'):
                    test_results['live_market_data'] = {
                        'status': 'success',
                        'details': f"Live data available - Last: {snapshot.get('LAST')}"
                    }
                    logger.info(f"  ✅ Live Market Data: SPY Last = {snapshot.get('LAST')}")
                elif snapshot and snapshot.get('error'):
                    test_results['live_market_data'] = {
                        'status': 'limited',
                        'details': f"Error: {snapshot.get('error', 'Unknown error')}"
                    }
                    logger.warning(f"  ⚠️  Live market data limited: {snapshot.get('error')}")
                else:
                    test_results['live_market_data'] = {'status': 'unavailable', 'details': 'No live market data received'}
                    logger.warning("  ❌ No live market data received - may need subscription")
            except Exception as e:
                test_results['live_market_data'] = {'status': 'error', 'details': f'Error: {str(e)[:100]}'}
                logger.error(f"  ❌ Live market data error: {e}")
            
            # Test 3: Historical Data
            logger.info("\\n🔍 Test 3: Historical Data Access")
            try:
                aapl_contract = self.ib_broker.create_stock_contract("AAPL", "STK", "SMART")
                aapl_contract.primaryExchange = "NASDAQ"
                
                historical = self.ib_broker.get_historical_data(
                    contract=aapl_contract,
                    duration_str="5 D",
                    bar_size_setting="1 day",
                    what_to_show="TRADES",
                    timeout=10
                )
                
                if historical and len(historical) > 0:
                    test_results['historical_data'] = {
                        'status': 'success',
                        'details': f"Historical data available - {len(historical)} bars received"
                    }
                    logger.info(f"  ✅ Historical Data: {len(historical)} AAPL daily bars")
                else:
                    test_results['historical_data'] = {'status': 'limited', 'details': 'No historical data received'}
                    logger.warning("  ⚠️  No historical data received")
            except Exception as e:
                test_results['historical_data'] = {'status': 'error', 'details': f'Error: {str(e)[:100]}'}
                logger.error(f"  ❌ Historical data error: {e}")
            
            # Test 4: Market Depth (Level 2)
            logger.info("\\n🔍 Test 4: Market Depth (Level 2) Access")
            try:
                spy_contract = self.ib_broker.create_stock_contract("SPY", "STK", "SMART")
                spy_contract.primaryExchange = "ARCA"
                
                depth = self.ib_broker.get_market_depth(spy_contract, num_rows=5, timeout=10)
                
                if depth and not depth.get('error') and (depth.get('bids') or depth.get('asks')):
                    bid_count = len(depth.get('bids', []))
                    ask_count = len(depth.get('asks', []))
                    test_results['market_depth'] = {
                        'status': 'success',
                        'details': f"Level 2 data available - {bid_count} bids, {ask_count} asks"
                    }
                    logger.info(f"  ✅ Market Depth: {bid_count} bids, {ask_count} asks")
                else:
                    error_msg = depth.get('error', 'No depth data received') if depth else 'No response'
                    test_results['market_depth'] = {'status': 'limited', 'details': f'Limited: {error_msg}'}
                    logger.warning(f"  ⚠️  Market depth limited: {error_msg}")
            except Exception as e:
                test_results['market_depth'] = {'status': 'error', 'details': f'Error: {str(e)[:100]}'}
                logger.error(f"  ❌ Market depth error: {e}")
            
            # Test 5: Contract Details
            logger.info("\\n🔍 Test 5: Contract Details Access")
            try:
                spy_contract = self.ib_broker.create_stock_contract("SPY", "STK", "SMART")
                details = self.ib_broker.get_contract_details(spy_contract, timeout=10)
                
                if details and len(details) > 0:
                    test_results['contract_details'] = {
                        'status': 'success',
                        'details': f"Contract details available - {len(details)} matches found"
                    }
                    logger.info(f"  ✅ Contract Details: {len(details)} SPY contract matches")
                else:
                    test_results['contract_details'] = {'status': 'limited', 'details': 'No contract details received'}
                    logger.warning("  ⚠️  No contract details received")
            except Exception as e:
                test_results['contract_details'] = {'status': 'error', 'details': f'Error: {str(e)[:100]}'}
                logger.error(f"  ❌ Contract details error: {e}")
            
            # Test 6: Market Scanner
            logger.info("\\n🔍 Test 6: Market Scanner Access")
            try:
                scanner_sub = ScannerSubscription()
                scanner_sub.instrument = "STK"
                scanner_sub.locationCode = "STK.US.MAJOR"
                scanner_sub.scanCode = "TOP_VOLUME"
                scanner_sub.numberOfRows = 10
                
                scanner_results = self.ib_broker.get_market_scanner_results(scanner_sub, timeout=15)
                
                if scanner_results and len(scanner_results) > 0:
                    test_results['market_scanner'] = {
                        'status': 'success',
                        'details': f"Market scanner available - {len(scanner_results)} results"
                    }
                    logger.info(f"  ✅ Market Scanner: {len(scanner_results)} results")
                else:
                    test_results['market_scanner'] = {'status': 'limited', 'details': 'No scanner results received'}
                    logger.warning("  ⚠️  No scanner results received")
            except Exception as e:
                test_results['market_scanner'] = {'status': 'error', 'details': f'Error: {str(e)[:100]}'}
                logger.error(f"  ❌ Market scanner error: {e}")
            
            # Test 7: Futures Data
            logger.info("\\n🔍 Test 7: Futures Data Access")
            try:
                es_contract = self.ib_broker.create_stock_contract("ES", "FUT", "CME")
                
                futures_snapshot = self.ib_broker.get_market_data_snapshot(es_contract, timeout=5)
                
                if futures_snapshot and not futures_snapshot.get('error') and futures_snapshot.get('LAST'):
                    test_results['futures_data'] = {
                        'status': 'success',
                        'details': f"Futures data available - ES Last: {futures_snapshot.get('LAST')}"
                    }
                    logger.info(f"  ✅ Futures Data: ES Last = {futures_snapshot.get('LAST')}")
                else:
                    error_msg = futures_snapshot.get('error', 'No futures data') if futures_snapshot else 'No response'
                    test_results['futures_data'] = {'status': 'limited', 'details': f'Limited: {error_msg}'}
                    logger.warning(f"  ⚠️  Futures data limited: {error_msg}")
            except Exception as e:
                test_results['futures_data'] = {'status': 'error', 'details': f'Error: {str(e)[:100]}'}
                logger.error(f"  ❌ Futures data error: {e}")
            
            # Test 8: Streaming Data Subscriptions
            logger.info("\\n🔍 Test 8: Streaming Data Subscriptions")
            try:
                spy_contract = self.ib_broker.create_stock_contract("SPY", "STK", "SMART")
                spy_contract.primaryExchange = "ARCA"
                
                subscription_id = self.ib_broker.subscribe_market_data(spy_contract, "")
                
                if subscription_id and subscription_id > 0:
                    # Brief wait to see if data flows
                    time.sleep(3)
                    
                    # Check for streaming data
                    has_streaming_data = False
                    if hasattr(self.broker, 'ib_connection') and hasattr(self.ib_broker.ib_connection, 'market_data'):
                        if subscription_id in self.ib_broker.ib_connection.market_data:
                            data = self.ib_broker.ib_connection.market_data[subscription_id]
                            if data and data.get('prices'):
                                has_streaming_data = True
                    
                    # Unsubscribe
                    self.ib_broker.unsubscribe_market_data(subscription_id)
                    
                    if has_streaming_data:
                        test_results['streaming_data'] = {
                            'status': 'success',
                            'details': 'Streaming data subscriptions working'
                        }
                        logger.info("  ✅ Streaming Data: Subscriptions working")
                    else:
                        test_results['streaming_data'] = {
                            'status': 'partial',
                            'details': 'Subscription created but no data received'
                        }
                        logger.warning("  ⚠️  Streaming: Subscription created but no data received")
                else:
                    test_results['streaming_data'] = {'status': 'limited', 'details': 'Failed to create subscription'}
                    logger.warning("  ❌ Failed to create streaming data subscription")
            except Exception as e:
                test_results['streaming_data'] = {'status': 'error', 'details': f'Error: {str(e)[:100]}'}
                logger.error(f"  ❌ Streaming data error: {e}")
            
            # Test 9: News Data
            logger.info("\\n🔍 Test 9: News Data Access")
            try:
                aapl_contract = self.ib_broker.create_stock_contract("AAPL", "STK", "SMART")
                aapl_contract.primaryExchange = "NASDAQ"
                
                news_data = self.ib_broker.get_news_data(aapl_contract, timeout=10)
                
                if news_data and len(news_data) > 0:
                    test_results['news_data'] = {
                        'status': 'success',
                        'details': f"News data available - {len(news_data)} items received"
                    }
                    logger.info(f"  ✅ News Data: {len(news_data)} news items for AAPL")
                else:
                    test_results['news_data'] = {'status': 'limited', 'details': 'No news data received'}
                    logger.warning("  ⚠️  No news data received - may require subscription")
            except Exception as e:
                test_results['news_data'] = {'status': 'error', 'details': f'Error: {str(e)[:100]}'}
                logger.error(f"  ❌ News data error: {e}")
            
            # Generate comprehensive report
            self._generate_access_level_report(test_results)
            
        except KeyboardInterrupt:
            logger.info("Access level tests interrupted by user")
        except Exception as e:
            logger.error(f"Error in access level pipeline: {e}")
        finally:
            self.disconnect_from_ib()
            logger.info("\\n🏁 Access Level Test Pipeline Complete")
    
    def _generate_access_level_report(self, test_results: Dict[str, Dict[str, str]]):
        """
        Generate a comprehensive report of access level test results.
        
        Args:
            test_results: Dictionary containing test results for each capability
        """
        logger.info("\\n" + "=" * 60)
        logger.info("📊 === COMPREHENSIVE ACCESS LEVEL REPORT ===")
        logger.info("=" * 60)
        
        # Count results by status
        status_counts = {'success': 0, 'limited': 0, 'partial': 0, 'unavailable': 0, 'error': 0, 'unknown': 0}
        
        logger.info("\\n🎯 CAPABILITY STATUS SUMMARY:")
        logger.info("-" * 40)
        
        for capability, result in test_results.items():
            status = result['status']
            details = result['details']
            status_counts[status] += 1
            
            # Choose emoji based on status
            emoji_map = {
                'success': '✅',
                'limited': '⚠️',
                'partial': '🟡',
                'unavailable': '❌',
                'error': '🔥',
                'unknown': '❓'
            }
            
            emoji = emoji_map.get(status, '❓')
            capability_name = capability.replace('_', ' ').title()
            
            logger.info(f"{emoji} {capability_name:<20} | {status.upper():<12} | {details}")
        
        # Overall assessment
        logger.info("\\n" + "-" * 60)
        logger.info("📈 OVERALL ASSESSMENT:")
        logger.info("-" * 60)
        
        total_tests = len(test_results)
        success_rate = (status_counts['success'] / total_tests) * 100
        
        logger.info(f"Total Tests Performed: {total_tests}")
        logger.info(f"✅ Fully Working:      {status_counts['success']} ({status_counts['success']/total_tests*100:.1f}%)")
        logger.info(f"⚠️  Limited Access:     {status_counts['limited']} ({status_counts['limited']/total_tests*100:.1f}%)")
        logger.info(f"🟡 Partial Working:    {status_counts['partial']} ({status_counts['partial']/total_tests*100:.1f}%)")
        logger.info(f"❌ Not Available:      {status_counts['unavailable']} ({status_counts['unavailable']/total_tests*100:.1f}%)")
        logger.info(f"🔥 Errors:            {status_counts['error']} ({status_counts['error']/total_tests*100:.1f}%)")
        
        # Recommendations
        logger.info("\\n" + "-" * 60)
        logger.info("💡 RECOMMENDATIONS:")
        logger.info("-" * 60)
        
        if status_counts['success'] >= 6:
            logger.info("🎉 EXCELLENT: Your access level supports most IB API capabilities!")
            logger.info("   • Consider upgrading any limited features for full functionality")
        elif status_counts['success'] >= 4:
            logger.info("👍 GOOD: Your access level supports core IB API capabilities")
            logger.info("   • Some advanced features may require additional subscriptions")
        elif status_counts['success'] >= 2:
            logger.info("⚠️  BASIC: Limited access detected")
            logger.info("   • Consider checking your IB account permissions and subscriptions")
        else:
            logger.info("🚨 MINIMAL: Very limited access detected")
            logger.info("   • Check IB Gateway/TWS connection and account status")
            logger.info("   • Verify market data subscriptions and permissions")
        
        # Specific recommendations based on failures
        if test_results['live_market_data']['status'] in ['limited', 'unavailable']:
            logger.info("   📡 Consider upgrading to live market data subscriptions")
        
        if test_results['market_depth']['status'] in ['limited', 'unavailable']:
            logger.info("   📊 Level 2 market depth may require additional subscription")
        
        if test_results['news_data']['status'] in ['limited', 'unavailable']:
            logger.info("   📰 News data requires specific market data subscriptions")
        
        if test_results['futures_data']['status'] in ['limited', 'unavailable']:
            logger.info("   📈 Futures data may require futures trading permissions")
        
        logger.info("\\n" + "=" * 60)
        logger.info("✨ Access Level Analysis Complete!")
        logger.info("=" * 60)










