"""
Example of how algorithms use MarketDataHistoryService to query historical data safely.
This demonstrates how trading algorithms can access historical data while respecting
the frontier to prevent look-ahead bias.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional
from abc import ABC, abstractmethod

from ..market_data_history_service import MarketDataHistoryService
from ...common.data_types import Slice, BaseData, TradeBar
from ...common.symbol import Symbol
from ...common.enums import Resolution


class BaseAlgorithm(ABC):
    """
    Base class for all trading algorithms.
    Provides common functionality and interface for accessing historical data.
    """
    
    def __init__(self, name: str, history_service: MarketDataHistoryService):
        self.name = name
        self.history_service = history_service
        
        # Algorithm state
        self.current_time: Optional[datetime] = None
        self.portfolio = {}
        self.trades = []
        
        # Statistics
        self.data_points_processed = 0
        self.trades_executed = 0
        self.history_requests = 0
    
    @abstractmethod
    def on_data(self, slice_obj: Slice):
        """Handle new market data. Must be implemented by subclasses."""
        pass
    
    def get_history(self, symbol: str, periods: int, 
                   resolution: Resolution = Resolution.DAILY) -> List[BaseData]:
        """
        Get historical data for a symbol, respecting the frontier.
        
        Args:
            symbol: Symbol string
            periods: Number of periods to retrieve
            resolution: Data resolution
            
        Returns:
            List of historical data points
        """
        self.history_requests += 1
        
        try:
            history = self.history_service.get_history(symbol, periods, resolution)
            print(f"Algorithm {self.name}: Retrieved {len(history)} historical data points for {symbol}")
            return history
            
        except Exception as e:
            print(f"Algorithm {self.name}: Error getting history for {symbol}: {e}")
            return []
    
    def get_history_range(self, symbol: str, start: datetime, end: datetime,
                         resolution: Resolution = Resolution.DAILY) -> List[BaseData]:
        """
        Get historical data for a specific date range.
        
        Args:
            symbol: Symbol string
            start: Start date
            end: End date (will be capped at frontier)
            resolution: Data resolution
            
        Returns:
            List of historical data points
        """
        self.history_requests += 1
        
        try:
            history = self.history_service.get_history_range(symbol, start, end, resolution)
            print(f"Algorithm {self.name}: Retrieved {len(history)} historical data points for {symbol} from {start} to {end}")
            return history
            
        except Exception as e:
            print(f"Algorithm {self.name}: Error getting history range for {symbol}: {e}")
            return []
    
    def can_access_time(self, time: datetime) -> bool:
        """Check if we can access data at the given time."""
        return self.history_service.can_access_time(time)
    
    def get_frontier_time(self) -> Optional[datetime]:
        """Get current frontier time."""
        return self.history_service.get_frontier_time()
    
    def execute_trade(self, symbol: str, quantity: int, price: float, trade_type: str):
        """Execute a trade (mock implementation)."""
        trade = {
            'symbol': symbol,
            'quantity': quantity,
            'price': price,
            'type': trade_type,
            'timestamp': self.current_time,
            'algorithm': self.name
        }
        
        self.trades.append(trade)
        self.trades_executed += 1
        
        print(f"Algorithm {self.name}: {trade_type} {quantity} shares of {symbol} at ${price:.2f}")


class MovingAverageAlgorithm(BaseAlgorithm):
    """
    Simple moving average crossover algorithm.
    Demonstrates basic historical data usage for technical analysis.
    """
    
    def __init__(self, name: str, history_service: MarketDataHistoryService,
                 short_window: int = 10, long_window: int = 30):
        super().__init__(name, history_service)
        self.short_window = short_window
        self.long_window = long_window
        self.positions = {}  # Track current positions
    
    def on_data(self, slice_obj: Slice):
        """Process new market data using moving average strategy."""
        self.current_time = slice_obj.time
        self.data_points_processed += 1
        
        for symbol in slice_obj.keys():
            current_data = slice_obj[symbol]
            
            if current_data and hasattr(current_data, 'close'):
                self._process_symbol(symbol.value if hasattr(symbol, 'value') else str(symbol), 
                                   current_data.close)
    
    def _process_symbol(self, symbol: str, current_price: float):
        """Process a single symbol with moving average logic."""
        try:
            # Get historical data for moving averages
            # We need long_window + 1 periods to calculate both averages
            history = self.get_history(symbol, self.long_window + 1, Resolution.DAILY)
            
            if len(history) < self.long_window:
                print(f"Not enough history for {symbol}: need {self.long_window}, got {len(history)}")
                return
            
            # Extract closing prices
            closes = [float(data.close) if hasattr(data, 'close') else float(data.value) 
                     for data in history]
            
            # Calculate moving averages
            short_ma = sum(closes[-self.short_window:]) / self.short_window
            long_ma = sum(closes[-self.long_window:]) / self.long_window
            
            # Previous values for crossover detection
            if len(closes) > self.long_window:
                prev_short_ma = sum(closes[-(self.short_window+1):-1]) / self.short_window
                prev_long_ma = sum(closes[-(self.long_window+1):-1]) / self.long_window
            else:
                prev_short_ma = short_ma
                prev_long_ma = long_ma
            
            print(f"{symbol}: Short MA={short_ma:.2f}, Long MA={long_ma:.2f}, Price={current_price:.2f}")
            
            # Trading logic
            is_long = symbol in self.positions and self.positions[symbol] > 0
            
            # Golden cross: short MA crosses above long MA (buy signal)
            if (short_ma > long_ma and prev_short_ma <= prev_long_ma and not is_long):
                self.execute_trade(symbol, 100, current_price, "BUY")
                self.positions[symbol] = 100
            
            # Death cross: short MA crosses below long MA (sell signal)
            elif (short_ma < long_ma and prev_short_ma >= prev_long_ma and is_long):
                self.execute_trade(symbol, -100, current_price, "SELL")
                self.positions[symbol] = 0
                
        except Exception as e:
            print(f"Error processing {symbol}: {e}")


class MeanReversionAlgorithm(BaseAlgorithm):
    """
    Mean reversion algorithm that uses historical volatility and price levels.
    Demonstrates more sophisticated historical data analysis.
    """
    
    def __init__(self, name: str, history_service: MarketDataHistoryService,
                 lookback_period: int = 20, volatility_threshold: float = 2.0):
        super().__init__(name, history_service)
        self.lookback_period = lookback_period
        self.volatility_threshold = volatility_threshold
        self.positions = {}
        self.entry_prices = {}
    
    def on_data(self, slice_obj: Slice):
        """Process new data using mean reversion strategy."""
        self.current_time = slice_obj.time
        self.data_points_processed += 1
        
        for symbol in slice_obj.keys():
            current_data = slice_obj[symbol]
            
            if current_data and hasattr(current_data, 'close'):
                self._process_mean_reversion(symbol.value if hasattr(symbol, 'value') else str(symbol),
                                           current_data.close)
    
    def _process_mean_reversion(self, symbol: str, current_price: float):
        """Apply mean reversion logic to a symbol."""
        try:
            # Get historical data for statistical analysis
            history = self.get_history(symbol, self.lookback_period, Resolution.DAILY)
            
            if len(history) < self.lookback_period:
                return
            
            # Extract prices and calculate statistics
            prices = [float(data.close) if hasattr(data, 'close') else float(data.value) 
                     for data in history]
            
            mean_price = sum(prices) / len(prices)
            squared_diffs = [(p - mean_price) ** 2 for p in prices]
            std_dev = (sum(squared_diffs) / len(squared_diffs)) ** 0.5
            
            # Calculate z-score
            z_score = (current_price - mean_price) / std_dev if std_dev > 0 else 0
            
            print(f"{symbol}: Mean=${mean_price:.2f}, StdDev=${std_dev:.2f}, Z-Score={z_score:.2f}")
            
            current_position = self.positions.get(symbol, 0)
            
            # Mean reversion signals
            if z_score < -self.volatility_threshold and current_position == 0:
                # Price is significantly below mean - buy signal
                self.execute_trade(symbol, 100, current_price, "BUY")
                self.positions[symbol] = 100
                self.entry_prices[symbol] = current_price
                
            elif z_score > self.volatility_threshold and current_position == 0:
                # Price is significantly above mean - short signal
                self.execute_trade(symbol, -100, current_price, "SHORT")
                self.positions[symbol] = -100
                self.entry_prices[symbol] = current_price
                
            elif abs(z_score) < 0.5 and current_position != 0:
                # Price has reverted to mean - close position
                if current_position > 0:
                    profit = (current_price - self.entry_prices[symbol]) * current_position
                    self.execute_trade(symbol, -current_position, current_price, "SELL")
                else:
                    profit = (self.entry_prices[symbol] - current_price) * abs(current_position)
                    self.execute_trade(symbol, -current_position, current_price, "COVER")
                
                print(f"{symbol}: Position closed, P&L: ${profit:.2f}")
                self.positions[symbol] = 0
                
        except Exception as e:
            print(f"Error in mean reversion for {symbol}: {e}")


class PairsTradingAlgorithm(BaseAlgorithm):
    """
    Pairs trading algorithm that analyzes relationships between multiple symbols.
    Demonstrates advanced historical data usage for statistical arbitrage.
    """
    
    def __init__(self, name: str, history_service: MarketDataHistoryService,
                 symbol_pairs: List[tuple], lookback_period: int = 30):
        super().__init__(name, history_service)
        self.symbol_pairs = symbol_pairs  # List of (symbol1, symbol2) tuples
        self.lookback_period = lookback_period
        self.positions = {}
        self.spread_stats = {}
    
    def on_data(self, slice_obj: Slice):
        """Process pairs trading signals."""
        self.current_time = slice_obj.time
        self.data_points_processed += 1
        
        # Only process if we have data for symbols in our pairs
        available_symbols = set(str(s) for s in slice_obj.keys())
        
        for symbol1, symbol2 in self.symbol_pairs:
            if symbol1 in available_symbols and symbol2 in available_symbols:
                data1 = slice_obj[symbol1]
                data2 = slice_obj[symbol2]
                
                if (data1 and data2 and 
                    hasattr(data1, 'close') and hasattr(data2, 'close')):
                    self._process_pair(symbol1, symbol2, data1.close, data2.close)
    
    def _process_pair(self, symbol1: str, symbol2: str, price1: float, price2: float):
        """Analyze and trade a pair of symbols."""
        try:
            pair_key = f"{symbol1}-{symbol2}"
            
            # Get historical data for both symbols
            history1 = self.get_history(symbol1, self.lookback_period, Resolution.DAILY)
            history2 = self.get_history(symbol2, self.lookback_period, Resolution.DAILY)
            
            if (len(history1) < self.lookback_period or 
                len(history2) < self.lookback_period):
                return
            
            # Calculate historical price spread
            spreads = []
            for h1, h2 in zip(history1, history2):
                p1 = float(h1.close) if hasattr(h1, 'close') else float(h1.value)
                p2 = float(h2.close) if hasattr(h2, 'close') else float(h2.value)
                spread = p1 - p2
                spreads.append(spread)
            
            # Calculate spread statistics
            mean_spread = sum(spreads) / len(spreads)
            squared_diffs = [(s - mean_spread) ** 2 for s in spreads]
            std_spread = (sum(squared_diffs) / len(squared_diffs)) ** 0.5
            
            # Current spread and z-score
            current_spread = price1 - price2
            z_score = (current_spread - mean_spread) / std_spread if std_spread > 0 else 0
            
            print(f"Pair {pair_key}: Spread={current_spread:.2f}, Mean={mean_spread:.2f}, Z-Score={z_score:.2f}")
            
            current_position = self.positions.get(pair_key, 0)
            
            # Pairs trading logic
            if z_score > 2.0 and current_position == 0:
                # Spread is too high - short symbol1, long symbol2
                self.execute_trade(symbol1, -100, price1, "SHORT")
                self.execute_trade(symbol2, 100, price2, "BUY")
                self.positions[pair_key] = -1
                print(f"Pairs trade: SHORT {symbol1}, LONG {symbol2}")
                
            elif z_score < -2.0 and current_position == 0:
                # Spread is too low - long symbol1, short symbol2
                self.execute_trade(symbol1, 100, price1, "BUY")
                self.execute_trade(symbol2, -100, price2, "SHORT")
                self.positions[pair_key] = 1
                print(f"Pairs trade: LONG {symbol1}, SHORT {symbol2}")
                
            elif abs(z_score) < 0.5 and current_position != 0:
                # Spread has normalized - close positions
                if current_position > 0:
                    self.execute_trade(symbol1, -100, price1, "SELL")
                    self.execute_trade(symbol2, 100, price2, "COVER")
                else:
                    self.execute_trade(symbol1, 100, price1, "COVER")
                    self.execute_trade(symbol2, -100, price2, "SELL")
                
                self.positions[pair_key] = 0
                print(f"Pairs trade closed for {pair_key}")
                
        except Exception as e:
            print(f"Error processing pair {symbol1}-{symbol2}: {e}")


def demonstrate_frontier_enforcement():
    """
    Demonstrate how the frontier prevents look-ahead bias.
    """
    print("=== Frontier Enforcement Demonstration ===")
    
    from ..data_loader import create_backtest_data_services
    
    try:
        # Create services for backtest
        services = create_backtest_data_services(
            data_folder="/path/to/data",
            start_time=datetime(2023, 1, 1),
            end_time=datetime(2023, 1, 31)
        )
        
        history_service = services.history_service
        
        print(f"Initial frontier: {history_service.get_frontier_time()}")
        
        # Try to access future data (should fail or return limited data)
        future_time = datetime(2023, 6, 1)
        
        print(f"Can access future time {future_time}? {history_service.can_access_time(future_time)}")
        
        # Get historical data respecting frontier
        current_history = history_service.get_history("AAPL", 10, Resolution.DAILY)
        print(f"Historical data points retrieved: {len(current_history)}")
        
        if current_history:
            latest_data_time = max(data.time for data in current_history)
            print(f"Latest data timestamp: {latest_data_time}")
            print(f"Is latest data before frontier? {latest_data_time <= history_service.get_frontier_time()}")
        
        # Simulate advancing time
        new_time = datetime(2023, 1, 15)
        if hasattr(history_service, '_advance_frontier'):
            history_service._advance_frontier(new_time)
            print(f"Advanced frontier to: {history_service.get_frontier_time()}")
        
    except Exception as e:
        print(f"Frontier demonstration failed: {e}")


def run_algorithm_examples():
    """Run examples of different algorithms using the history service."""
    print("=== Algorithm Usage Examples ===")
    
    from ..data_loader import create_backtest_data_services
    from ..examples.engine_loop_example import TradingEngine
    
    try:
        # Initialize services
        services = create_backtest_data_services(
            data_folder="/path/to/data",
            start_time=datetime(2023, 1, 1),
            end_time=datetime(2023, 3, 31)
        )
        
        # Create algorithms
        ma_algo = MovingAverageAlgorithm("MovingAverage", services.history_service, 5, 15)
        mr_algo = MeanReversionAlgorithm("MeanReversion", services.history_service, 20, 1.5)
        pairs_algo = PairsTradingAlgorithm(
            "PairsTrading", 
            services.history_service,
            [("AAPL", "MSFT"), ("GOOGL", "META")]
        )
        
        # Create engine and add algorithms
        engine = TradingEngine(services.market_data_service, services.history_service)
        engine.add_algorithm(ma_algo)
        engine.add_algorithm(mr_algo)
        engine.add_algorithm(pairs_algo)
        
        # Run backtest
        symbols = ["AAPL", "MSFT", "GOOGL", "META", "TSLA"]
        engine.run_backtest(symbols, time_step=timedelta(days=1))
        
        # Print results
        print("\n=== Algorithm Results ===")
        
        print(f"\nMoving Average Algorithm:")
        print(f"  Data points processed: {ma_algo.data_points_processed}")
        print(f"  Trades executed: {ma_algo.trades_executed}")
        print(f"  History requests: {ma_algo.history_requests}")
        print(f"  Final positions: {ma_algo.positions}")
        
        print(f"\nMean Reversion Algorithm:")
        print(f"  Data points processed: {mr_algo.data_points_processed}")
        print(f"  Trades executed: {mr_algo.trades_executed}")
        print(f"  History requests: {mr_algo.history_requests}")
        print(f"  Final positions: {mr_algo.positions}")
        
        print(f"\nPairs Trading Algorithm:")
        print(f"  Data points processed: {pairs_algo.data_points_processed}")
        print(f"  Trades executed: {pairs_algo.trades_executed}")
        print(f"  History requests: {pairs_algo.history_requests}")
        print(f"  Final positions: {pairs_algo.positions}")
        
        # Print sample trades
        print(f"\nSample trades from Moving Average Algorithm:")
        for trade in ma_algo.trades[:5]:  # First 5 trades
            print(f"  {trade}")
        
    except Exception as e:
        print(f"Algorithm examples failed: {e}")


if __name__ == "__main__":
    print("Market Data History Service Algorithm Examples")
    print("=" * 50)
    
    # Run demonstrations
    demonstrate_frontier_enforcement()
    print("\n" + "="*50 + "\n")
    
    run_algorithm_examples()
    
    print("\nAll algorithm examples completed!")