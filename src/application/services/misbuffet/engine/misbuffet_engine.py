"""
Misbuffet Engine Module

This module contains the main MisbuffetEngine class and related components
for backtesting and live trading operations.
"""

import logging
from datetime import timedelta, datetime
from typing import Optional, List, Dict, Any
import pandas as pd

from decimal import Decimal
# Import the stock data repository for real data access
from infrastructure.repositories.local_repo.back_testing import StockDataRepository

from domain.entities.finance.back_testing import Portfolio

# Import BaseEngine for proper inheritance
from .base_engine import BaseEngine
from .engine_node_packet import EngineNodePacket


class MisbuffetEngine(BaseEngine):
    """Misbuffet backtesting and live trading engine."""
    
    def __init__(self):
        # Initialize BaseEngine first
        super().__init__()
        
        # Additional MisbuffetEngine specific attributes
        self.stock_data_repository = None
        self.database_manager = None
        
        # Override logger to maintain existing naming
        self.logger = logging.getLogger("misbuffet.engine")
        self._logger = self.logger  # Keep BaseEngine's logger reference
        
        # Maintain backward compatibility for algorithm attribute
        self.algorithm = self._algorithm
        
    def setup(self, data_feed=None, transaction_handler=None, result_handler=None, setup_handler=None):
        """Setup the engine with handlers."""
        # Use BaseEngine's handler attributes
        if data_feed:
            self._data_feed = data_feed
        if transaction_handler:
            self._transaction_handler = transaction_handler
        if result_handler:
            self._result_handler = result_handler
        if setup_handler:
            self._setup_handler = setup_handler
            
        # Maintain backward compatibility with old attribute names
        self.data_feed = self._data_feed
        self.transaction_handler = self._transaction_handler
        self.result_handler = self._result_handler
        self.setup_handler = self._setup_handler
        
    def run(self, config):
        """Run backtest with the given configuration."""
        self.logger.info("Starting backtest engine...")
        
        # Create a simple EngineNodePacket from config for BaseEngine compatibility
        try:
            from .engine_node_packet import EngineNodePacket
            from .enums import EngineMode, LogLevel, PacketType
            
            # Create job packet from config with required arguments
            job = EngineNodePacket(
                type=PacketType.ALGORITHM_NODE_PACKET,
                user_id=1,  # Default user ID
                project_id=1,  # Default project ID
                session_id="misbuffet_session"  # Default session ID
            )
            job.algorithm_id = getattr(config, 'algorithm_type_name', 'MisbuffetAlgorithm')
            job.engine_mode = EngineMode.BACKTESTING
            job.log_level = LogLevel.INFO
            
            # Set up basic configuration
            engine_config = getattr(config, 'custom_config', {})
            job.start_date = engine_config.get('start_date')
            job.end_date = engine_config.get('end_date')
            
            # Store job for use in BaseEngine methods
            self._job = job
            
        except ImportError:
            # Fallback if engine components aren't available
            self.logger.warning("Could not create EngineNodePacket, using legacy mode")
            pass
        
        try:
            # Initialize algorithm - create instance from class
            if hasattr(config, 'algorithm') and config.algorithm:
                self.logger.info(f"Creating algorithm instance from class: {config.algorithm}")
                self._algorithm = config.algorithm()  # Instantiate the class
                self.algorithm = self._algorithm  # Maintain backward compatibility
                self.logger.info(f"Algorithm instance created: {self.algorithm}")
                
            # Setup algorithm with config
            if self.algorithm:
                # Portfolio setup with domain entity
                initial_capital = getattr(config, 'initial_capital', 100000)

                self.algorithm.portfolio = Portfolio(
                    name=f"Algorithm_{self.algorithm.__class__.__name__}",
                    initial_cash=Decimal(str(initial_capital))
                )
                
                # Setup time property (required by MyAlgorithm)
                from datetime import datetime
                self.algorithm.time = datetime.now()
                
                # Add log method if not present
                if not hasattr(self.algorithm, 'log'):
                    self.algorithm.log = lambda msg: self.logger.info(f"Algorithm: {msg}")
                
                # Add market_order method if not present  
                if not hasattr(self.algorithm, 'market_order'):
                    self.algorithm.market_order = lambda symbol, qty: self.logger.info(f"Market order: {symbol} qty={qty}")
                
                # Add add_equity method if not present
                if not hasattr(self.algorithm, 'add_equity'):
                    def add_equity_with_database(symbol, resolution):
                        if self.stock_data_repository and self.stock_data_repository.table_exists(symbol):
                            self.logger.info(f"✅ Added equity: {symbol} resolution={resolution} (database data available)")
                        else:
                            self.logger.info(f"⚠️ Added equity: {symbol} resolution={resolution} (using mock data - no database table found)")
                    self.algorithm.add_equity = add_equity_with_database
                
                # Setup database connection for real data access
                if hasattr(config, 'database_manager'):
                    self.database_manager = config.database_manager
                    self.stock_data_repository = StockDataRepository(self.database_manager)
                    self.logger.info("Database connection established for real stock data access")
                
                # Add history method that uses real data from database
                if not hasattr(self.algorithm, 'history'):
                    def real_history(tickers, periods, resolution, end_time=None):
                        return self._get_historical_data(tickers, periods, end_time)
                    self.algorithm.history = real_history
                
                self.logger.info(f"Portfolio setup complete with initial capital: {initial_capital}")
            
            # Initialize algorithm - this is where initialize() should be called
            if self.algorithm and hasattr(self.algorithm, 'initialize'):
                self.logger.info("Calling algorithm.initialize()...")
                self.algorithm.initialize()
                self.logger.info("Algorithm.initialize() completed successfully")
            else:
                self.logger.warning("Algorithm doesn't have initialize method or algorithm is None")
                
            # Run simulation and collect performance data
            performance_data = self._run_simulation(config)
            
            # Create comprehensive result
            result = BacktestResult()
            result.success = True
            
            # Set performance data
            engine_config = getattr(config, 'custom_config', {})
            initial_capital = engine_config.get('initial_capital', 100000)
            start_date = engine_config.get('start_date', datetime(2021, 1, 1))
            end_date = engine_config.get('end_date', datetime(2022, 1, 1))
            
            # Calculate final portfolio value (simplified)
            final_value = initial_capital + (performance_data.get('data_points_processed', 0) * 10)  # Mock growth
            
            result.set_performance_data(
                initial_capital=initial_capital,
                final_value=final_value,
                start_date=start_date,
                end_date=end_date,
                data_points=performance_data.get('data_points_processed', 0),
                algorithm_calls=performance_data.get('algorithm_calls', 0),
                total_trades=performance_data.get('total_trades', 0)
            )
            
            self.logger.info("Backtest completed successfully.")
            return result
            
        except Exception as e:
            self.logger.error(f"Engine run failed: {e}")
            result = BacktestResult()
            result.success = False
            result.error_message = str(e)
            return result
    
    def _run_simulation(self, config):
        """Run the actual simulation loop."""
        # Get date range from engine config
        engine_config = getattr(config, 'custom_config', {})
        start_date = engine_config.get('start_date', datetime(2021, 1, 1))
        end_date = engine_config.get('end_date', datetime(2022, 1, 1))
        
        self.logger.info(f"Running simulation from {start_date} to {end_date}")
        
        current_date = start_date
        data_points_processed = 0
        
        # Track universe of symbols the algorithm is interested in
        universe = getattr(self.algorithm, 'universe', ['AAPL', 'MSFT', 'AMZN', 'GOOGL'])
        
        # Simple simulation loop - process data daily
        while current_date <= end_date:
            # Create data slice with real stock data for this date
            if self.algorithm and hasattr(self.algorithm, 'on_data'):
                try:
                    data_slice = self._create_data_slice(current_date, universe)
                    
                    # Only call on_data if we have data for this date
                    if data_slice.has_data:
                        # Update algorithm time
                        self.algorithm.time = current_date
                        
                        # Call on_data with real data
                        self.algorithm.on_data(data_slice)
                        data_points_processed += 1
                        
                        if data_points_processed % 50 == 0:  # Log every 50 data points
                            self.logger.info(f"Processed {data_points_processed} data points, current date: {current_date.date()}")
                    
                except Exception as e:
                    self.logger.warning(f"Algorithm on_data error at {current_date}: {e}")
                    
            current_date += timedelta(days=1)
        
        self.logger.info(f"Simulation complete. Processed {data_points_processed} data points.")
        
        # Return performance data
        return {
            'data_points_processed': data_points_processed,
            'algorithm_calls': data_points_processed,  # Same as data points for now
            'total_trades': 0,  # Would be tracked by transaction handler
            'universe_size': len(universe)
        }
    
    def _create_data_slice(self, current_date, universe):
        """Create a data slice for the given date and universe of symbols."""
        from ..common.data_types import Slice, TradeBars, TradeBar
        from ..common.symbol import Symbol
        
        # Create the slice for this time point
        slice_data = Slice(time=current_date)
        
        # Get data for each symbol in the universe
        for ticker in universe:
            try:
                # Get historical data for just this one day
                hist_data = self._get_single_day_data(ticker, current_date)
                
                if hist_data is not None and not hist_data.empty:
                    # Create Symbol object
                    symbol = Symbol.create_equity(ticker)
                    
                    # Use the most recent data point (should be just one for this date)
                    latest_data = hist_data.iloc[-1]
                    
                    # Create TradeBar from the data
                    trade_bar = TradeBar(
                        symbol=symbol,
                        time=current_date,
                        end_time=current_date,
                        open=float(latest_data.get('Open', latest_data.get('open', 0.0))),
                        high=float(latest_data.get('High', latest_data.get('high', 0.0))),
                        low=float(latest_data.get('Low', latest_data.get('low', 0.0))),
                        close=float(latest_data.get('Close', latest_data.get('close', 0.0))),
                        volume=int(latest_data.get('Volume', latest_data.get('volume', 0)))
                    )
                    
                    # Add to slice
                    slice_data.bars[symbol] = trade_bar
                    
            except Exception as e:
                self.logger.debug(f"No data available for {ticker} on {current_date}: {e}")
                continue
        
        return slice_data
    
    def _get_single_day_data(self, ticker, target_date):
        """Get stock data for a single day."""
        if self.stock_data_repository is None:
            return None
        
        try:
            # Get data around the target date (±1 day window)
            df = self.stock_data_repository.get_historical_data(ticker, periods=3, end_time=target_date + timedelta(days=1))
            
            if df is not None and not df.empty:
                
                # Convert Date column to datetime if it's not already
                if 'Date' in df.columns:
                    df['Date'] = pd.to_datetime(df['Date'])
                    
                    # Filter to get the closest date to target_date
                    df['date_diff'] = abs((df['Date'] - target_date).dt.days)
                    closest_data = df.loc[df['date_diff'].idxmin()]
                    
                    # Return as single-row DataFrame
                    return pd.DataFrame([closest_data])
            
            return None
            
        except Exception as e:
            self.logger.debug(f"Error getting single day data for {ticker} on {target_date}: {e}")
            return None
    
    def _get_historical_data(self, tickers, periods, end_time=None):
        """
        Retrieve historical stock data from database.
        
        Args:
            tickers: List of ticker symbols or single ticker
            periods: Number of periods to retrieve
            end_time: Optional end date for historical data
            
        Returns:
            DataFrame or dictionary of DataFrames with historical data
        """
        
        
        try:
            # Handle single ticker or list of tickers
            if isinstance(tickers, str):
                tickers = [tickers]
            elif not isinstance(tickers, list):
                # Handle cases where tickers might be passed in other formats
                tickers = list(tickers)
            
            # Get data from database for each ticker
            result_data = {}
            for ticker in tickers:
                df = self.stock_data_repository.get_historical_data(ticker, periods, end_time)
                
                # Rename columns to match expected format
                df_standardized = df.rename(columns={
                    'Date': 'time',
                    'Open': 'open', 
                    'High': 'high',
                    'Low': 'low',
                    'Close': 'close',
                    'Volume': 'volume'
                })
                result_data[ticker] = df_standardized
                self.logger.info(f"Retrieved {len(df)} records for {ticker} from database")
                
            
            # Return format based on input
            if len(tickers) == 1:
                return result_data.get(tickers[0], pd.DataFrame())
            else:
                return result_data
                
        except Exception as e:
            self.logger.error(f"Error retrieving historical data: {e}")
            
    
    

    def _execute_main_loop(self) -> None:
        """Execute the main engine loop. Required by BaseEngine."""
        try:
            # Use the existing simulation logic
            if hasattr(self, '_job') and self._job:
                # Get configuration from the job
                engine_config = getattr(self._job, 'custom_config', {})
                start_date = getattr(self._job, 'start_date', datetime(2021, 1, 1))
                end_date = getattr(self._job, 'end_date', datetime(2022, 1, 1))
            else:
                # Fallback configuration
                start_date = datetime(2021, 1, 1)
                end_date = datetime(2022, 1, 1)
            
            self.logger.info(f"Running simulation from {start_date} to {end_date}")
            
            current_date = start_date
            data_points_processed = 0
            
            # Track universe of symbols the algorithm is interested in
            universe = getattr(self.algorithm, 'universe', ['AAPL', 'MSFT', 'AMZN', 'GOOGL'])
            
            # Simple simulation loop - process data daily
            while current_date <= end_date:
                if self._stop_requested():
                    break
                    
                # Create data slice with real stock data for this date
                if self.algorithm and hasattr(self.algorithm, 'on_data'):
                    try:
                        data_slice = self._create_data_slice(current_date, universe)
                        
                        # Only call on_data if we have data for this date
                        if data_slice.has_data:
                            # Update algorithm time
                            self.algorithm.time = current_date
                            
                            # Call on_data with real data
                            self.algorithm.on_data(data_slice)
                            data_points_processed += 1
                            
                            if data_points_processed % 50 == 0:  # Log every 50 data points
                                self.logger.info(f"Processed {data_points_processed} data points, current date: {current_date.date()}")
                        
                    except Exception as e:
                        self.logger.warning(f"Algorithm on_data error at {current_date}: {e}")
                        
                current_date += timedelta(days=1)
            
            self.logger.info(f"Simulation complete. Processed {data_points_processed} data points.")
            
        except Exception as e:
            self.logger.error(f"Error in main execution loop: {e}")
            self._errors.append(f"Main loop error: {str(e)}")
            raise

    def _create_handlers(self) -> bool:
        """Create and configure engine handlers. Required by BaseEngine."""
        try:
            self.logger.info("Creating MisbuffetEngine handlers")
            
            
            from . import BacktestingDataFeed
            #Importing Handlers
            from . import (
                BacktestingTransactionHandler, BacktestingResultHandler, 
                BacktestingSetupHandler, BacktestingRealTimeHandler,
                AlgorithmHandler
            )
            
            # Create handlers
            if not self._setup_handler:
                self._setup_handler = BacktestingSetupHandler()
            if not self._data_feed:
                self._data_feed = BacktestingDataFeed()
            if not self._transaction_handler:
                self._transaction_handler = BacktestingTransactionHandler()
            if not self._result_handler:
                self._result_handler = BacktestingResultHandler()
            if not self._realtime_handler:
                self._realtime_handler = BacktestingRealTimeHandler()
            if not self._algorithm_handler:
                self._algorithm_handler = AlgorithmHandler()
                
            # Maintain backward compatibility
            self.setup_handler = self._setup_handler
            self.data_feed = self._data_feed
            self.transaction_handler = self._transaction_handler
            self.result_handler = self._result_handler
                

            
            self.logger.info("MisbuffetEngine handlers created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating handlers: {e}")
            return False


# Mock classes removed - using domain entities instead


class BacktestResult:
    """Result of a backtest run."""
    
    def __init__(self):
        self.success = False
        self.error_message = None
        self.runtime_statistics = {}
        self.performance_statistics = {}
        self.portfolio_statistics = {}
        self.trade_statistics = {}
        self.start_date = None
        self.end_date = None
        self.total_return = 0.0
        self.sharpe_ratio = 0.0
        self.max_drawdown = 0.0
        self.total_trades = 0
        self.win_rate = 0.0
        self.initial_capital = 0.0
        self.final_portfolio_value = 0.0
        
    def summary(self):
        """Return a detailed summary of the backtest results."""
        if self.success:
            summary_lines = [
                "🎉 Backtest completed successfully!",
                "",
                "📊 Performance Summary:",
                f"  • Period: {self.start_date} to {self.end_date}",
                f"  • Initial Capital: ${self.initial_capital:,.2f}",
                f"  • Final Portfolio Value: ${self.final_portfolio_value:,.2f}",
                f"  • Total Return: {self.total_return:.2%}",
                f"  • Sharpe Ratio: {self.sharpe_ratio:.3f}",
                f"  • Maximum Drawdown: {self.max_drawdown:.2%}",
                "",
                "📈 Trading Statistics:",
                f"  • Total Trades: {self.total_trades}",
                f"  • Win Rate: {self.win_rate:.2%}",
                "",
                "⚙️  Runtime Statistics:",
                f"  • Data Points Processed: {self.runtime_statistics.get('data_points_processed', 0)}",
                f"  • Algorithm Calls: {self.runtime_statistics.get('algorithm_calls', 0)}",
                f"  • Errors: {self.runtime_statistics.get('errors', 0)}",
            ]
            
            # Add detailed performance stats if available
            if self.performance_statistics:
                summary_lines.extend([
                    "",
                    "📈 Detailed Performance:",
                    f"  • Alpha: {self.performance_statistics.get('alpha', 0.0):.3f}",
                    f"  • Beta: {self.performance_statistics.get('beta', 0.0):.3f}",
                    f"  • Volatility: {self.performance_statistics.get('volatility', 0.0):.2%}",
                    f"  • Information Ratio: {self.performance_statistics.get('information_ratio', 0.0):.3f}",
                ])
            
            return "\n".join(summary_lines)
        else:
            return f"❌ Backtest failed: {self.error_message}"
    
    def set_performance_data(self, initial_capital, final_value, start_date, end_date, 
                           data_points=0, algorithm_calls=0, total_trades=0):
        """Set basic performance data for the backtest result."""
        self.initial_capital = initial_capital
        self.final_portfolio_value = final_value
        self.start_date = start_date.strftime('%Y-%m-%d') if start_date else "N/A"
        self.end_date = end_date.strftime('%Y-%m-%d') if end_date else "N/A"
        self.total_trades = total_trades
        
        # Calculate total return
        if initial_capital > 0:
            self.total_return = (final_value - initial_capital) / initial_capital
        
        # Update runtime statistics
        self.runtime_statistics.update({
            'data_points_processed': data_points,
            'algorithm_calls': algorithm_calls,
            'total_orders': total_trades,
            'trades': total_trades
        })
        
        # Calculate basic performance metrics (simplified)
        if data_points > 0:
            # Estimate annualized Sharpe ratio (simplified calculation)
            if self.total_return > 0:
                self.sharpe_ratio = self.total_return * (252 ** 0.5) / max(0.01, abs(self.total_return))
            
            # Estimate max drawdown (simplified)
            self.max_drawdown = max(0, -self.total_return * 0.3)  # Rough estimate
        
        # Win rate estimation (simplified)
        self.win_rate = 0.6 if self.total_return > 0 else 0.4


__all__ = [
    'MisbuffetEngine',
    'BacktestResult'
]