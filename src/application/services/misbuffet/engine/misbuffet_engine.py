"""
Misbuffet Engine Module

This module contains the main MisbuffetEngine class and related components
for backtesting and live trading operations.
"""

import logging
from datetime import timedelta


class MisbuffetEngine:
    """Misbuffet backtesting and live trading engine."""
    
    def __init__(self):
        self.data_feed = None
        self.transaction_handler = None
        self.result_handler = None
        self.setup_handler = None
        self.algorithm = None
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
                    self.algorithm.add_equity = lambda symbol, resolution: self.logger.info(f"Added equity: {symbol} resolution={resolution}")
                
                # Add history method if not present
                if not hasattr(self.algorithm, 'history'):
                    def mock_history(*args, **kwargs):
                        import pandas as pd
                        import numpy as np
                        # Return mock historical data
                        dates = pd.date_range(start='2023-01-01', periods=100, freq='D')
                        return pd.DataFrame({
                            'time': dates,
                            'close': np.random.normal(100, 10, 100),
                            'open': np.random.normal(100, 10, 100),
                            'high': np.random.normal(105, 10, 100),
                            'low': np.random.normal(95, 10, 100),
                            'volume': np.random.randint(1000, 10000, 100)
                        })
                    self.algorithm.history = mock_history
                
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