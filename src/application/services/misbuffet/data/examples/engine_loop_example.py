"""
Example of how the trading engine uses MarketDataService to generate data slices.
This demonstrates the engine's main loop for both backtest and live trading scenarios.
"""

from datetime import datetime, timedelta
from typing import List, Optional
import time

from ..data_loader import DataLoader, create_backtest_data_services, create_live_trading_data_services
from ..market_data_service import MarketDataService
from ..market_data_history_service import MarketDataHistoryService
from ...common.data_types import Slice
from ...common.symbol import Symbol


class TradingEngine:
    """
    Example trading engine that uses MarketDataService to get market data slices.
    This represents the core engine that orchestrates data flow to algorithms.
    """
    
    def __init__(self, market_data_service: MarketDataService, 
                 history_service: MarketDataHistoryService):
        self.market_data_service = market_data_service
        self.history_service = history_service
        self.algorithms = []  # List of algorithms to notify
        self.is_running = False
        
        # Engine statistics
        self.slices_processed = 0
        self.algorithms_notified = 0
        self.errors = 0
    
    def add_algorithm(self, algorithm):
        """Add an algorithm to receive data updates."""
        self.algorithms.append(algorithm)
    
    def remove_algorithm(self, algorithm):
        """Remove an algorithm from receiving data updates."""
        if algorithm in self.algorithms:
            self.algorithms.remove(algorithm)
    
    def run_backtest(self, symbols: List[str], time_step: timedelta = timedelta(minutes=1)):
        """
        Run the engine in backtest mode, stepping through time and generating slices.
        
        Args:
            symbols: List of symbol strings to subscribe to
            time_step: Time increment for each step
        """
        self.is_running = True
        
        try:
            # Add symbols to market data service
            for symbol_str in symbols:
                symbol = self.market_data_service.resolve_symbol(symbol_str)
                if symbol:
                    self.market_data_service.add_symbol(symbol)
                    print(f"Added symbol: {symbol}")
                else:
                    print(f"Warning: Could not resolve symbol: {symbol_str}")
            
            print(f"Starting backtest engine loop with {len(symbols)} symbols")
            current_time = self.market_data_service.current_time
            
            while self.is_running:
                # Advance time and get new data slice
                slice_obj = self.market_data_service.advance_time(current_time)
                
                if slice_obj and slice_obj.has_data:
                    self.slices_processed += 1
                    print(f"Processing slice at {slice_obj.time} with {len(slice_obj.keys())} symbols")
                    
                    # Notify all algorithms
                    self._notify_algorithms(slice_obj)
                    
                    # Check if we should continue
                    if self.slices_processed % 100 == 0:
                        print(f"Processed {self.slices_processed} slices so far...")
                        stats = self.market_data_service.get_statistics()
                        print(f"Market data service stats: {stats}")
                
                # Advance to next time step
                current_time += time_step
                
                # Add some realistic delay for demonstration
                time.sleep(0.001)  # 1ms delay
                
                # Stop condition for example (in real implementation, this would be end of data)
                if self.slices_processed >= 1000:  # Stop after 1000 slices for demo
                    print("Stopping demo after 1000 slices")
                    break
        
        except KeyboardInterrupt:
            print("Backtest interrupted by user")
        except Exception as e:
            self.errors += 1
            print(f"Error in backtest loop: {e}")
        finally:
            self.is_running = False
            print(f"Backtest completed. Processed {self.slices_processed} slices")
    
    def run_live_trading(self, symbols: List[str], update_interval: float = 1.0):
        """
        Run the engine in live trading mode, continuously getting real-time data.
        
        Args:
            symbols: List of symbol strings to subscribe to
            update_interval: Seconds between data updates
        """
        self.is_running = True
        
        try:
            # Add symbols to market data service
            for symbol_str in symbols:
                symbol = self.market_data_service.resolve_symbol(symbol_str)
                if symbol:
                    self.market_data_service.add_symbol(symbol)
                    print(f"Subscribed to live data for: {symbol}")
                else:
                    print(f"Warning: Could not resolve symbol: {symbol_str}")
            
            print(f"Starting live trading engine loop with {len(symbols)} symbols")
            
            while self.is_running:
                # Get current data slice
                slice_obj = self.market_data_service.get_current_slice()
                
                if slice_obj and slice_obj.has_data:
                    self.slices_processed += 1
                    print(f"Live slice at {slice_obj.time} with {len(slice_obj.keys())} symbols")
                    
                    # Notify all algorithms
                    self._notify_algorithms(slice_obj)
                
                # Wait for next update
                time.sleep(update_interval)
                
                # Periodic status updates
                if self.slices_processed % 60 == 0:  # Every 60 slices
                    print(f"Live trading: processed {self.slices_processed} slices")
        
        except KeyboardInterrupt:
            print("Live trading interrupted by user")
        except Exception as e:
            self.errors += 1
            print(f"Error in live trading loop: {e}")
        finally:
            self.is_running = False
            print(f"Live trading stopped. Processed {self.slices_processed} slices")
    
    def _notify_algorithms(self, slice_obj: Slice):
        """Notify all algorithms of new data."""
        for algorithm in self.algorithms:
            try:
                # In a real implementation, this would call the algorithm's OnData method
                if hasattr(algorithm, 'on_data'):
                    algorithm.on_data(slice_obj)
                elif hasattr(algorithm, 'OnData'):
                    algorithm.OnData(slice_obj)
                else:
                    print(f"Warning: Algorithm {algorithm} has no on_data or OnData method")
                
                self.algorithms_notified += 1
                
            except Exception as e:
                self.errors += 1
                print(f"Error notifying algorithm {algorithm}: {e}")
    
    def stop(self):
        """Stop the engine."""
        self.is_running = False
        print("Engine stop requested")
    
    def get_statistics(self):
        """Get engine statistics."""
        return {
            'slices_processed': self.slices_processed,
            'algorithms_notified': self.algorithms_notified,
            'errors': self.errors,
            'is_running': self.is_running,
            'active_algorithms': len(self.algorithms)
        }


class MockAlgorithm:
    """Mock algorithm for demonstration purposes."""
    
    def __init__(self, name: str):
        self.name = name
        self.data_received = 0
    
    def on_data(self, slice_obj: Slice):
        """Handle new market data."""
        self.data_received += 1
        
        # Print occasional updates
        if self.data_received % 50 == 0:
            print(f"Algorithm {self.name}: received {self.data_received} data slices")
        
        # Example of accessing data from slice
        for symbol in slice_obj.keys():
            data = slice_obj[symbol]
            if data:
                # In a real algorithm, this is where trading logic would go
                pass


def run_backtest_example():
    """Example of running a backtest engine loop."""
    print("=== Backtest Engine Loop Example ===")
    
    try:
        # Initialize data services for backtest
        start_time = datetime(2023, 1, 1)
        end_time = datetime(2023, 1, 31)
        
        services = create_backtest_data_services(
            data_folder="/path/to/historical/data",
            start_time=start_time,
            end_time=end_time
        )
        
        # Create trading engine
        engine = TradingEngine(
            services.market_data_service,
            services.history_service
        )
        
        # Add some mock algorithms
        algo1 = MockAlgorithm("MomentumStrategy")
        algo2 = MockAlgorithm("MeanReversionStrategy")
        
        engine.add_algorithm(algo1)
        engine.add_algorithm(algo2)
        
        # Define symbols to trade
        symbols = ["AAPL", "GOOGL", "MSFT", "TSLA"]
        
        # Run the backtest
        engine.run_backtest(symbols, time_step=timedelta(minutes=5))
        
        # Print final statistics
        print("\nFinal Engine Statistics:")
        print(engine.get_statistics())
        
        print("\nAlgorithm Statistics:")
        print(f"Algorithm {algo1.name}: {algo1.data_received} data points")
        print(f"Algorithm {algo2.name}: {algo2.data_received} data points")
        
    except Exception as e:
        print(f"Backtest example failed: {e}")


def run_live_trading_example():
    """Example of running a live trading engine loop."""
    print("=== Live Trading Engine Loop Example ===")
    
    try:
        # Initialize data services for live trading
        services = create_live_trading_data_services()
        
        # Create trading engine
        engine = TradingEngine(
            services.market_data_service,
            services.history_service
        )
        
        # Add a mock algorithm
        algo = MockAlgorithm("LiveTradingStrategy")
        engine.add_algorithm(algo)
        
        # Define symbols to trade
        symbols = ["SPY", "QQQ", "IWM"]
        
        # Run live trading (this would run indefinitely in a real scenario)
        print("Starting live trading for 30 seconds...")
        import threading
        
        # Start engine in a separate thread
        engine_thread = threading.Thread(
            target=engine.run_live_trading,
            args=(symbols, 1.0)  # 1 second updates
        )
        engine_thread.daemon = True
        engine_thread.start()
        
        # Let it run for 30 seconds
        time.sleep(30)
        
        # Stop the engine
        engine.stop()
        engine_thread.join(timeout=5)
        
        # Print final statistics
        print("\nFinal Engine Statistics:")
        print(engine.get_statistics())
        print(f"Algorithm {algo.name}: {algo.data_received} data points")
        
    except Exception as e:
        print(f"Live trading example failed: {e}")


def run_advanced_example():
    """Advanced example showing engine with custom data handling."""
    print("=== Advanced Engine Loop Example ===")
    
    try:
        # Initialize with custom configuration
        loader = DataLoader()
        services = loader.load_for_backtest(
            data_folder="/path/to/data",
            start_time=datetime(2023, 6, 1),
            end_time=datetime(2023, 6, 30),
            database_type='sqlite'
        )
        
        engine = TradingEngine(services.market_data_service, services.history_service)
        
        # Custom algorithm with more sophisticated logic
        class AdvancedAlgorithm:
            def __init__(self, name: str, history_service: MarketDataHistoryService):
                self.name = name
                self.history_service = history_service
                self.positions = {}
                self.trades = 0
            
            def on_data(self, slice_obj: Slice):
                """More sophisticated data handling."""
                for symbol in slice_obj.keys():
                    current_data = slice_obj[symbol]
                    if current_data and hasattr(current_data, 'close'):
                        # Get some historical data for decision making
                        history = self.history_service.get_history(symbol, 20)  # 20 periods
                        
                        if len(history) >= 20:
                            # Simple moving average strategy
                            recent_prices = [h.close for h in history[-10:]]
                            avg_price = sum(recent_prices) / len(recent_prices)
                            
                            current_price = current_data.close
                            
                            # Simple trading logic
                            if current_price > avg_price * 1.02:  # 2% above average
                                if symbol not in self.positions:
                                    print(f"{self.name}: BUY signal for {symbol} at {current_price}")
                                    self.positions[symbol] = current_price
                                    self.trades += 1
                            
                            elif current_price < avg_price * 0.98:  # 2% below average
                                if symbol in self.positions:
                                    entry_price = self.positions[symbol]
                                    profit = current_price - entry_price
                                    print(f"{self.name}: SELL signal for {symbol} at {current_price}, P&L: {profit:.2f}")
                                    del self.positions[symbol]
                                    self.trades += 1
        
        # Add advanced algorithm
        advanced_algo = AdvancedAlgorithm("AdvancedStrategy", services.history_service)
        engine.add_algorithm(advanced_algo)
        
        # Run with fewer symbols for this example
        symbols = ["AAPL", "MSFT"]
        engine.run_backtest(symbols, time_step=timedelta(hours=1))  # Hourly data
        
        print(f"\nAdvanced Algorithm Results:")
        print(f"Trades executed: {advanced_algo.trades}")
        print(f"Final positions: {advanced_algo.positions}")
        
        # Clean up
        loader.dispose()
        
    except Exception as e:
        print(f"Advanced example failed: {e}")


if __name__ == "__main__":
    print("Market Data Service Engine Loop Examples")
    print("========================================")
    
    # Run examples
    run_backtest_example()
    print("\n" + "="*50 + "\n")
    
    # Uncomment to run live trading example
    # run_live_trading_example()
    # print("\n" + "="*50 + "\n")
    
    run_advanced_example()
    
    print("\nAll examples completed!")