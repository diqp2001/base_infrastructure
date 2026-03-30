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
    python comprehensive_market_data_examples.py ticks    # Run comprehensive tick access test only
    python comprehensive_market_data_examples.py conid    # Test get_by_conid function with example CONIDs
    python comprehensive_market_data_examples.py esz6     # Test ESZ6 options & futures prices
    python comprehensive_market_data_examples.py volsurf  # Test volatility surface for AAPL stock options

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
            contract = Contract()
            contract.symbol = "ES"
            contract.secType = "FUT"
            contract.exchange = "GLOBEX"
            contract.currency = "USD"
            contract.lastTradeDateOrContractMonth = "20260326"
            contract.multiplier = "50"
            contract.tradingClass = "ES"
            base = Contract()
            base.symbol = "ES"
            base.secType = "FUT"
            base.exchange = "GLOBEX"
            base.currency = "USD"

            contract_details = self.ib_broker.ib_connection.reqContractDetailsSync(base)  # custom sync wrapper
            if not contract_details:
                raise ValueError("No contract details found ")
            es_contract = contract_details[0].contract 
            #self.ib_broker.ib_connection.request_contract_details(1, base)
            es_contract = contract

            # es_contract = self.ib_broker.create_stock_contract("ES", "FUT", "CME")
            # es_contract.lastTradeDateOrContractMonth = "202403"

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
            es_contract = self.ib_broker.ib_connection.contract_details.contract 
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
            # self.example_sp500_index_historical_data()
            # time.sleep(2)

            # self.example_sp500_future_historical_data()
            # time.sleep(2)

            # self.example_live_market_data()
            # time.sleep(2)  # Brief pause between examples
            
            self.example_historical_data()
            time.sleep(2)
            
            # self.example_contract_details()
            # time.sleep(2)
            
            # self.example_delayed_market_data()
            # time.sleep(2)
            
            
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

    def test_comprehensive_market_access(self):
        """
        Comprehensive test function that tests ALL market access types and returns a detailed summary.
        
        This function tests:
        - Asset Classes: Stocks, Commodities, Bonds, Futures
        - Data Types: Live market data, Historical delayed data, Streaming data
        - Market Access: Real-time quotes, Level 2 data, Contract details
        
        Returns:
            Dict: Comprehensive summary of all market access test results
        """
        logger.info("\n🚀 === COMPREHENSIVE MARKET ACCESS TEST ===")
        logger.info("=" * 70)
        
        # Initialize results structure
        market_access_results = {
            'connection_status': {'tested': False, 'status': 'unknown', 'details': ''},
            'asset_classes': {
                'stocks': {'tested': False, 'status': 'unknown', 'details': '', 'test_results': {}},
                'commodities': {'tested': False, 'status': 'unknown', 'details': '', 'test_results': {}},
                'bonds': {'tested': False, 'status': 'unknown', 'details': '', 'test_results': {}},
                'futures': {'tested': False, 'status': 'unknown', 'details': '', 'test_results': {}}
            },
            'data_types': {
                'live_market_data': {'tested': False, 'status': 'unknown', 'details': '', 'symbols_tested': []},
                'historical_delayed': {'tested': False, 'status': 'unknown', 'details': '', 'symbols_tested': []},
                'streaming_data': {'tested': False, 'status': 'unknown', 'details': '', 'symbols_tested': []},
                'level2_depth': {'tested': False, 'status': 'unknown', 'details': '', 'symbols_tested': []},
                'contract_details': {'tested': False, 'status': 'unknown', 'details': '', 'symbols_tested': []}
            },
            'test_summary': {
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'partial': 0,
                'start_time': datetime.now(),
                'end_time': None,
                'duration': None
            },
            'recommendations': []
        }
        
        # Connect to IB
        try:
            if not self.connected:
                if not self.ib_broker.connect():
                    market_access_results['connection_status'] = {
                        'tested': True, 
                        'status': 'failed', 
                        'details': 'Cannot connect to Interactive Brokers Gateway/TWS'
                    }
                    return self._generate_market_access_summary(market_access_results)
                
            market_access_results['connection_status'] = {
                'tested': True, 
                'status': 'success', 
                'details': 'Successfully connected to IB Gateway/TWS'
            }
            logger.info("✅ Connected to Interactive Brokers")
            
        except Exception as e:
            market_access_results['connection_status'] = {
                'tested': True, 
                'status': 'error', 
                'details': f'Connection error: {str(e)[:100]}'
            }
            return self._generate_market_access_summary(market_access_results)
        
        # Test 1: STOCKS Asset Class
        logger.info("\n📈 Testing STOCKS Asset Class...")
        stock_results = self._test_stocks_market_access()
        market_access_results['asset_classes']['stocks'] = stock_results
        
        # Test 2: COMMODITIES Asset Class  
        logger.info("\n🥇 Testing COMMODITIES Asset Class...")
        commodity_results = self._test_commodities_market_access()
        market_access_results['asset_classes']['commodities'] = commodity_results
        
        # Test 3: BONDS Asset Class
        logger.info("\n🏛️ Testing BONDS Asset Class...")
        bond_results = self._test_bonds_market_access()
        market_access_results['asset_classes']['bonds'] = bond_results
        
        # Test 4: FUTURES Asset Class
        logger.info("\n📊 Testing FUTURES Asset Class...")
        futures_results = self._test_futures_market_access()
        market_access_results['asset_classes']['futures'] = futures_results
        
        # Test 5: Data Types Comprehensive Testing
        logger.info("\n🔍 Testing DATA TYPES across all assets...")
        self._test_data_types_comprehensive(market_access_results)
        
        # Finalize summary
        market_access_results['test_summary']['end_time'] = datetime.now()
        market_access_results['test_summary']['duration'] = (
            market_access_results['test_summary']['end_time'] - 
            market_access_results['test_summary']['start_time']
        ).total_seconds()
        
        # Generate and return comprehensive summary
        return self._generate_market_access_summary(market_access_results)

    def _test_stocks_market_access(self):
        """Test stocks market access across different exchanges and data types."""
        result = {'tested': True, 'status': 'unknown', 'details': '', 'test_results': {}}
        
        # Test stocks: US equities, ETFs, international
        test_symbols = [
            {'symbol': 'AAPL', 'exchange': 'SMART', 'primaryExchange': 'NASDAQ', 'type': 'US Large Cap'},
            {'symbol': 'SPY', 'exchange': 'SMART', 'primaryExchange': 'ARCA', 'type': 'ETF'},
            {'symbol': 'TSLA', 'exchange': 'SMART', 'primaryExchange': 'NASDAQ', 'type': 'US Growth'},
        ]
        
        successful_tests = 0
        total_tests = len(test_symbols)
        
        for stock_info in test_symbols:
            try:
                logger.info(f"  Testing {stock_info['symbol']} ({stock_info['type']})...")
                
                # Create contract
                contract = self.ib_broker.create_stock_contract(
                    stock_info['symbol'], 'STK', stock_info['exchange']
                )
                if stock_info.get('primaryExchange'):
                    contract.primaryExchange = stock_info['primaryExchange']
                
                test_result = {
                    'live_data': False,
                    'historical_data': False,
                    'contract_details': False,
                    'error_messages': []
                }
                
                # Test live market data
                try:
                    snapshot = self.ib_broker.get_market_data_snapshot(contract, timeout=5)
                    if snapshot and not snapshot.get('error') and snapshot.get('LAST'):
                        test_result['live_data'] = True
                        logger.info(f"    ✅ Live data: Last = {snapshot.get('LAST')}")
                    else:
                        error_msg = snapshot.get('error', 'No live data') if snapshot else 'No response'
                        test_result['error_messages'].append(f"Live data: {error_msg}")
                        logger.info(f"    ⚠️  Live data limited: {error_msg}")
                except Exception as e:
                    test_result['error_messages'].append(f"Live data error: {str(e)[:50]}")
                
                # Test historical data
                try:
                    historical = self.ib_broker.get_historical_data(
                        contract=contract,
                        duration_str="5 D",
                        bar_size_setting="1 day",
                        what_to_show="TRADES",
                        timeout=8
                    )
                    if historical and len(historical) > 0:
                        test_result['historical_data'] = True
                        logger.info(f"    ✅ Historical: {len(historical)} bars")
                    else:
                        test_result['error_messages'].append("Historical: No data received")
                        logger.info("    ⚠️  No historical data")
                except Exception as e:
                    test_result['error_messages'].append(f"Historical error: {str(e)[:50]}")
                
                # Test contract details
                try:
                    details = self.ib_broker.get_contract_details(contract, timeout=5)
                    if details and len(details) > 0:
                        test_result['contract_details'] = True
                        logger.info(f"    ✅ Contract details: {len(details)} matches")
                    else:
                        test_result['error_messages'].append("Contract details: No details received")
                except Exception as e:
                    test_result['error_messages'].append(f"Contract details error: {str(e)[:50]}")
                
                result['test_results'][stock_info['symbol']] = test_result
                
                # Count as successful if at least 2 out of 3 work
                working_count = sum([test_result['live_data'], test_result['historical_data'], test_result['contract_details']])
                if working_count >= 2:
                    successful_tests += 1
                    
            except Exception as e:
                logger.error(f"    ❌ Error testing {stock_info['symbol']}: {e}")
                result['test_results'][stock_info['symbol']] = {
                    'live_data': False, 'historical_data': False, 'contract_details': False,
                    'error_messages': [f"General error: {str(e)[:50]}"]
                }
        
        # Determine overall status
        if successful_tests == total_tests:
            result['status'] = 'success'
            result['details'] = f"All {total_tests} stock symbols tested successfully"
        elif successful_tests > 0:
            result['status'] = 'partial'
            result['details'] = f"{successful_tests}/{total_tests} stock symbols working"
        else:
            result['status'] = 'failed'
            result['details'] = f"No stock symbols working ({total_tests} tested)"
            
        return result

    def _test_commodities_market_access(self):
        """Test commodities market access (futures and spot)."""
        result = {'tested': True, 'status': 'unknown', 'details': '', 'test_results': {}}
        
        # Test commodity futures (most accessible way to trade commodities via IB)
        commodity_contracts = [
            {'symbol': 'CL', 'exchange': 'NYMEX', 'type': 'Crude Oil Futures'},
            {'symbol': 'GC', 'exchange': 'COMEX', 'type': 'Gold Futures'},
            {'symbol': 'SI', 'exchange': 'COMEX', 'type': 'Silver Futures'},
        ]
        
        successful_tests = 0
        total_tests = len(commodity_contracts)
        
        for commodity_info in commodity_contracts:
            try:
                logger.info(f"  Testing {commodity_info['symbol']} ({commodity_info['type']})...")
                
                # Create futures contract
                contract = self.ib_broker.create_stock_contract(
                    commodity_info['symbol'], 'FUT', commodity_info['exchange']
                )
                contract.currency = 'USD'
                
                test_result = {
                    'live_data': False,
                    'historical_data': False,
                    'contract_details': False,
                    'error_messages': []
                }
                
                # Test market data snapshot
                try:
                    snapshot = self.ib_broker.get_market_data_snapshot(contract, timeout=5)
                    if snapshot and not snapshot.get('error') and snapshot.get('LAST'):
                        test_result['live_data'] = True
                        logger.info(f"    ✅ Live data: Last = {snapshot.get('LAST')}")
                    else:
                        error_msg = snapshot.get('error', 'No commodity data') if snapshot else 'No response'
                        test_result['error_messages'].append(f"Live data: {error_msg}")
                        logger.info(f"    ⚠️  Commodity data limited: {error_msg}")
                except Exception as e:
                    test_result['error_messages'].append(f"Live data error: {str(e)[:50]}")
                
                # Test historical data
                try:
                    historical = self.ib_broker.get_historical_data(
                        contract=contract,
                        duration_str="1 M",
                        bar_size_setting="1 day",
                        what_to_show="TRADES",
                        timeout=8
                    )
                    if historical and len(historical) > 0:
                        test_result['historical_data'] = True
                        logger.info(f"    ✅ Historical: {len(historical)} bars")
                    else:
                        test_result['error_messages'].append("Historical: No commodity historical data")
                except Exception as e:
                    test_result['error_messages'].append(f"Historical error: {str(e)[:50]}")
                
                # Test contract details
                try:
                    details = self.ib_broker.get_contract_details(contract, timeout=8)
                    if details and len(details) > 0:
                        test_result['contract_details'] = True
                        logger.info(f"    ✅ Contract details: {len(details)} commodity contracts")
                    else:
                        test_result['error_messages'].append("Contract details: No commodity contracts found")
                except Exception as e:
                    test_result['error_messages'].append(f"Contract details error: {str(e)[:50]}")
                
                result['test_results'][commodity_info['symbol']] = test_result
                
                # Count as successful if at least 1 out of 3 work (commodities can be more restrictive)
                working_count = sum([test_result['live_data'], test_result['historical_data'], test_result['contract_details']])
                if working_count >= 1:
                    successful_tests += 1
                    
            except Exception as e:
                logger.error(f"    ❌ Error testing {commodity_info['symbol']}: {e}")
                result['test_results'][commodity_info['symbol']] = {
                    'live_data': False, 'historical_data': False, 'contract_details': False,
                    'error_messages': [f"General error: {str(e)[:50]}"]
                }
        
        # Determine overall status
        if successful_tests == total_tests:
            result['status'] = 'success'
            result['details'] = f"All {total_tests} commodity symbols tested successfully"
        elif successful_tests > 0:
            result['status'] = 'partial'
            result['details'] = f"{successful_tests}/{total_tests} commodity symbols working"
        else:
            result['status'] = 'failed'
            result['details'] = f"No commodity symbols working ({total_tests} tested)"
            
        return result

    def _test_bonds_market_access(self):
        """Test bonds market access (Treasury futures and corporate bonds)."""
        result = {'tested': True, 'status': 'unknown', 'details': '', 'test_results': {}}
        
        # Test Treasury futures (most accessible bond instruments via IB)
        bond_contracts = [
            {'symbol': 'ZN', 'exchange': 'CBOT', 'type': '10-Year Treasury Note Futures'},
            {'symbol': 'ZB', 'exchange': 'CBOT', 'type': '30-Year Treasury Bond Futures'},
            {'symbol': 'ZF', 'exchange': 'CBOT', 'type': '5-Year Treasury Note Futures'},
        ]
        
        successful_tests = 0
        total_tests = len(bond_contracts)
        
        for bond_info in bond_contracts:
            try:
                logger.info(f"  Testing {bond_info['symbol']} ({bond_info['type']})...")
                
                # Create Treasury futures contract
                contract = self.ib_broker.create_stock_contract(
                    bond_info['symbol'], 'FUT', bond_info['exchange']
                )
                contract.currency = 'USD'
                
                test_result = {
                    'live_data': False,
                    'historical_data': False,
                    'contract_details': False,
                    'error_messages': []
                }
                
                # Test market data snapshot
                try:
                    snapshot = self.ib_broker.get_market_data_snapshot(contract, timeout=5)
                    if snapshot and not snapshot.get('error') and snapshot.get('LAST'):
                        test_result['live_data'] = True
                        logger.info(f"    ✅ Live data: Last = {snapshot.get('LAST')}")
                    else:
                        error_msg = snapshot.get('error', 'No bond data') if snapshot else 'No response'
                        test_result['error_messages'].append(f"Live data: {error_msg}")
                        logger.info(f"    ⚠️  Bond data limited: {error_msg}")
                except Exception as e:
                    test_result['error_messages'].append(f"Live data error: {str(e)[:50]}")
                
                # Test historical data
                try:
                    historical = self.ib_broker.get_historical_data(
                        contract=contract,
                        duration_str="1 M",
                        bar_size_setting="1 day",
                        what_to_show="TRADES",
                        timeout=8
                    )
                    if historical and len(historical) > 0:
                        test_result['historical_data'] = True
                        logger.info(f"    ✅ Historical: {len(historical)} bars")
                    else:
                        test_result['error_messages'].append("Historical: No bond historical data")
                except Exception as e:
                    test_result['error_messages'].append(f"Historical error: {str(e)[:50]}")
                
                # Test contract details
                try:
                    details = self.ib_broker.get_contract_details(contract, timeout=8)
                    if details and len(details) > 0:
                        test_result['contract_details'] = True
                        logger.info(f"    ✅ Contract details: {len(details)} bond contracts")
                    else:
                        test_result['error_messages'].append("Contract details: No bond contracts found")
                except Exception as e:
                    test_result['error_messages'].append(f"Contract details error: {str(e)[:50]}")
                
                result['test_results'][bond_info['symbol']] = test_result
                
                # Count as successful if at least 1 out of 3 work
                working_count = sum([test_result['live_data'], test_result['historical_data'], test_result['contract_details']])
                if working_count >= 1:
                    successful_tests += 1
                    
            except Exception as e:
                logger.error(f"    ❌ Error testing {bond_info['symbol']}: {e}")
                result['test_results'][bond_info['symbol']] = {
                    'live_data': False, 'historical_data': False, 'contract_details': False,
                    'error_messages': [f"General error: {str(e)[:50]}"]
                }
        
        # Determine overall status
        if successful_tests == total_tests:
            result['status'] = 'success' 
            result['details'] = f"All {total_tests} bond symbols tested successfully"
        elif successful_tests > 0:
            result['status'] = 'partial'
            result['details'] = f"{successful_tests}/{total_tests} bond symbols working"
        else:
            result['status'] = 'failed'
            result['details'] = f"No bond symbols working ({total_tests} tested)"
            
        return result

    def _test_futures_market_access(self):
        """Test futures market access across different categories."""
        result = {'tested': True, 'status': 'unknown', 'details': '', 'test_results': {}}
        
        # Test various futures categories
        futures_contracts = [
            {'symbol': 'ES', 'exchange': 'CME', 'type': 'S&P 500 E-mini Futures'},
            {'symbol': 'NQ', 'exchange': 'CME', 'type': 'Nasdaq 100 E-mini Futures'},  
            {'symbol': 'YM', 'exchange': 'CBOT', 'type': 'Dow Jones E-mini Futures'},
        ]
        
        successful_tests = 0
        total_tests = len(futures_contracts)
        
        for futures_info in futures_contracts:
            try:
                logger.info(f"  Testing {futures_info['symbol']} ({futures_info['type']})...")
                
                # Create futures contract
                contract = self.ib_broker.create_stock_contract(
                    futures_info['symbol'], 'FUT', futures_info['exchange']
                )
                contract.currency = 'USD'
                
                test_result = {
                    'live_data': False,
                    'historical_data': False,
                    'contract_details': False,
                    'error_messages': []
                }
                
                # Test market data snapshot
                try:
                    snapshot = self.ib_broker.get_market_data_snapshot(contract, timeout=5)
                    if snapshot and not snapshot.get('error') and snapshot.get('LAST'):
                        test_result['live_data'] = True
                        logger.info(f"    ✅ Live data: Last = {snapshot.get('LAST')}")
                    else:
                        error_msg = snapshot.get('error', 'No futures data') if snapshot else 'No response'
                        test_result['error_messages'].append(f"Live data: {error_msg}")
                        logger.info(f"    ⚠️  Futures data limited: {error_msg}")
                except Exception as e:
                    test_result['error_messages'].append(f"Live data error: {str(e)[:50]}")
                
                # Test historical data
                try:
                    historical = self.ib_broker.get_historical_data(
                        contract=contract,
                        duration_str="1 M",
                        bar_size_setting="1 day",
                        what_to_show="TRADES",
                        use_rth=False,  # Futures trade nearly 24h
                        timeout=8
                    )
                    if historical and len(historical) > 0:
                        test_result['historical_data'] = True
                        logger.info(f"    ✅ Historical: {len(historical)} bars")
                    else:
                        test_result['error_messages'].append("Historical: No futures historical data")
                except Exception as e:
                    test_result['error_messages'].append(f"Historical error: {str(e)[:50]}")
                
                # Test contract details
                try:
                    details = self.ib_broker.get_contract_details(contract, timeout=8)
                    if details and len(details) > 0:
                        test_result['contract_details'] = True
                        logger.info(f"    ✅ Contract details: {len(details)} futures contracts")
                    else:
                        test_result['error_messages'].append("Contract details: No futures contracts found")
                except Exception as e:
                    test_result['error_messages'].append(f"Contract details error: {str(e)[:50]}")
                
                result['test_results'][futures_info['symbol']] = test_result
                
                # Count as successful if at least 2 out of 3 work
                working_count = sum([test_result['live_data'], test_result['historical_data'], test_result['contract_details']])
                if working_count >= 2:
                    successful_tests += 1
                    
            except Exception as e:
                logger.error(f"    ❌ Error testing {futures_info['symbol']}: {e}")
                result['test_results'][futures_info['symbol']] = {
                    'live_data': False, 'historical_data': False, 'contract_details': False,
                    'error_messages': [f"General error: {str(e)[:50]}"]
                }
        
        # Determine overall status
        if successful_tests == total_tests:
            result['status'] = 'success'
            result['details'] = f"All {total_tests} futures symbols tested successfully"
        elif successful_tests > 0:
            result['status'] = 'partial'
            result['details'] = f"{successful_tests}/{total_tests} futures symbols working"
        else:
            result['status'] = 'failed'
            result['details'] = f"No futures symbols working ({total_tests} tested)"
            
        return result

    def _test_data_types_comprehensive(self, market_access_results):
        """Test different data types comprehensively across asset classes."""
        
        # Test Level 2 Market Depth
        logger.info("  🔍 Testing Level 2 Market Depth...")
        try:
            spy_contract = self.ib_broker.create_stock_contract("SPY", "STK", "SMART")
            spy_contract.primaryExchange = "ARCA"
            
            depth = self.ib_broker.get_market_depth(spy_contract, num_rows=5, timeout=8)
            if depth and not depth.get('error') and (depth.get('bids') or depth.get('asks')):
                bid_count = len(depth.get('bids', []))
                ask_count = len(depth.get('asks', []))
                market_access_results['data_types']['level2_depth'] = {
                    'tested': True, 'status': 'success',
                    'details': f"Level 2 data available - {bid_count} bids, {ask_count} asks",
                    'symbols_tested': ['SPY']
                }
                logger.info(f"    ✅ Level 2: {bid_count} bids, {ask_count} asks")
            else:
                error_msg = depth.get('error', 'No depth data') if depth else 'No response'
                market_access_results['data_types']['level2_depth'] = {
                    'tested': True, 'status': 'limited',
                    'details': f"Limited: {error_msg}",
                    'symbols_tested': ['SPY']
                }
                logger.info(f"    ⚠️  Level 2 limited: {error_msg}")
        except Exception as e:
            market_access_results['data_types']['level2_depth'] = {
                'tested': True, 'status': 'error',
                'details': f"Error: {str(e)[:100]}",
                'symbols_tested': ['SPY']
            }
        
        # Test Streaming Data Subscriptions
        logger.info("  📡 Testing Streaming Data Subscriptions...")
        try:
            spy_contract = self.ib_broker.create_stock_contract("SPY", "STK", "SMART") 
            spy_contract.primaryExchange = "ARCA"
            
            subscription_id = self.ib_broker.subscribe_market_data(spy_contract, "")
            if subscription_id and subscription_id > 0:
                time.sleep(3)  # Brief wait for data
                
                # Check for streaming data
                has_streaming_data = False
                if hasattr(self.ib_broker, 'ib_connection') and hasattr(self.ib_broker.ib_connection, 'market_data'):
                    if subscription_id in self.ib_broker.ib_connection.market_data:
                        data = self.ib_broker.ib_connection.market_data[subscription_id]
                        if data and data.get('prices'):
                            has_streaming_data = True
                
                self.ib_broker.unsubscribe_market_data(subscription_id)
                
                if has_streaming_data:
                    market_access_results['data_types']['streaming_data'] = {
                        'tested': True, 'status': 'success',
                        'details': 'Streaming data subscriptions working',
                        'symbols_tested': ['SPY']
                    }
                    logger.info("    ✅ Streaming: Working")
                else:
                    market_access_results['data_types']['streaming_data'] = {
                        'tested': True, 'status': 'partial',
                        'details': 'Subscription created but no data received',
                        'symbols_tested': ['SPY']
                    }
                    logger.info("    ⚠️  Streaming: Subscription created but no data")
            else:
                market_access_results['data_types']['streaming_data'] = {
                    'tested': True, 'status': 'failed',
                    'details': 'Failed to create subscription',
                    'symbols_tested': ['SPY']
                }
        except Exception as e:
            market_access_results['data_types']['streaming_data'] = {
                'tested': True, 'status': 'error',
                'details': f"Error: {str(e)[:100]}",
                'symbols_tested': ['SPY']
            }

    def _generate_market_access_summary(self, market_access_results):
        """Generate comprehensive summary of market access test results."""
        
        logger.info("\n" + "=" * 70)
        logger.info("📊 === COMPREHENSIVE MARKET ACCESS SUMMARY ===")
        logger.info("=" * 70)
        
        summary = market_access_results['test_summary']
        summary['end_time'] = datetime.now()
        
        # Connection Status
        logger.info(f"\n🔌 CONNECTION STATUS:")
        conn = market_access_results['connection_status']
        status_icon = "✅" if conn['status'] == 'success' else "❌"
        logger.info(f"  {status_icon} {conn['details']}")
        
        # Asset Classes Summary
        logger.info(f"\n📈 ASSET CLASSES ACCESS:")
        logger.info("-" * 40)
        
        asset_summary = {}
        for asset_type, result in market_access_results['asset_classes'].items():
            if result['tested']:
                icon = {"success": "✅", "partial": "🟡", "failed": "❌", "error": "🔥"}.get(result['status'], "❓")
                logger.info(f"  {icon} {asset_type.upper():<12} | {result['status'].upper():<8} | {result['details']}")
                asset_summary[asset_type] = result['status']
        
        # Data Types Summary
        logger.info(f"\n🔍 DATA TYPES ACCESS:")
        logger.info("-" * 40)
        
        data_summary = {}
        for data_type, result in market_access_results['data_types'].items():
            if result.get('tested', False):
                icon = {"success": "✅", "partial": "🟡", "failed": "❌", "limited": "⚠️", "error": "🔥"}.get(result['status'], "❓")
                logger.info(f"  {icon} {data_type.replace('_', ' ').upper():<18} | {result['status'].upper():<8} | {result['details']}")
                data_summary[data_type] = result['status']
        
        # Overall Statistics
        logger.info(f"\n📊 OVERALL STATISTICS:")
        logger.info("-" * 40)
        
        # Count successes
        asset_success = sum(1 for status in asset_summary.values() if status == 'success')
        asset_partial = sum(1 for status in asset_summary.values() if status == 'partial')
        data_success = sum(1 for status in data_summary.values() if status == 'success')
        data_partial = sum(1 for status in data_summary.values() if status == 'partial')
        
        total_asset_tests = len([r for r in market_access_results['asset_classes'].values() if r['tested']])
        total_data_tests = len([r for r in market_access_results['data_types'].values() if r.get('tested', False)])
        
        logger.info(f"  Asset Classes:     {asset_success}/{total_asset_tests} fully working, {asset_partial}/{total_asset_tests} partially working")
        logger.info(f"  Data Types:        {data_success}/{total_data_tests} fully working, {data_partial}/{total_data_tests} partially working")
        logger.info(f"  Total Success Rate: {((asset_success + data_success) / max(total_asset_tests + total_data_tests, 1) * 100):.1f}%")
        
        # Generate Recommendations
        recommendations = []
        if asset_summary.get('stocks') == 'failed':
            recommendations.append("📈 Check stock market data subscriptions - core equity access limited")
        if asset_summary.get('futures') in ['failed', 'partial']:
            recommendations.append("📊 Consider enabling futures trading permissions for full futures access")
        if asset_summary.get('commodities') in ['failed', 'partial']:
            recommendations.append("🥇 Commodity futures may require specific exchange data subscriptions")
        if asset_summary.get('bonds') in ['failed', 'partial']:
            recommendations.append("🏛️ Treasury futures access may require bond market data subscriptions")
        if data_summary.get('level2_depth') in ['failed', 'limited']:
            recommendations.append("📊 Level 2 market depth requires additional market data subscriptions")
        if data_summary.get('streaming_data') in ['failed', 'partial']:
            recommendations.append("📡 Streaming data issues may indicate market data permission limits")
        
        logger.info(f"\n💡 RECOMMENDATIONS:")
        logger.info("-" * 40)
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                logger.info(f"  {i}. {rec}")
        else:
            logger.info("  🎉 Excellent! All tested market access types are working well.")
        
        logger.info(f"\n⏱️  Test Duration: {summary.get('duration', 0):.1f} seconds")
        logger.info("=" * 70)
        logger.info("✨ Comprehensive Market Access Test Complete!")
        logger.info("=" * 70)
        
        # Clean up connection
        try:
            self.disconnect_from_ib()
        except:
            pass
        
        return market_access_results

    def test_comprehensive_tick_access(self):
        """
        Comprehensive tick testing function that tests ALL IBKR tick types and returns a detailed summary.
        
        This function tests:
        - Basic Price Ticks: BID, ASK, LAST, HIGH, LOW, CLOSE, OPEN
        - Size Ticks: BID_SIZE, ASK_SIZE, LAST_SIZE, VOLUME
        - Extended Ticks: 52-week high/low, option volume, implied volatility, etc.
        - Generic Ticks: Auction data, shortable shares, fundamental ratios, etc.
        - String Ticks: Last timestamp, news, dividends
        
        Returns:
            Dict: Comprehensive summary of all tick access test results
        """
        logger.info("\n🎯 === COMPREHENSIVE TICK ACCESS TEST ====")
        logger.info("=" * 70)
        
        # Initialize tick test results structure
        tick_test_results = {
            'connection_status': {'tested': False, 'status': 'unknown', 'details': ''},
            'tick_categories': {
                'basic_price_ticks': {'tested': False, 'status': 'unknown', 'details': '', 'ticks_tested': {}},
                'size_ticks': {'tested': False, 'status': 'unknown', 'details': '', 'ticks_tested': {}},
                'extended_price_ticks': {'tested': False, 'status': 'unknown', 'details': '', 'ticks_tested': {}},
                'generic_ticks': {'tested': False, 'status': 'unknown', 'details': '', 'ticks_tested': {}},
                'string_ticks': {'tested': False, 'status': 'unknown', 'details': '', 'ticks_tested': {}},
                'option_ticks': {'tested': False, 'status': 'unknown', 'details': '', 'ticks_tested': {}}
            },
            'asset_tick_compatibility': {
                'stocks': {'tested': False, 'status': 'unknown', 'details': '', 'successful_ticks': []},
                'futures': {'tested': False, 'status': 'unknown', 'details': '', 'successful_ticks': []},
                'options': {'tested': False, 'status': 'unknown', 'details': '', 'successful_ticks': []}
            },
            'test_summary': {
                'total_tick_types_tested': 0,
                'successful_ticks': 0,
                'failed_ticks': 0,
                'partial_ticks': 0,
                'start_time': datetime.now(),
                'end_time': None,
                'duration': None
            },
            'recommendations': []
        }
        
        # Connect to IB
        try:
            if not self.connected:
                if not self.ib_broker.connect():
                    tick_test_results['connection_status'] = {
                        'tested': True, 
                        'status': 'failed', 
                        'details': 'Cannot connect to Interactive Brokers Gateway/TWS'
                    }
                    return self._generate_tick_access_summary(tick_test_results)
                
            tick_test_results['connection_status'] = {
                'tested': True, 
                'status': 'success', 
                'details': 'Successfully connected to IB Gateway/TWS'
            }
            logger.info("✅ Connected to Interactive Brokers for tick testing")
            
        except Exception as e:
            tick_test_results['connection_status'] = {
                'tested': True, 
                'status': 'error', 
                'details': f'Connection error: {str(e)[:100]}'
            }
            return self._generate_tick_access_summary(tick_test_results)
        
        # Test 1: Basic Price Ticks
        logger.info("\n💰 Testing BASIC PRICE TICKS...")
        basic_price_results = self._test_basic_price_ticks()
        tick_test_results['tick_categories']['basic_price_ticks'] = basic_price_results
        
        # Test 2: Size Ticks
        logger.info("\n📊 Testing SIZE TICKS...")
        size_results = self._test_size_ticks()
        tick_test_results['tick_categories']['size_ticks'] = size_results
        
        # Test 3: Extended Price Ticks
        logger.info("\n📈 Testing EXTENDED PRICE TICKS...")
        extended_results = self._test_extended_price_ticks()
        tick_test_results['tick_categories']['extended_price_ticks'] = extended_results
        
        # Test 4: Generic Ticks
        logger.info("\n🔧 Testing GENERIC TICKS...")
        generic_results = self._test_generic_ticks()
        tick_test_results['tick_categories']['generic_ticks'] = generic_results
        
        # Test 5: String Ticks
        logger.info("\n📝 Testing STRING TICKS...")
        string_results = self._test_string_ticks()
        tick_test_results['tick_categories']['string_ticks'] = string_results
        
        # Test 6: Option Ticks (if option data is available)
        logger.info("\n📋 Testing OPTION TICKS...")
        option_results = self._test_option_ticks()
        tick_test_results['tick_categories']['option_ticks'] = option_results
        
        # Test 7: Asset-Tick Compatibility
        logger.info("\n🎯 Testing ASSET-TICK COMPATIBILITY...")
        self._test_asset_tick_compatibility(tick_test_results)
        
        # Finalize summary
        tick_test_results['test_summary']['end_time'] = datetime.now()
        tick_test_results['test_summary']['duration'] = (
            tick_test_results['test_summary']['end_time'] - 
            tick_test_results['test_summary']['start_time']
        ).total_seconds()
        
        # Generate and return comprehensive summary
        return self._generate_tick_access_summary(tick_test_results)

    def _test_basic_price_ticks(self):
        """Test basic price tick types (BID, ASK, LAST, HIGH, LOW, CLOSE, OPEN)."""
        result = {'tested': True, 'status': 'unknown', 'details': '', 'ticks_tested': {}}
        
        # Define basic price tick types according to IBKR API
        basic_price_ticks = {
            1: 'BID',
            2: 'ASK', 
            4: 'LAST',
            6: 'HIGH',
            7: 'LOW',
            9: 'CLOSE',
            14: 'OPEN'
        }
        
        # Test with liquid stock (SPY)
        try:
            spy_contract = self.ib_broker.create_stock_contract("SPY", "STK", "SMART")
            spy_contract.primaryExchange = "ARCA"
            
            logger.info("  Testing basic price ticks with SPY...")
            
            # Get market data snapshot to test all basic ticks
            snapshot = self.ib_broker.get_market_data_snapshot(
                contract=spy_contract,
                generic_tick_list="",  # Basic ticks don't need generic tick list
                timeout=8
            )
            
            successful_ticks = 0
            total_ticks = len(basic_price_ticks)
            
            if snapshot and not snapshot.get('error'):
                for tick_id, tick_name in basic_price_ticks.items():
                    if tick_name in snapshot and snapshot[tick_name] is not None:
                        result['ticks_tested'][tick_name] = {
                            'tick_id': tick_id,
                            'status': 'success',
                            'value': snapshot[tick_name],
                            'details': f'Received: {snapshot[tick_name]}'
                        }
                        successful_ticks += 1
                        logger.info(f"    ✅ {tick_name} (ID:{tick_id}): {snapshot[tick_name]}")
                    else:
                        result['ticks_tested'][tick_name] = {
                            'tick_id': tick_id,
                            'status': 'failed',
                            'value': None,
                            'details': 'No data received'
                        }
                        logger.info(f"    ⚠️ {tick_name} (ID:{tick_id}): No data")
            else:
                error_msg = snapshot.get('error', 'No response') if snapshot else 'No response'
                for tick_name in basic_price_ticks.values():
                    result['ticks_tested'][tick_name] = {
                        'status': 'error',
                        'details': f'Snapshot failed: {error_msg}'
                    }
                logger.warning(f"  ❌ Basic price tick test failed: {error_msg}")
            
            # Determine overall status
            if successful_ticks == total_ticks:
                result['status'] = 'success'
                result['details'] = f'All {total_ticks} basic price ticks working'
            elif successful_ticks > total_ticks // 2:
                result['status'] = 'partial' 
                result['details'] = f'{successful_ticks}/{total_ticks} basic price ticks working'
            else:
                result['status'] = 'failed'
                result['details'] = f'Only {successful_ticks}/{total_ticks} basic price ticks working'
                
        except Exception as e:
            result['status'] = 'error'
            result['details'] = f'Error testing basic price ticks: {str(e)[:100]}'
            logger.error(f"  ❌ Error in basic price tick testing: {e}")
        
        return result

    def _test_size_ticks(self):
        """Test size tick types (BID_SIZE, ASK_SIZE, LAST_SIZE, VOLUME)."""
        result = {'tested': True, 'status': 'unknown', 'details': '', 'ticks_tested': {}}
        
        # Define size tick types according to IBKR API
        size_ticks = {
            0: 'BID_SIZE',
            3: 'ASK_SIZE',
            5: 'LAST_SIZE',
            8: 'VOLUME'
        }
        
        try:
            spy_contract = self.ib_broker.create_stock_contract("SPY", "STK", "SMART")
            spy_contract.primaryExchange = "ARCA"
            
            logger.info("  Testing size ticks with SPY...")
            
            # Get market data snapshot to test size ticks
            snapshot = self.ib_broker.get_market_data_snapshot(
                contract=spy_contract,
                generic_tick_list="",
                timeout=8
            )
            
            successful_ticks = 0
            total_ticks = len(size_ticks)
            
            if snapshot and not snapshot.get('error'):
                for tick_id, tick_name in size_ticks.items():
                    if tick_name in snapshot and snapshot[tick_name] is not None:
                        result['ticks_tested'][tick_name] = {
                            'tick_id': tick_id,
                            'status': 'success',
                            'value': snapshot[tick_name],
                            'details': f'Received: {snapshot[tick_name]}'
                        }
                        successful_ticks += 1
                        logger.info(f"    ✅ {tick_name} (ID:{tick_id}): {snapshot[tick_name]}")
                    else:
                        result['ticks_tested'][tick_name] = {
                            'tick_id': tick_id,
                            'status': 'failed', 
                            'value': None,
                            'details': 'No data received'
                        }
                        logger.info(f"    ⚠️ {tick_name} (ID:{tick_id}): No data")
            else:
                error_msg = snapshot.get('error', 'No response') if snapshot else 'No response'
                for tick_name in size_ticks.values():
                    result['ticks_tested'][tick_name] = {
                        'status': 'error',
                        'details': f'Snapshot failed: {error_msg}'
                    }
                logger.warning(f"  ❌ Size tick test failed: {error_msg}")
            
            # Determine overall status
            if successful_ticks == total_ticks:
                result['status'] = 'success'
                result['details'] = f'All {total_ticks} size ticks working'
            elif successful_ticks > 0:
                result['status'] = 'partial'
                result['details'] = f'{successful_ticks}/{total_ticks} size ticks working'
            else:
                result['status'] = 'failed'
                result['details'] = f'No size ticks working ({total_ticks} tested)'
                
        except Exception as e:
            result['status'] = 'error'
            result['details'] = f'Error testing size ticks: {str(e)[:100]}'
            logger.error(f"  ❌ Error in size tick testing: {e}")
        
        return result

    def _test_extended_price_ticks(self):
        """Test extended price tick types (52-week high/low, etc.)."""
        result = {'tested': True, 'status': 'unknown', 'details': '', 'ticks_tested': {}}
        
        # Define extended price tick types that might be available
        extended_price_ticks = {
            15: '52_WEEK_HIGH',
            16: '52_WEEK_LOW', 
            30: 'BID_EXCH',
            31: 'ASK_EXCH',
            32: 'LAST_EXCH'
        }
        
        try:
            aapl_contract = self.ib_broker.create_stock_contract("AAPL", "STK", "SMART")
            aapl_contract.primaryExchange = "NASDAQ"
            
            logger.info("  Testing extended price ticks with AAPL...")
            
            # Note: Extended ticks may require specific generic tick codes
            snapshot = self.ib_broker.get_market_data_snapshot(
                contract=aapl_contract,
                generic_tick_list="",  # Try basic first
                timeout=8
            )
            
            successful_ticks = 0
            total_ticks = len(extended_price_ticks)
            
            if snapshot and not snapshot.get('error'):
                # Check if extended tick data is in the response
                for tick_id, tick_name in extended_price_ticks.items():
                    # Extended ticks might be in generic section or not available
                    tick_value = None
                    if f'GENERIC_{tick_id}' in snapshot:
                        tick_value = snapshot[f'GENERIC_{tick_id}']
                    elif tick_name in snapshot:
                        tick_value = snapshot[tick_name]
                    
                    if tick_value is not None:
                        result['ticks_tested'][tick_name] = {
                            'tick_id': tick_id,
                            'status': 'success',
                            'value': tick_value,
                            'details': f'Received: {tick_value}'
                        }
                        successful_ticks += 1
                        logger.info(f"    ✅ {tick_name} (ID:{tick_id}): {tick_value}")
                    else:
                        result['ticks_tested'][tick_name] = {
                            'tick_id': tick_id,
                            'status': 'limited',
                            'value': None,
                            'details': 'Extended tick may require specific subscription'
                        }
                        logger.info(f"    🟡 {tick_name} (ID:{tick_id}): Limited access")
            else:
                error_msg = snapshot.get('error', 'No response') if snapshot else 'No response'
                for tick_name in extended_price_ticks.values():
                    result['ticks_tested'][tick_name] = {
                        'status': 'error',
                        'details': f'Snapshot failed: {error_msg}'
                    }
                logger.warning(f"  ❌ Extended price tick test failed: {error_msg}")
            
            # Extended ticks are often limited - be lenient with success criteria
            if successful_ticks > 0:
                result['status'] = 'partial'
                result['details'] = f'{successful_ticks}/{total_ticks} extended price ticks available'
            else:
                result['status'] = 'limited'
                result['details'] = 'Extended price ticks may require specific subscriptions'
                
        except Exception as e:
            result['status'] = 'error'
            result['details'] = f'Error testing extended price ticks: {str(e)[:100]}'
            logger.error(f"  ❌ Error in extended price tick testing: {e}")
        
        return result

    def _test_generic_ticks(self):
        """Test generic tick types (auction data, shortable shares, etc.)."""
        result = {'tested': True, 'status': 'unknown', 'details': '', 'ticks_tested': {}}
        
        # Define important generic tick types according to IBKR API documentation
        generic_ticks = {
            100: 'OPTION_VOLUME',
            101: 'OPTION_OPEN_INTEREST',
            104: 'HISTORICAL_VOLATILITY',
            106: 'IMPLIED_VOLATILITY',
            225: 'AUCTION_IMBALANCE',
            233: 'RT_VOLUME',
            236: 'SHORTABLE_SHARES',
            256: 'INVENTORY',
            293: 'TRADE_RATE',
            375: 'RT_TRADE_VOLUME',
            411: 'REALTIME_HISTORICAL_VOLATILITY'
        }
        
        try:
            spy_contract = self.ib_broker.create_stock_contract("SPY", "STK", "SMART")
            spy_contract.primaryExchange = "ARCA"
            
            logger.info("  Testing generic ticks with SPY...")
            
            # Test with a selection of important generic ticks
            test_generic_list = "225,233,236,256,293"  # Most commonly available
            
            snapshot = self.ib_broker.get_market_data_snapshot(
                contract=spy_contract,
                generic_tick_list=test_generic_list,
                timeout=10
            )
            
            successful_ticks = 0
            total_ticks = len([tick for tick in test_generic_list.split(',')])
            
            if snapshot and not snapshot.get('error'):
                for tick_code in test_generic_list.split(','):
                    tick_id = int(tick_code)
                    tick_name = generic_ticks.get(tick_id, f'GENERIC_{tick_id}')
                    
                    # Check for generic tick data
                    tick_value = None
                    if f'GENERIC_{tick_id}' in snapshot:
                        tick_value = snapshot[f'GENERIC_{tick_id}']
                    
                    if tick_value is not None and tick_value != '' and tick_value != '0':
                        result['ticks_tested'][tick_name] = {
                            'tick_id': tick_id,
                            'status': 'success',
                            'value': tick_value,
                            'details': f'Received: {tick_value}'
                        }
                        successful_ticks += 1
                        logger.info(f"    ✅ {tick_name} (ID:{tick_id}): {tick_value}")
                    else:
                        result['ticks_tested'][tick_name] = {
                            'tick_id': tick_id,
                            'status': 'limited',
                            'value': tick_value,
                            'details': 'Generic tick may require subscription or market conditions'
                        }
                        logger.info(f"    🟡 {tick_name} (ID:{tick_id}): Limited/No data")
                
                # Also check for any other generic ticks that might be present
                for key, value in snapshot.items():
                    if key.startswith('GENERIC_') and key not in [f'GENERIC_{int(code)}' for code in test_generic_list.split(',')]:
                        generic_id = key.replace('GENERIC_', '')
                        generic_name = f'UNKNOWN_GENERIC_{generic_id}'
                        result['ticks_tested'][generic_name] = {
                            'tick_id': generic_id,
                            'status': 'success',
                            'value': value,
                            'details': f'Unexpected generic tick found: {value}'
                        }
                        logger.info(f"    ✨ {generic_name}: {value}")
                        
            else:
                error_msg = snapshot.get('error', 'No response') if snapshot else 'No response'
                for tick_code in test_generic_list.split(','):
                    tick_id = int(tick_code)
                    tick_name = generic_ticks.get(tick_id, f'GENERIC_{tick_id}')
                    result['ticks_tested'][tick_name] = {
                        'status': 'error',
                        'details': f'Snapshot failed: {error_msg}'
                    }
                logger.warning(f"  ❌ Generic tick test failed: {error_msg}")
            
            # Generic ticks are often subscription-dependent - be realistic with expectations
            if successful_ticks >= total_ticks // 2:
                result['status'] = 'success'
                result['details'] = f'{successful_ticks}/{total_ticks} generic ticks working'
            elif successful_ticks > 0:
                result['status'] = 'partial'
                result['details'] = f'{successful_ticks}/{total_ticks} generic ticks available'
            else:
                result['status'] = 'limited'
                result['details'] = 'Generic ticks may require specific market data subscriptions'
                
        except Exception as e:
            result['status'] = 'error'
            result['details'] = f'Error testing generic ticks: {str(e)[:100]}'
            logger.error(f"  ❌ Error in generic tick testing: {e}")
        
        return result

    def _test_string_ticks(self):
        """Test string tick types (timestamps, news, etc.)."""
        result = {'tested': True, 'status': 'unknown', 'details': '', 'ticks_tested': {}}
        
        # Define string tick types according to IBKR API
        string_ticks = {
            45: 'LAST_TIMESTAMP',
            49: 'HALTED',
            59: 'DIVIDENDS'
        }
        
        try:
            aapl_contract = self.ib_broker.create_stock_contract("AAPL", "STK", "SMART")
            aapl_contract.primaryExchange = "NASDAQ"
            
            logger.info("  Testing string ticks with AAPL...")
            
            snapshot = self.ib_broker.get_market_data_snapshot(
                contract=aapl_contract,
                generic_tick_list="",
                timeout=8
            )
            
            successful_ticks = 0
            total_ticks = len(string_ticks)
            
            if snapshot and not snapshot.get('error'):
                for tick_id, tick_name in string_ticks.items():
                    tick_value = None
                    
                    # String ticks might be in different format
                    if tick_name in snapshot:
                        tick_value = snapshot[tick_name]
                    elif f'STRING_{tick_id}' in snapshot:
                        tick_value = snapshot[f'STRING_{tick_id}']
                    
                    if tick_value is not None and tick_value != '':
                        result['ticks_tested'][tick_name] = {
                            'tick_id': tick_id,
                            'status': 'success',
                            'value': tick_value,
                            'details': f'Received: {tick_value}'
                        }
                        successful_ticks += 1
                        logger.info(f"    ✅ {tick_name} (ID:{tick_id}): {tick_value}")
                    else:
                        result['ticks_tested'][tick_name] = {
                            'tick_id': tick_id,
                            'status': 'limited',
                            'value': None,
                            'details': 'String tick not available or empty'
                        }
                        logger.info(f"    🟡 {tick_name} (ID:{tick_id}): No string data")
            else:
                error_msg = snapshot.get('error', 'No response') if snapshot else 'No response'
                for tick_name in string_ticks.values():
                    result['ticks_tested'][tick_name] = {
                        'status': 'error',
                        'details': f'Snapshot failed: {error_msg}'
                    }
                logger.warning(f"  ❌ String tick test failed: {error_msg}")
            
            # String ticks are often optional - be lenient
            if successful_ticks > 0:
                result['status'] = 'success'
                result['details'] = f'{successful_ticks}/{total_ticks} string ticks available'
            else:
                result['status'] = 'limited'
                result['details'] = 'String ticks not available - may be conditional or require subscriptions'
                
        except Exception as e:
            result['status'] = 'error'
            result['details'] = f'Error testing string ticks: {str(e)[:100]}'
            logger.error(f"  ❌ Error in string tick testing: {e}")
        
        return result

    def _test_option_ticks(self):
        """Test option-specific tick types (implied volatility, option volume, etc.)."""
        result = {'tested': True, 'status': 'unknown', 'details': '', 'ticks_tested': {}}
        
        # Define option-specific tick types
        option_ticks = {
            10: 'BID_IMPLIED_VOL',
            11: 'ASK_IMPLIED_VOL', 
            12: 'LAST_IMPLIED_VOL',
            13: 'MODEL_OPTION_PRICE',
            27: 'CALL_OPTION_VOLUME',
            28: 'PUT_OPTION_VOLUME'
        }
        
        try:
            # Create an option contract - this is more complex and may not always work
            logger.info("  Testing option ticks (may have limited access)...")
            
            # Try to create a simple SPY option contract
            # Note: This is simplified - in practice, you'd need to get actual option chains
            spy_option = Contract()
            spy_option.symbol = "SPY"
            spy_option.secType = "OPT"
            spy_option.exchange = "SMART"
            spy_option.currency = "USD"
            spy_option.lastTradeDateOrContractMonth = "20260321"  # March 2026 expiry
            spy_option.strike = 500.0  # ATM strike (approximate)
            spy_option.right = "C"  # Call option
            
            # Test option ticks with generic tick list for options
            snapshot = self.ib_broker.get_market_data_snapshot(
                contract=spy_option,
                generic_tick_list="100,101,104,106",  # Option-related generic ticks
                timeout=10
            )
            
            successful_ticks = 0
            total_ticks = len(option_ticks)
            
            if snapshot and not snapshot.get('error'):
                for tick_id, tick_name in option_ticks.items():
                    tick_value = None
                    
                    # Option ticks might be in various formats
                    if tick_name in snapshot:
                        tick_value = snapshot[tick_name]
                    elif f'OPTION_{tick_id}' in snapshot:
                        tick_value = snapshot[f'OPTION_{tick_id}']
                    elif f'GENERIC_{tick_id}' in snapshot:
                        tick_value = snapshot[f'GENERIC_{tick_id}']
                    
                    if tick_value is not None and tick_value != '' and tick_value != 0:
                        result['ticks_tested'][tick_name] = {
                            'tick_id': tick_id,
                            'status': 'success',
                            'value': tick_value,
                            'details': f'Received: {tick_value}'
                        }
                        successful_ticks += 1
                        logger.info(f"    ✅ {tick_name} (ID:{tick_id}): {tick_value}")
                    else:
                        result['ticks_tested'][tick_name] = {
                            'tick_id': tick_id,
                            'status': 'limited',
                            'value': None,
                            'details': 'Option tick requires option trading permissions'
                        }
                        logger.info(f"    🟡 {tick_name} (ID:{tick_id}): Limited access")
            else:
                error_msg = snapshot.get('error', 'No option data') if snapshot else 'No response'
                for tick_name in option_ticks.values():
                    result['ticks_tested'][tick_name] = {
                        'status': 'limited',
                        'details': f'Option access limited: {error_msg}'
                    }
                logger.info(f"  🟡 Option tick access limited: {error_msg}")
            
            # Option ticks often require special permissions
            if successful_ticks > 0:
                result['status'] = 'success'
                result['details'] = f'{successful_ticks}/{total_ticks} option ticks available'
            else:
                result['status'] = 'limited'
                result['details'] = 'Option ticks require option trading permissions and market data subscriptions'
                
        except Exception as e:
            result['status'] = 'limited'
            result['details'] = f'Option access limited - requires option permissions: {str(e)[:50]}'
            logger.info(f"  🟡 Option tick testing limited: {str(e)[:50]}")
        
        return result

    def _test_asset_tick_compatibility(self, tick_test_results):
        """Test tick compatibility across different asset classes."""
        
        # Test Stocks
        logger.info("  📋 Testing tick compatibility with STOCKS...")
        try:
            tsla_contract = self.ib_broker.create_stock_contract("TSLA", "STK", "SMART")
            tsla_contract.primaryExchange = "NASDAQ"
            
            snapshot = self.ib_broker.get_market_data_snapshot(
                contract=tsla_contract,
                generic_tick_list="225,236",
                timeout=8
            )
            
            successful_ticks = []
            if snapshot and not snapshot.get('error'):
                basic_ticks = ['BID', 'ASK', 'LAST', 'VOLUME']
                for tick in basic_ticks:
                    if tick in snapshot and snapshot[tick] is not None:
                        successful_ticks.append(tick)
                
                tick_test_results['asset_tick_compatibility']['stocks'] = {
                    'tested': True,
                    'status': 'success' if len(successful_ticks) >= 3 else 'partial',
                    'details': f'{len(successful_ticks)} basic ticks working with stocks',
                    'successful_ticks': successful_ticks
                }
                logger.info(f"    ✅ Stocks: {len(successful_ticks)} ticks working")
            else:
                tick_test_results['asset_tick_compatibility']['stocks'] = {
                    'tested': True, 'status': 'failed',
                    'details': 'Stock tick compatibility test failed',
                    'successful_ticks': []
                }
        except Exception as e:
            tick_test_results['asset_tick_compatibility']['stocks'] = {
                'tested': True, 'status': 'error',
                'details': f'Error: {str(e)[:100]}', 'successful_ticks': []
            }
        
        # Test Futures
        logger.info("  📈 Testing tick compatibility with FUTURES...")
        try:
            es_contract = self.ib_broker.create_stock_contract("ES", "FUT", "CME")
            es_contract.currency = "USD"
            
            snapshot = self.ib_broker.get_market_data_snapshot(
                contract=es_contract,
                generic_tick_list="",
                timeout=8
            )
            
            successful_ticks = []
            if snapshot and not snapshot.get('error'):
                basic_ticks = ['BID', 'ASK', 'LAST', 'VOLUME']
                for tick in basic_ticks:
                    if tick in snapshot and snapshot[tick] is not None:
                        successful_ticks.append(tick)
                
                tick_test_results['asset_tick_compatibility']['futures'] = {
                    'tested': True,
                    'status': 'success' if len(successful_ticks) >= 2 else 'partial',
                    'details': f'{len(successful_ticks)} basic ticks working with futures',
                    'successful_ticks': successful_ticks
                }
                logger.info(f"    ✅ Futures: {len(successful_ticks)} ticks working")
            else:
                tick_test_results['asset_tick_compatibility']['futures'] = {
                    'tested': True, 'status': 'limited',
                    'details': 'Futures tick compatibility limited',
                    'successful_ticks': []
                }
        except Exception as e:
            tick_test_results['asset_tick_compatibility']['futures'] = {
                'tested': True, 'status': 'error',
                'details': f'Error: {str(e)[:100]}', 'successful_ticks': []
            }
        
        # Test Options (limited test due to complexity)
        logger.info("  📋 Testing tick compatibility with OPTIONS...")
        tick_test_results['asset_tick_compatibility']['options'] = {
            'tested': True, 'status': 'limited',
            'details': 'Option tick testing requires specific option contracts and permissions',
            'successful_ticks': []
        }
        logger.info("    🟡 Options: Testing limited due to contract complexity")

    def _generate_tick_access_summary(self, tick_test_results):
        """Generate comprehensive summary of tick access test results."""
        
        logger.info("\\n" + "=" * 70)
        logger.info("🎯 === COMPREHENSIVE TICK ACCESS SUMMARY ===")
        logger.info("=" * 70)
        
        summary = tick_test_results['test_summary']
        summary['end_time'] = datetime.now()
        
        # Connection Status
        logger.info(f"\\n🔌 CONNECTION STATUS:")
        conn = tick_test_results['connection_status']
        status_icon = "✅" if conn['status'] == 'success' else "❌"
        logger.info(f"  {status_icon} {conn['details']}")
        
        # Tick Categories Summary
        logger.info(f"\\n🎯 TICK CATEGORIES ACCESS:")
        logger.info("-" * 50)
        
        category_summary = {}
        total_successful_ticks = 0
        total_tested_ticks = 0
        
        for category, result in tick_test_results['tick_categories'].items():
            if result['tested']:
                icon_map = {
                    "success": "✅", "partial": "🟡", "limited": "⚠️", 
                    "failed": "❌", "error": "🔥"
                }
                icon = icon_map.get(result['status'], "❓")
                logger.info(f"  {icon} {category.replace('_', ' ').upper():<20} | {result['status'].upper():<8} | {result['details']}")
                category_summary[category] = result['status']
                
                # Count successful ticks in this category
                if 'ticks_tested' in result:
                    for tick_name, tick_data in result['ticks_tested'].items():
                        total_tested_ticks += 1
                        if tick_data.get('status') == 'success':
                            total_successful_ticks += 1
        
        # Asset Compatibility Summary
        logger.info(f"\\n📋 ASSET TICK COMPATIBILITY:")
        logger.info("-" * 50)
        
        for asset_type, result in tick_test_results['asset_tick_compatibility'].items():
            if result['tested']:
                icon_map = {
                    "success": "✅", "partial": "🟡", "limited": "⚠️", 
                    "failed": "❌", "error": "🔥"
                }
                icon = icon_map.get(result['status'], "❓")
                successful_count = len(result.get('successful_ticks', []))
                logger.info(f"  {icon} {asset_type.upper():<12} | {result['status'].upper():<8} | {successful_count} ticks | {result['details']}")
        
        # Overall Statistics
        logger.info(f"\\n📊 OVERALL TICK STATISTICS:")
        logger.info("-" * 50)
        
        if total_tested_ticks > 0:
            success_rate = (total_successful_ticks / total_tested_ticks) * 100
            logger.info(f"  Total Ticks Tested:     {total_tested_ticks}")
            logger.info(f"  Successful Ticks:       {total_successful_ticks} ({success_rate:.1f}%)")
            logger.info(f"  Limited/Failed Ticks:   {total_tested_ticks - total_successful_ticks}")
        else:
            logger.info("  No tick data collected - connection or access issues")
        
        # Generate Recommendations
        logger.info(f"\\n💡 TICK ACCESS RECOMMENDATIONS:")
        logger.info("-" * 50)
        
        recommendations = []
        
        if category_summary.get('basic_price_ticks') == 'failed':
            recommendations.append("💰 Basic price tick access failed - check market data permissions")
        if category_summary.get('size_ticks') == 'failed':
            recommendations.append("📊 Size tick access failed - verify Level 1 data subscription")
        if category_summary.get('generic_ticks') == 'limited':
            recommendations.append("🔧 Generic ticks limited - consider upgrading market data packages")
        if category_summary.get('option_ticks') == 'limited':
            recommendations.append("📋 Option ticks require option trading permissions and data subscriptions")
        if category_summary.get('extended_price_ticks') == 'limited':
            recommendations.append("📈 Extended price ticks may require premium market data subscriptions")
        
        # Asset-specific recommendations
        asset_compat = tick_test_results['asset_tick_compatibility']
        if asset_compat['stocks']['status'] in ['failed', 'error']:
            recommendations.append("📋 Stock tick compatibility issues - verify equity market data access")
        if asset_compat['futures']['status'] in ['limited', 'error']:
            recommendations.append("📈 Futures tick access limited - may require futures data subscriptions")
        
        if recommendations:
            for i, rec in enumerate(recommendations, 1):
                logger.info(f"  {i}. {rec}")
        else:
            logger.info("  🎉 Excellent! Your tick access configuration is working well across all tested categories.")
        
        # Test Duration
        duration = summary.get('duration', 0)
        #logger.info(f"\\n⏱️  Test Duration: {duration:.1f} seconds")
        #logger.info(f"Performance: {total_tested_ticks / max(duration, 1):.1f} ticks tested per second")
        
        logger.info("=" * 70)
        logger.info("✨ Comprehensive Tick Access Test Complete!")
        logger.info("=" * 70)
        
        # Clean up connection
        try:
            self.disconnect_from_ib()
        except:
            pass
        
        return tick_test_results
    
    def test_account_access(self):
        """
        Comprehensive test function that tests IBKR account data access.

        This function tests:
        - Account summary (cash, net liquidation, margin, etc.)
        - Portfolio positions
        - Account values consistency
        - Multi-account support

        Returns:
            Dict: Comprehensive summary of account access test results
        """

        logger.info("\n🏦 === ACCOUNT ACCESS TEST ===")
        logger.info("=" * 70)

        account_results = {
            'connection_status': {'tested': False, 'status': 'unknown', 'details': ''},
            'account_summary': {'tested': False, 'status': 'unknown', 'details': '', 'data': {}},
            'positions': {'tested': False, 'status': 'unknown', 'details': '', 'count': 0},
            'account_values': {'tested': False, 'status': 'unknown', 'details': '', 'keys': []},
            'multi_account': {'tested': False, 'status': 'unknown', 'details': '', 'accounts_found': []},
            'test_summary': {
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'partial': 0,
                'start_time': datetime.now(),
                'end_time': None,
                'duration': None
            },
            'recommendations': []
        }

        # ---------------------------
        # Connection
        # ---------------------------
        try:
            if not self.connected:
                if not self.ib_broker.connect():
                    account_results['connection_status'] = {
                        'tested': True,
                        'status': 'failed',
                        'details': 'Cannot connect to IB Gateway/TWS'
                    }
                    return self._generate_account_summary(account_results)

            account_results['connection_status'] = {
                'tested': True,
                'status': 'success',
                'details': 'Connected to IBKR'
            }
            logger.info("✅ Connected to IBKR")

        except Exception as e:
            account_results['connection_status'] = {
                'tested': True,
                'status': 'error',
                'details': f'Connection error: {str(e)[:100]}'
            }
            return self._generate_account_summary(account_results)

        ib = self.ib_broker # assuming ib_insync instance
        account_summary = self._get_account_summary()
        positions = self._get_positions()
        # ---------------------------
        # Test 1: Account Summary
        # ---------------------------
        logger.info("\n💰 Testing Account Summary...")
        try:
            summary = self.accountSummary()

            if summary:
                extracted = {item.tag: item.value for item in summary}

                account_results['account_summary'] = {
                    'tested': True,
                    'status': 'success',
                    'details': f"Retrieved {len(summary)} summary fields",
                    'data': {
                        'NetLiquidation': extracted.get('NetLiquidation'),
                        'AvailableFunds': extracted.get('AvailableFunds'),
                        'BuyingPower': extracted.get('BuyingPower'),
                        'CashBalance': extracted.get('TotalCashValue')
                    }
                }
                logger.info(f"✅ Account summary retrieved ({len(summary)} fields)")
            else:
                account_results['account_summary'] = {
                    'tested': True,
                    'status': 'failed',
                    'details': 'Empty account summary response'
                }

        except Exception as e:
            account_results['account_summary'] = {
                'tested': True,
                'status': 'error',
                'details': str(e)[:100]
            }

        # ---------------------------
        # Test 2: Positions
        # ---------------------------
        logger.info("\n📊 Testing Positions...")
        try:
            positions = self.positions()

            account_results['positions'] = {
                'tested': True,
                'status': 'success' if positions else 'partial',
                'details': f"{len(positions)} positions retrieved",
                'count': len(positions)
            }

            logger.info(f"✅ Positions retrieved: {len(positions)}")

        except Exception as e:
            account_results['positions'] = {
                'tested': True,
                'status': 'error',
                'details': str(e)[:100],
                'count': 0
            }

        # ---------------------------
        # Test 3: Account Values
        # ---------------------------
        logger.info("\n📋 Testing Account Values...")
        try:
            values = ib.accountValues()

            keys = list(set([v.tag for v in values]))

            account_results['account_values'] = {
                'tested': True,
                'status': 'success' if values else 'failed',
                'details': f"{len(values)} values retrieved",
                'keys': keys[:10]  # limit output
            }

            logger.info(f"✅ Account values retrieved: {len(values)}")

        except Exception as e:
            account_results['account_values'] = {
                'tested': True,
                'status': 'error',
                'details': str(e)[:100],
                'keys': []
            }

        # ---------------------------
        # Test 4: Multi-account detection
        # ---------------------------
        logger.info("\n🏢 Testing Multi-Account Access...")
        try:
            accounts = self.managedAccounts()

            account_results['multi_account'] = {
                'tested': True,
                'status': 'success',
                'details': f"{len(accounts)} account(s) detected",
                'accounts_found': accounts
            }

            logger.info(f"✅ Accounts detected: {accounts}")

        except Exception as e:
            account_results['multi_account'] = {
                'tested': True,
                'status': 'error',
                'details': str(e)[:100],
                'accounts_found': []
            }

        # ---------------------------
        # Final Summary
        # ---------------------------
        account_results['test_summary']['end_time'] = datetime.now()
        account_results['test_summary']['duration'] = (
            account_results['test_summary']['end_time'] -
            account_results['test_summary']['start_time']
        )

        # Count results
        for section in ['account_summary', 'positions', 'account_values', 'multi_account']:
            account_results['test_summary']['total_tests'] += 1
            status = account_results[section]['status']

            if status == 'success':
                account_results['test_summary']['passed'] += 1
            elif status == 'partial':
                account_results['test_summary']['partial'] += 1
            else:
                account_results['test_summary']['failed'] += 1

        # Recommendations
        if account_results['account_summary']['status'] != 'success':
            account_results['recommendations'].append("Check IBKR account data permissions")

        if account_results['positions']['count'] == 0:
            account_results['recommendations'].append("No positions found - verify portfolio is funded")

        if account_results['multi_account']['status'] != 'success':
            account_results['recommendations'].append("Multi-account access may be restricted")

        return self._generate_account_summary(account_results)


    def _generate_account_summary(self, results: dict) -> dict:
        """
        Generate final formatted summary for account access test.
        """

        summary = results['test_summary']

        # Compute totals safely
        total = summary['total_tests']
        passed = summary['passed']
        failed = summary['failed']
        partial = summary['partial']

        success_rate = (passed / total * 100) if total > 0 else 0

        logger.info("\n📊 === ACCOUNT ACCESS SUMMARY ===")
        logger.info("=" * 70)
        logger.info(f"Total Tests   : {total}")
        logger.info(f"✅ Passed     : {passed}")
        logger.info(f"❌ Failed     : {failed}")
        logger.info(f"⚠️ Partial    : {partial}")
        logger.info(f"📈 Success %  : {success_rate:.2f}%")
        logger.info(f"⏱ Duration   : {summary['duration']}")

        # Log key account info if available
        acc_summary = results.get('account_summary', {}).get('data', {})
        if acc_summary:
            logger.info("\n💰 Account Snapshot:")
            for k, v in acc_summary.items():
                logger.info(f"   {k}: {v}")

        # Recommendations
        if results['recommendations']:
            logger.info("\n💡 Recommendations:")
            for rec in results['recommendations']:
                logger.info(f" - {rec}")

        return results
    
    def _get_account_summary(self):
        """
        Extract account summary from IBTWSClient internal state.
        """

        ib = self.ib_broker.ib_connection

        if not ib.account_summary:
            return None

        # Normalize structure
        summary = {
            key: {
                'value': float(value['value']),
                'currency': value['currency'],
                'account': value['account']
            }
            for key, value in ib.account_summary.items()
        }

        return summary
    
    def _get_positions(self):
        """
        Extract positions from IBTWSClient.
        """

        ib = self.ib_broker.ib_connection

        if not ib.positions:
            return []

        normalized_positions = []

        for pos in ib.positions:
            try:
                normalized_positions.append({
                    'symbol': getattr(pos.contract, 'symbol', None),
                    'secType': getattr(pos.contract, 'secType', None),
                    'currency': getattr(pos.contract, 'currency', None),
                    'position': pos.position,
                    'avgCost': pos.avgCost
                })
            except Exception:
                continue

        return normalized_positions
    def get_by_conid(self, conid: int, get_market_data: bool = True, timeout: int = 15) -> Dict[str, Any]:
        """
        Get contract details and optionally market data by Contract Identifier (CONID).
        
        Args:
            conid: Interactive Brokers Contract Identifier
            get_market_data: If True, also fetch current market data snapshot
            timeout: Timeout in seconds for requests
            
        Returns:
            Dictionary containing contract details and optionally market data
            
        Example:
            # Get contract details only
            result = examples.get_by_conid(123456789, get_market_data=False)
            
            # Get contract details and market data
            result = examples.get_by_conid(123456789, get_market_data=True)
        """
        logger.info(f"\n=== Get by CONID: {conid} ===")
        
        if not self.connected:
            logger.info("Connecting to IB...")
            self.ib_broker.connect()
            
        
        
        try:
            # Create a contract with the specified CONID
            contract = Contract()
            contract.conId = conid
            
            # First, get contract details to fully populate the contract
            logger.info(f"📋 Fetching contract details for CONID {conid}...")
            contract_details = self.ib_broker.get_contract_details(contract, timeout=timeout)
            
            result = {
                'status': 'success',
                'conid': conid,
                'contract_details': contract_details,
                'market_data': None,
                'timestamp': datetime.now().isoformat()
            }
            
            if contract_details:
                logger.info(f"✅ Found contract details for CONID {conid}")
                
                # Log basic contract info
                if len(contract_details) > 0:
                    detail = contract_details[0]
                    logger.info(f"  Symbol: {detail.get('symbol', 'N/A')}")
                    logger.info(f"  Exchange: {detail.get('exchange', 'N/A')}")
                    logger.info(f"  Currency: {detail.get('currency', 'N/A')}")
                    logger.info(f"  Security Type: {detail.get('sec_type', 'N/A')}")
                    
                    # If market data is requested, fetch it using the first contract detail
                    if get_market_data:
                        logger.info(f"📊 Fetching market data for CONID {conid}...")
                        
                        try:
                            # Create a proper contract from the details for market data request
                            market_contract = Contract()
                            market_contract.conId = conid
                            market_contract.symbol = detail.get('symbol', '')
                            market_contract.secType = detail.get('sec_type', '')
                            market_contract.exchange = detail.get('exchange', '')
                            market_contract.currency = detail.get('currency', 'USD')
                            
                            # Get market data snapshot
                            market_data = self.ib_broker.get_market_data_snapshot(
                                market_contract, 
                                timeout=timeout
                            )
                            
                            if market_data:
                                result['market_data'] = market_data
                                logger.info(f"✅ Market data retrieved for CONID {conid}")
                                
                                # Log key market data points
                                if 'bid' in market_data:
                                    logger.info(f"  Bid: {market_data.get('bid', 'N/A')}")
                                if 'ask' in market_data:
                                    logger.info(f"  Ask: {market_data.get('ask', 'N/A')}")
                                if 'last' in market_data:
                                    logger.info(f"  Last: {market_data.get('last', 'N/A')}")
                                if 'volume' in market_data:
                                    logger.info(f"  Volume: {market_data.get('volume', 'N/A')}")
                            else:
                                logger.warning(f"⚠️ No market data available for CONID {conid}")
                                result['market_data'] = {'status': 'no_data', 'message': 'Market data not available'}
                                
                        except Exception as market_data_error:
                            logger.error(f"❌ Error fetching market data for CONID {conid}: {market_data_error}")
                            result['market_data'] = {
                                'status': 'error', 
                                'message': f'Market data error: {str(market_data_error)}'
                            }
            else:
                logger.warning(f"⚠️ No contract details found for CONID {conid}")
                result['status'] = 'not_found'
                result['message'] = f'No contract found for CONID {conid}'
                
            return result
            
        except Exception as e:
            logger.error(f"❌ Error fetching data for CONID {conid}: {e}")
            return {
                'status': 'error',
                'message': f'Error: {str(e)}',
                'conid': conid,
                'timestamp': datetime.now().isoformat()
            }
        
        finally:
            # Note: We don't disconnect here to allow for multiple calls
            # The user can call disconnect_from_ib() explicitly when done
            pass

    def get_volatility_surface(self, symbol: str, sec_type: str = "STK", exchange: str = "SMART", 
                             currency: str = "USD", get_implied_volatility: bool = True, 
                             max_strikes: int = 20, max_expirations: int = 6, 
                             timeout: int = 30) -> Dict[str, Any]:
        """
        Get volatility surface data for options on a given underlying security.
        
        This function creates a comprehensive volatility surface by:
        1. Finding the underlying security contract details
        2. Getting available options chains for the underlying
        3. Fetching market data and implied volatility for option contracts
        4. Organizing data by expiration dates and strike prices
        5. Building a volatility surface structure
        
        Args:
            symbol: Underlying security symbol (e.g., "AAPL", "SPY", "ES")
            sec_type: Security type of underlying ("STK" for stocks, "FUT" for futures)
            exchange: Exchange for underlying security
            currency: Currency for contracts
            get_implied_volatility: If True, fetch implied volatility data
            max_strikes: Maximum number of strikes per expiration
            max_expirations: Maximum number of expiration dates
            timeout: Timeout in seconds for requests
            
        Returns:
            Dictionary containing volatility surface data organized by expiration and strike
            
        Example:
            # Get volatility surface for AAPL stock
            result = examples.get_volatility_surface("AAPL", "STK", "SMART")
            
            # Get volatility surface for ES futures
            result = examples.get_volatility_surface("ES", "FUT", "CME")
        """
        logger.info(f"\n=== Building Volatility Surface for {symbol} ===")
        
        if not self.connected:
            logger.info("Connecting to IB...")
            self.ib_broker.connect()
            
        result = {
            'status': 'success',
            'symbol': symbol,
            'sec_type': sec_type,
            'exchange': exchange,
            'currency': currency,
            'timestamp': datetime.now().isoformat(),
            'underlying_data': None,
            'options_chains': {},
            'volatility_surface': {},
            'summary_stats': {},
            'error_messages': []
        }
        
        try:
            # 1. Create and validate underlying contract
            logger.info(f"📋 Creating underlying contract for {symbol}...")
            underlying_contract = Contract()
            underlying_contract.symbol = symbol
            underlying_contract.secType = sec_type
            underlying_contract.exchange = exchange
            underlying_contract.currency = currency
            
            # For futures, we may need to specify contract month
            if sec_type == "FUT":
                # Use nearest month as default - this can be enhanced
                current_date = datetime.now()
                contract_month = f"{current_date.year}{current_date.month:02d}"
                underlying_contract.lastTradeDateOrContractMonth = contract_month
            
            # 2. Get underlying contract details
            logger.info(f"🔍 Fetching underlying contract details...")
            underlying_details = self.ib_broker.get_contract_details(underlying_contract, timeout=timeout)
            
            if not underlying_details:
                result['status'] = 'error'
                result['error_messages'].append(f'Could not find underlying contract for {symbol}')
                return result
            
            result['underlying_data'] = underlying_details[0] if underlying_details else None
            logger.info(f"✅ Found underlying: {symbol}")
            
            # 3. Get underlying market data for reference price
            underlying_price = None
            try:
                logger.info(f"📊 Fetching underlying market data...")
                underlying_market_data = self.ib_broker.get_market_data_snapshot(
                    underlying_contract, timeout=timeout
                )
                
                if underlying_market_data:
                    underlying_price = underlying_market_data.get('last') or underlying_market_data.get('mark') or underlying_market_data.get('mid')
                    result['underlying_data']['market_data'] = underlying_market_data
                    logger.info(f"  Underlying price: {underlying_price}")
            except Exception as e:
                logger.warning(f"⚠️ Could not get underlying market data: {e}")
                result['error_messages'].append(f'Underlying market data error: {str(e)}')
            
            # 4. Search for options contracts
            logger.info(f"🔎 Searching for options on {symbol}...")
            options_contract = Contract()
            options_contract.symbol = symbol
            options_contract.secType = "OPT"
            options_contract.exchange = "SMART"
            options_contract.currency = currency
            
            # Get all available options contracts
            options_details = self.ib_broker.get_contract_details(options_contract, timeout=timeout)
            
            if not options_details:
                result['status'] = 'partial'
                result['error_messages'].append(f'No options found for {symbol}')
                logger.warning(f"⚠️ No options contracts found for {symbol}")
                return result
                
            logger.info(f"📈 Found {len(options_details)} options contracts")
            
            # 5. Organize options by expiration date and strike
            options_by_expiry = {}
            for option_detail in options_details[:100]:  # Limit to prevent overload
                try:
                    expiry = option_detail.get('expiry', 'unknown')
                    strike = float(option_detail.get('strike', 0))
                    right = option_detail.get('right', '')
                    
                    if expiry not in options_by_expiry:
                        options_by_expiry[expiry] = {'calls': {}, 'puts': {}}
                    
                    if right == 'C':
                        options_by_expiry[expiry]['calls'][strike] = option_detail
                    elif right == 'P':
                        options_by_expiry[expiry]['puts'][strike] = option_detail
                        
                except (ValueError, KeyError) as e:
                    continue
            
            result['options_chains'] = options_by_expiry
            logger.info(f"📊 Organized options into {len(options_by_expiry)} expiration dates")
            
            # 6. Build volatility surface by fetching market data for key options
            if get_implied_volatility:
                logger.info(f"🌊 Building volatility surface...")
                vol_surface = {}
                processed_count = 0
                
                # Process limited number of expirations
                for expiry in sorted(list(options_by_expiry.keys()))[:max_expirations]:
                    vol_surface[expiry] = {'calls': {}, 'puts': {}}
                    expiry_data = options_by_expiry[expiry]
                    
                    # Process calls
                    call_strikes = sorted(list(expiry_data['calls'].keys()))
                    selected_call_strikes = call_strikes[:max_strikes//2] if len(call_strikes) > max_strikes//2 else call_strikes
                    
                    for strike in selected_call_strikes:
                        if processed_count >= 50:  # Limit total requests to prevent timeout
                            break
                            
                        try:
                            option_detail = expiry_data['calls'][strike]
                            
                            # Create option contract for market data
                            option_contract = Contract()
                            option_contract.symbol = symbol
                            option_contract.secType = "OPT"
                            option_contract.exchange = option_detail.get('exchange', 'SMART')
                            option_contract.currency = currency
                            option_contract.lastTradeDateOrContractMonth = expiry
                            option_contract.strike = strike
                            option_contract.right = 'C'
                            
                            # Get option market data
                            option_market_data = self.ib_broker.get_market_data_snapshot(
                                option_contract, timeout=5
                            )
                            
                            if option_market_data:
                                vol_surface[expiry]['calls'][strike] = {
                                    'contract_details': option_detail,
                                    'market_data': option_market_data,
                                    'implied_vol': option_market_data.get('impliedVol'),
                                    'delta': option_market_data.get('delta'),
                                    'gamma': option_market_data.get('gamma'),
                                    'theta': option_market_data.get('theta'),
                                    'vega': option_market_data.get('vega')
                                }
                                processed_count += 1
                                
                        except Exception as e:
                            logger.warning(f"⚠️ Error processing call option {strike}: {e}")
                            continue
                    
                    # Process puts
                    put_strikes = sorted(list(expiry_data['puts'].keys()), reverse=True)
                    selected_put_strikes = put_strikes[:max_strikes//2] if len(put_strikes) > max_strikes//2 else put_strikes
                    
                    for strike in selected_put_strikes:
                        if processed_count >= 50:  # Limit total requests
                            break
                            
                        try:
                            option_detail = expiry_data['puts'][strike]
                            
                            # Create option contract for market data
                            option_contract = Contract()
                            option_contract.symbol = symbol
                            option_contract.secType = "OPT"
                            option_contract.exchange = option_detail.get('exchange', 'SMART')
                            option_contract.currency = currency
                            option_contract.lastTradeDateOrContractMonth = expiry
                            option_contract.strike = strike
                            option_contract.right = 'P'
                            
                            # Get option market data
                            option_market_data = self.ib_broker.get_market_data_snapshot(
                                option_contract, timeout=5
                            )
                            
                            if option_market_data:
                                vol_surface[expiry]['puts'][strike] = {
                                    'contract_details': option_detail,
                                    'market_data': option_market_data,
                                    'implied_vol': option_market_data.get('impliedVol'),
                                    'delta': option_market_data.get('delta'),
                                    'gamma': option_market_data.get('gamma'),
                                    'theta': option_market_data.get('theta'),
                                    'vega': option_market_data.get('vega')
                                }
                                processed_count += 1
                                
                        except Exception as e:
                            logger.warning(f"⚠️ Error processing put option {strike}: {e}")
                            continue
                
                result['volatility_surface'] = vol_surface
                logger.info(f"✅ Built volatility surface with {processed_count} option data points")
                
                # 7. Calculate summary statistics
                all_ivs = []
                for expiry_data in vol_surface.values():
                    for option_type_data in expiry_data.values():
                        for strike_data in option_type_data.values():
                            iv = strike_data.get('implied_vol')
                            if iv is not None and iv > 0:
                                all_ivs.append(iv)
                
                if all_ivs:
                    result['summary_stats'] = {
                        'total_options_processed': processed_count,
                        'total_expirations': len(vol_surface),
                        'avg_implied_vol': sum(all_ivs) / len(all_ivs),
                        'min_implied_vol': min(all_ivs),
                        'max_implied_vol': max(all_ivs),
                        'underlying_price': underlying_price
                    }
                    logger.info(f"📈 Average implied volatility: {result['summary_stats']['avg_implied_vol']:.2%}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error building volatility surface for {symbol}: {e}")
            return {
                'status': 'error',
                'message': f'Error: {str(e)}',
                'symbol': symbol,
                'timestamp': datetime.now().isoformat(),
                'error_messages': [str(e)]
            }
        
        finally:
            # Note: We don't disconnect here to allow for multiple calls
            # The user can call disconnect_from_ib() explicitly when done
            pass

    def get_esz6_options_futures_prices(self, timeout: int = 30) -> Dict[str, Any]:
        """
        Get options and futures prices for ESZ6 (E-mini S&P 500 December 2026).
        
        This function retrieves:
        1. ESZ6 futures contract details and current price
        2. Available options contracts on ESZ6 (if any)
        3. Market data for both futures and options
        
        Args:
            timeout: Timeout in seconds for requests
            
        Returns:
            Dictionary containing futures and options data for ESZ6
            
        Example:
            result = examples.get_esz6_options_futures_prices(timeout=20)
        """
        logger.info(f"\n=== ESZ6 Options & Futures Prices ===")
        
        if not self.connected:
            logger.info("Connecting to IB...")
            self.ib_broker.connect()
        
        result = {
            'status': 'success',
            'symbol': 'ESZ6',
            'timestamp': datetime.now().isoformat(),
            'futures_data': None,
            'options_data': [],
            'error_messages': []
        }
        
        try:
            # 1. Create ESZ6 futures contract
            logger.info("📊 Creating ESZ6 futures contract...")
            esz6_contract = Contract()
            esz6_contract.symbol = "ES"
            esz6_contract.secType = "FUT"
            esz6_contract.exchange = "CME"
            esz6_contract.currency = "USD"
            esz6_contract.lastTradeDateOrContractMonth = "202612"  # December 2026
            esz6_contract.multiplier = "50"
            esz6_contract.tradingClass = "ES"
            
            # 2. Get ESZ6 futures contract details
            logger.info("🔍 Fetching ESZ6 contract details...")
            futures_details = self.ib_broker.get_contract_details(esz6_contract, timeout=timeout)
            
            if futures_details:
                result['futures_data'] = {
                    'contract_details': futures_details,
                    'market_data': None,
                    'status': 'found'
                }
                
                # Log basic contract info
                if len(futures_details) > 0:
                    detail = futures_details[0]
                    logger.info(f"✅ Found ESZ6 contract:")
                    logger.info(f"  Contract: {detail.get('contract_summary', {}).get('localSymbol', 'ESZ26')}")
                    logger.info(f"  Exchange: {detail.get('contract_summary', {}).get('exchange', 'CME')}")
                    logger.info(f"  Last Trading Date: {detail.get('contract_summary', {}).get('lastTradeDateOrContractMonth', '202612')}")
                    logger.info(f"  Multiplier: {detail.get('contract_summary', {}).get('multiplier', '50')}")
                    
                    # 3. Get current market data for ESZ6
                    logger.info("💰 Fetching ESZ6 current market data...")
                    try:
                        market_data = self.ib_broker.get_market_data_snapshot(
                            esz6_contract,
                            timeout=timeout
                        )
                        
                        if market_data:
                            result['futures_data']['market_data'] = market_data
                            logger.info(f"✅ ESZ6 Market Data Retrieved:")
                            if 'bid' in market_data:
                                logger.info(f"  Bid: {market_data.get('bid', 'N/A')}")
                            if 'ask' in market_data:
                                logger.info(f"  Ask: {market_data.get('ask', 'N/A')}")
                            if 'last' in market_data:
                                logger.info(f"  Last: {market_data.get('last', 'N/A')}")
                            if 'volume' in market_data:
                                logger.info(f"  Volume: {market_data.get('volume', 'N/A')}")
                        else:
                            logger.warning("⚠️ No market data available for ESZ6")
                            result['futures_data']['market_data'] = {'status': 'no_data'}
                            
                    except Exception as market_error:
                        logger.error(f"❌ Error fetching ESZ6 market data: {market_error}")
                        result['futures_data']['market_data'] = {'status': 'error', 'message': str(market_error)}
                        result['error_messages'].append(f"Market data error: {market_error}")
            else:
                logger.warning("⚠️ No contract details found for ESZ6")
                result['futures_data'] = {'status': 'not_found', 'message': 'ESZ6 contract not found'}
                result['error_messages'].append("ESZ6 contract not found")
            
            # 4. Search for options on ESZ6
            logger.info("🔍 Searching for options contracts on ESZ6...")
            
            # Note: Options on futures typically use the underlying futures contract
            # For ES futures, options would be on the same contract structure
            option_search_patterns = [
                # Try different option contract patterns
                {"secType": "FOP", "exchange": "CME", "symbol": "ES", "lastTradeDateOrContractMonth": "202612"},
                {"secType": "OPT", "exchange": "CME", "symbol": "ESZ6"},
                {"secType": "OPT", "exchange": "GLOBEX", "symbol": "ES"}
            ]
            
            options_found = False
            
            for i, pattern in enumerate(option_search_patterns):
                try:
                    logger.info(f"  Pattern {i+1}: Searching for {pattern['secType']} options...")
                    
                    # Create option search contract
                    option_search = Contract()
                    option_search.symbol = pattern["symbol"]
                    option_search.secType = pattern["secType"]
                    option_search.exchange = pattern["exchange"]
                    option_search.currency = "USD"
                    if "lastTradeDateOrContractMonth" in pattern:
                        option_search.lastTradeDateOrContractMonth = pattern["lastTradeDateOrContractMonth"]
                    
                    # Get contract details for options
                    option_details = self.ib_broker.get_contract_details(option_search, timeout=timeout//3)
                    
                    if option_details and len(option_details) > 0:
                        logger.info(f"    ✅ Found {len(option_details)} option contracts with pattern {i+1}")
                        options_found = True
                        
                        # Add first few options to result (limit to avoid overwhelming output)
                        for j, opt_detail in enumerate(option_details[:5]):  # Limit to first 5 options
                            option_data = {
                                'pattern': i+1,
                                'contract_detail': opt_detail,
                                'market_data': None
                            }
                            
                            # Try to get market data for this option
                            try:
                                opt_contract = Contract()
                                opt_summary = opt_detail.get('contract_summary', {})
                                opt_contract.conId = opt_summary.get('conId')
                                opt_contract.symbol = opt_summary.get('symbol', pattern['symbol'])
                                opt_contract.secType = pattern['secType']
                                opt_contract.exchange = pattern['exchange']
                                opt_contract.currency = "USD"
                                
                                if opt_contract.conId:
                                    opt_market_data = self.ib_broker.get_market_data_snapshot(
                                        opt_contract, timeout=5
                                    )
                                    if opt_market_data:
                                        option_data['market_data'] = opt_market_data
                                        
                            except Exception as opt_market_error:
                                logger.debug(f"Could not get market data for option {j}: {opt_market_error}")
                                option_data['market_data'] = {'status': 'error', 'message': str(opt_market_error)}
                            
                            result['options_data'].append(option_data)
                            
                        # Log summary of found options
                        logger.info(f"    Added {min(len(option_details), 5)} options to result")
                        if len(option_details) > 5:
                            logger.info(f"    (Total {len(option_details)} options available - showing first 5)")
                    else:
                        logger.info(f"    🟡 No options found with pattern {i+1}")
                        
                except Exception as option_error:
                    logger.debug(f"  Error searching options pattern {i+1}: {option_error}")
                    result['error_messages'].append(f"Options search pattern {i+1}: {option_error}")
            
            if not options_found:
                logger.info("🟡 No options contracts found for ESZ6")
                result['options_data'] = []
                result['error_messages'].append("No options found - options on ES futures may require special permissions or may not be available for this expiry")
            
            # 5. Summary
            futures_status = "✅" if result['futures_data'] and result['futures_data']['status'] == 'found' else "❌"
            options_count = len(result['options_data'])
            options_status = "✅" if options_count > 0 else "🟡"
            
            logger.info(f"\n📋 Summary:")
            logger.info(f"  {futures_status} ESZ6 Futures: {result['futures_data']['status'] if result['futures_data'] else 'not found'}")
            logger.info(f"  {options_status} ESZ6 Options: {options_count} contracts found")
            
            if result['error_messages']:
                logger.info(f"  ⚠️ Errors: {len(result['error_messages'])} issues encountered")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error retrieving ESZ6 options/futures data: {e}")
            result['status'] = 'error'
            result['error_messages'].append(f"General error: {str(e)}")
            return result
        
        finally:
            # Note: We don't disconnect here to allow for multiple calls
            # The user can call disconnect_from_ib() explicitly when done
            pass


def main():
    """
    Main entry point for running the comprehensive IB market data examples.
    
    Usage:
        python comprehensive_market_data_examples.py                # Run all examples
        python comprehensive_market_data_examples.py test          # Run access level test pipeline
        python comprehensive_market_data_examples.py comprehensive # Run comprehensive market access test
        python comprehensive_market_data_examples.py ticks         # Run comprehensive tick access test
        python comprehensive_market_data_examples.py volsurf       # Test volatility surface for AAPL stock options
        python comprehensive_market_data_examples.py help          # Show help
    """
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == 'test':
            # Run access level test pipeline only
            examples = ComprehensiveIBMarketDataExamples()
            examples.test_access_level_pipeline()
        elif sys.argv[1] == 'comprehensive':
            # Run comprehensive market access test
            examples = ComprehensiveIBMarketDataExamples()
            results = examples.test_comprehensive_market_access()
            return results
        elif sys.argv[1] == 'ticks':
            # Run comprehensive tick access test
            examples = ComprehensiveIBMarketDataExamples()
            results = examples.test_comprehensive_tick_access()
            return results
        elif sys.argv[1] == 'conid':
            # Test get_by_conid function with example CONIDs
            examples = ComprehensiveIBMarketDataExamples()
            
            # Example CONIDs (these are real Interactive Brokers CONIDs)
            test_conids = [
                265598,    # AAPL (Apple Inc.)
                756733,    # SPY (SPDR S&P 500 ETF)
                270639     # MSFT (Microsoft Corp.)
            ]
            
            print("\n=== Testing get_by_conid function ===")
            print("Note: Requires active IB connection and market data permissions")
            
            for conid in test_conids:
                print(f"\nTesting CONID: {conid}")
                result = examples.get_by_conid(conid, get_market_data=True, timeout=10)
                
                if result['status'] == 'success' and result['contract_details']:
                    detail = result['contract_details'][0]
                    print(f"  ✅ {detail.get('symbol', 'N/A')} ({detail.get('sec_type', 'N/A')}) on {detail.get('exchange', 'N/A')}")
                    if result.get('market_data') and 'last' in result['market_data']:
                        print(f"     Last Price: {result['market_data']['last']}")
                elif result['status'] == 'error':
                    print(f"  ❌ Error: {result.get('message', 'Unknown error')}")
                elif result['status'] == 'not_found':
                    print(f"  ⚠️ Contract not found: {result.get('message', 'No details')}")
            
            return
        elif sys.argv[1] == 'esz6':
            # Test get_esz6_options_futures_prices function
            examples = ComprehensiveIBMarketDataExamples()
            
            print("\n=== Testing ESZ6 Options & Futures Prices ===")
            print("Note: Requires active IB connection, futures permissions, and market data subscriptions")
            
            result = examples.get_esz6_options_futures_prices(timeout=30)
            
            if result['status'] == 'success':
                print(f"\n✅ ESZ6 Data Retrieved Successfully")
                
                # Display futures data
                if result['futures_data'] and result['futures_data']['status'] == 'found':
                    print(f"\n📊 ESZ6 Futures:")
                    futures_market = result['futures_data']['market_data']
                    if futures_market and futures_market.get('last'):
                        print(f"  Last Price: {futures_market['last']}")
                        print(f"  Bid/Ask: {futures_market.get('bid', 'N/A')} / {futures_market.get('ask', 'N/A')}")
                        if 'volume' in futures_market:
                            print(f"  Volume: {futures_market['volume']}")
                    else:
                        print(f"  Status: Contract found but no current market data")
                else:
                    print(f"\n❌ ESZ6 Futures: Not found or error")
                
                # Display options data
                options_count = len(result['options_data'])
                if options_count > 0:
                    print(f"\n📋 ESZ6 Options: Found {options_count} contracts")
                    for i, option in enumerate(result['options_data'][:3], 1):  # Show first 3
                        opt_detail = option['contract_detail']
                        opt_summary = opt_detail.get('contract_summary', {})
                        print(f"  Option {i}: {opt_summary.get('localSymbol', 'N/A')}")
                        if option['market_data'] and isinstance(option['market_data'], dict) and option['market_data'].get('last'):
                            print(f"    Price: {option['market_data']['last']}")
                    if options_count > 3:
                        print(f"  ... and {options_count - 3} more options")
                else:
                    print(f"\n🟡 ESZ6 Options: No options contracts found")
                
                # Display any errors
                if result['error_messages']:
                    print(f"\n⚠️ Issues encountered ({len(result['error_messages'])}):")
                    for error in result['error_messages'][:3]:  # Show first 3 errors
                        print(f"  - {error}")
                    if len(result['error_messages']) > 3:
                        print(f"  ... and {len(result['error_messages']) - 3} more issues")
                        
            elif result['status'] == 'error':
                print(f"❌ Error retrieving ESZ6 data: {result.get('error_messages', ['Unknown error'])[0]}")
            
            return
        elif sys.argv[1] == 'volsurf':
            # Test get_volatility_surface function
            examples = ComprehensiveIBMarketDataExamples()
            
            print("\n=== Testing Volatility Surface for AAPL ===")
            print("Note: Requires active IB connection, options permissions, and market data subscriptions")
            
            result = examples.get_volatility_surface("AAPL", "STK", "SMART", "USD", 
                                                   get_implied_volatility=True, 
                                                   max_strikes=10, max_expirations=3, 
                                                   timeout=30)
            
            if result['status'] == 'success':
                print(f"\n✅ Volatility Surface Built Successfully for {result['symbol']}")
                
                # Display underlying data
                if result['underlying_data'] and result['underlying_data'].get('market_data'):
                    underlying_price = result['underlying_data']['market_data'].get('last')
                    print(f"\n📊 Underlying ({result['symbol']}):")
                    print(f"  Current Price: ${underlying_price}" if underlying_price else "  Price: Not available")
                
                # Display options chains summary
                total_chains = len(result['options_chains'])
                print(f"\n📈 Options Chains: {total_chains} expirations found")
                
                # Display volatility surface summary
                if result.get('summary_stats'):
                    stats = result['summary_stats']
                    print(f"\n🌊 Volatility Surface Summary:")
                    print(f"  Options Processed: {stats.get('total_options_processed', 0)}")
                    print(f"  Expirations: {stats.get('total_expirations', 0)}")
                    print(f"  Avg Implied Vol: {stats.get('avg_implied_vol', 0):.2%}")
                    print(f"  Vol Range: {stats.get('min_implied_vol', 0):.2%} - {stats.get('max_implied_vol', 0):.2%}")
                
                # Display sample volatility data
                if result.get('volatility_surface'):
                    print(f"\n📋 Sample Volatility Data:")
                    sample_count = 0
                    for expiry, expiry_data in list(result['volatility_surface'].items())[:2]:
                        print(f"\n  Expiry: {expiry}")
                        
                        # Show sample calls
                        calls = expiry_data.get('calls', {})
                        if calls:
                            print(f"    Calls:")
                            for strike, call_data in list(calls.items())[:3]:
                                iv = call_data.get('implied_vol')
                                if iv:
                                    print(f"      Strike ${strike}: IV {iv:.2%}")
                                    sample_count += 1
                        
                        # Show sample puts  
                        puts = expiry_data.get('puts', {})
                        if puts:
                            print(f"    Puts:")
                            for strike, put_data in list(puts.items())[:3]:
                                iv = put_data.get('implied_vol')
                                if iv:
                                    print(f"      Strike ${strike}: IV {iv:.2%}")
                                    sample_count += 1
                        
                        if sample_count >= 10:  # Limit output
                            break
                
                # Display any error messages
                if result.get('error_messages'):
                    print(f"\n⚠️ Issues encountered ({len(result['error_messages'])}):")
                    for error in result['error_messages'][:3]:  # Show first 3 errors
                        print(f"  - {error}")
                        
            elif result['status'] == 'error':
                print(f"❌ Error building volatility surface: {result.get('message', 'Unknown error')}")
            elif result['status'] == 'partial':
                print(f"🟡 Partial success: {result.get('error_messages', ['Unknown issue'])[0]}")
            
            return
        elif sys.argv[1] == 'help':
            print("Usage:")
            print("  python comprehensive_market_data_examples.py              # Run all examples")
            print("  python comprehensive_market_data_examples.py test         # Run access level test pipeline") 
            print("  python comprehensive_market_data_examples.py comprehensive # Run comprehensive market access test")
            print("  python comprehensive_market_data_examples.py ticks        # Run comprehensive tick access test")
            print("  python comprehensive_market_data_examples.py conid        # Test get_by_conid function with example CONIDs")
            print("  python comprehensive_market_data_examples.py esz6         # Test ESZ6 options & futures prices")
            print("  python comprehensive_market_data_examples.py volsurf      # Test volatility surface for AAPL stock options")
            print("  python comprehensive_market_data_examples.py help         # Show this help")
            return
    else:
        # Run all examples
        examples = ComprehensiveIBMarketDataExamples()
        examples.run_all_examples()










