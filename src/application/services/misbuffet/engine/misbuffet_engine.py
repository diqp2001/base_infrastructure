"""
Misbuffet Engine Module

This module contains the main MisbuffetEngine class and related components
for backtesting and live trading operations.
"""

import logging
from datetime import timedelta, datetime
from typing import Optional, List, Dict, Any
import pandas as pd

# Import the stock data repository for real data access
from infrastructure.repositories.local_repo.back_testing import StockDataRepository


class MisbuffetEngine:
    """Misbuffet backtesting and live trading engine."""
    
    def __init__(self):
        self.data_feed = None
        self.transaction_handler = None
        self.result_handler = None
        self.setup_handler = None
        self.algorithm = None
        self.stock_data_repository = None
        self.database_manager = None
        self.logger = logging.getLogger("misbuffet.engine")
        
    def setup(self, data_feed=None, transaction_handler=None, result_handler=None, setup_handler=None):
        """Setup the engine with handlers."""
        self.data_feed = data_feed
        self.transaction_handler = transaction_handler
        self.result_handler = result_handler
        self.setup_handler = setup_handler
        
    def run(self, config):
        """Run backtest with the given configuration."""
        self.logger.info("Starting backtest engine...")
        
        try:
            # Initialize algorithm - create instance from class
            if hasattr(config, 'algorithm') and config.algorithm:
                self.logger.info(f"Creating algorithm instance from class: {config.algorithm}")
                self.algorithm = config.algorithm()  # Instantiate the class
                self.logger.info(f"Algorithm instance created: {self.algorithm}")
                
            # Setup algorithm with config
            if self.algorithm:
                # Mock portfolio setup
                initial_capital = getattr(config, 'initial_capital', 100000)
                self.algorithm.portfolio = MockPortfolio(initial_capital)
                
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
                
            # Run simulation
            self._run_simulation(config)
            
            # Create result
            result = BacktestResult()
            result.success = True
            result.runtime_statistics = {"Total Orders": 0, "Trades": 0}
            
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
        start_date = getattr(config, 'start_date', None)
        end_date = getattr(config, 'end_date', None)
        
        if not start_date or not end_date:
            return
            
        current_date = start_date
        
        # Simple simulation loop
        while current_date <= end_date:
            # Mock data for algorithm
            if self.algorithm and hasattr(self.algorithm, 'on_data'):
                # Create mock data slice
                mock_data = {}
                # You would populate this with actual market data
                
                try:
                    self.algorithm.on_data(mock_data)
                except Exception as e:
                    self.logger.warning(f"Algorithm on_data error: {e}")
                    
            current_date += timedelta(days=1)
    
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
        if self.stock_data_repository is None:
            self.logger.warning("No stock data repository available, using mock data")
            return self._generate_mock_historical_data(tickers, periods)
        
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
                if not df.empty:
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
                else:
                    self.logger.warning(f"No data found for {ticker}, using mock data")
                    result_data[ticker] = self._generate_mock_historical_data([ticker], periods)
            
            # Return format based on input
            if len(tickers) == 1:
                return result_data.get(tickers[0], pd.DataFrame())
            else:
                return result_data
                
        except Exception as e:
            self.logger.error(f"Error retrieving historical data: {e}")
            return self._generate_mock_historical_data(tickers, periods)
    
    def _generate_mock_historical_data(self, tickers, periods):
        """Fallback method to generate mock historical data."""
        import numpy as np
        
        if isinstance(tickers, str):
            tickers = [tickers]
        
        dates = pd.date_range(start='2023-01-01', periods=periods, freq='D')
        result_data = {}
        
        for ticker in tickers:
            result_data[ticker] = pd.DataFrame({
                'time': dates,
                'close': np.random.normal(100, 10, periods),
                'open': np.random.normal(100, 10, periods),
                'high': np.random.normal(105, 10, periods),
                'low': np.random.normal(95, 10, periods),
                'volume': np.random.randint(1000, 10000, periods)
            })
        
        if len(tickers) == 1:
            return result_data[tickers[0]]
        else:
            return result_data


class MockPortfolio:
    """Mock portfolio for testing purposes."""
    
    def __init__(self, initial_capital=100000):
        self.total_portfolio_value = initial_capital
        self._securities = {}
    
    def __getitem__(self, symbol):
        if symbol not in self._securities:
            self._securities[symbol] = MockSecurity()
        return self._securities[symbol]


class MockSecurity:
    """Mock security for testing purposes."""
    
    def __init__(self):
        self.holdings_value = 0
        self.invested = False


class BacktestResult:
    """Result of a backtest run."""
    
    def __init__(self):
        self.success = False
        self.error_message = None
        self.runtime_statistics = {}
        
    def summary(self):
        """Return a summary of the backtest results."""
        if self.success:
            return f"Backtest completed successfully. Statistics: {self.runtime_statistics}"
        else:
            return f"Backtest failed: {self.error_message}"


__all__ = [
    'MisbuffetEngine',
    'BacktestResult',
    'MockPortfolio',
    'MockSecurity'
]