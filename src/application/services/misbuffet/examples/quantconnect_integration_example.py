"""
QuantConnect Integration Example for Misbuffet Service

This example demonstrates how to use the QuantConnect-style data management layer
with existing misbuffet handlers and managers for algorithmic trading strategies.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from ..common.symbol import Symbol
from ..common.enums import Resolution
from ..common.data_types import Slice, TradeBar
from ..algorithm.base import BaseAlgorithm
from ..data.quantconnect_data_manager import QuantConnectDataManager, QuantConnectCompatibilityLayer
from ..data.quantconnect_history_provider import QuantConnectHistoryProvider
from ..engine.quantconnect_frontier_manager import FrontierTimeManager, AlgorithmTimeCoordinator
from ..engine.misbuffet_engine import MisbuffetEngine

# Import existing services for database integration
from src.application.services.data.entities.entity_service import EntityService
from src.application.services.data.entities.factor.factor_service import FactorService


class QuantConnectIntegratedAlgorithm(BaseAlgorithm):
    """
    Example algorithm using QuantConnect-style interfaces with misbuffet infrastructure.
    """
    
    def __init__(self):
        """Initialize the algorithm with QuantConnect integration."""
        super().__init__()
        
        # QuantConnect components
        self.qc_data: Optional[QuantConnectDataManager] = None
        self.qc_history: Optional[QuantConnectHistoryProvider] = None
        self.frontier_manager: Optional[FrontierTimeManager] = None
        self.time_coordinator: Optional[AlgorithmTimeCoordinator] = None
        
        # Algorithm state
        self.universe = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]
        self.symbols: Dict[str, Symbol] = {}
        self.performance_metrics = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0
        }
        
        # Strategy parameters
        self.lookback_period = 20
        self.rebalance_frequency = timedelta(days=30)
        self.last_rebalance: Optional[datetime] = None
        
    def initialize(self):
        """
        QuantConnect-style initialize method using existing misbuffet infrastructure.
        """
        try:
            self.log("Initializing QuantConnect integrated algorithm")
            
            # Validate QuantConnect components are available
            if not self.qc_data:
                raise ValueError("QuantConnect data manager not available")
            
            # Set algorithm properties
            self.set_start_date(datetime(2023, 1, 1))
            self.set_end_date(datetime(2024, 1, 1))
            self.set_cash(100000)
            
            # Add equity subscriptions using QuantConnect-style interface
            for ticker in self.universe:
                symbol = self.qc_data.add_equity(ticker, Resolution.DAILY)
                self.symbols[ticker] = symbol
                self.log(f"Added equity subscription: {ticker}")
            
            # Set up universe
            self.qc_data.set_universe(self.universe, Resolution.DAILY)
            
            # Initialize performance tracking
            self.last_rebalance = self.get_algorithm_time()
            
            # Set up recurring rebalancing
            if self.frontier_manager:
                self.frontier_manager.schedule_recurring_callback(
                    self.rebalance_frequency,
                    self.rebalance_portfolio
                )
            
            self.log(f"Algorithm initialized with {len(self.universe)} symbols")
            
        except Exception as e:
            self.log(f"Error in algorithm initialization: {e}")
            raise
    
    def on_data(self, slice: Slice):
        """
        QuantConnect-style OnData method processing data slices.
        
        Args:
            slice: Data slice containing market data for current time
        """
        try:
            if not slice.has_data:
                return
            
            current_time = slice.time
            self.log(f"Processing data slice at {current_time}")
            
            # Synchronize algorithm time
            if self.time_coordinator:
                self.time_coordinator.sync_algorithm_time()
            
            # Process each symbol in the slice
            for symbol in slice.bars.keys():
                ticker = symbol.value
                if ticker in self.universe:
                    self.process_symbol_data(ticker, slice[symbol])
            
            # Check for rebalancing opportunity
            if self.should_rebalance():
                self.rebalance_portfolio()
            
        except Exception as e:
            self.log(f"Error in on_data: {e}")
    
    def process_symbol_data(self, ticker: str, data: TradeBar):
        """
        Process individual symbol data and make trading decisions.
        
        Args:
            ticker: Stock ticker symbol
            data: Trade bar data
        """
        try:
            if not data or data.close <= 0:
                return
            
            # Get historical data for analysis
            if self.qc_data:
                history = self.qc_data.history([ticker], self.lookback_period, Resolution.DAILY)
                
                if not history.empty and 'Close' in history.columns:
                    # Calculate simple moving average
                    sma = history['Close'].mean()
                    current_price = data.close
                    
                    # Simple momentum strategy
                    if current_price > sma * 1.05:  # 5% above SMA
                        self.buy_signal(ticker, current_price)
                    elif current_price < sma * 0.95:  # 5% below SMA  
                        self.sell_signal(ticker, current_price)
            
        except Exception as e:
            self.log(f"Error processing symbol data for {ticker}: {e}")
    
    def buy_signal(self, ticker: str, price: float):
        """Execute buy signal for a symbol."""
        try:
            if not self.portfolio.is_invested(ticker):
                # Calculate position size (equal weight)
                target_allocation = 1.0 / len(self.universe)
                self.set_holdings(ticker, target_allocation)
                
                self.performance_metrics['total_trades'] += 1
                self.log(f"BUY signal: {ticker} at ${price:.2f}")
                
        except Exception as e:
            self.log(f"Error executing buy signal for {ticker}: {e}")
    
    def sell_signal(self, ticker: str, price: float):
        """Execute sell signal for a symbol."""
        try:
            if self.portfolio.is_invested(ticker):
                self.liquidate(ticker)
                
                self.performance_metrics['total_trades'] += 1
                self.log(f"SELL signal: {ticker} at ${price:.2f}")
                
        except Exception as e:
            self.log(f"Error executing sell signal for {ticker}: {e}")
    
    def should_rebalance(self) -> bool:
        """Check if portfolio should be rebalanced."""
        try:
            if not self.last_rebalance:
                return True
            
            current_time = self.get_algorithm_time()
            return (current_time - self.last_rebalance) >= self.rebalance_frequency
            
        except Exception:
            return False
    
    def rebalance_portfolio(self):
        """Rebalance portfolio to equal weights."""
        try:
            self.log("Rebalancing portfolio...")
            
            # Equal weight allocation
            target_weight = 1.0 / len(self.universe)
            
            for ticker in self.universe:
                if ticker in self.symbols:
                    self.set_holdings(ticker, target_weight)
            
            self.last_rebalance = self.get_algorithm_time()
            self.log("Portfolio rebalancing completed")
            
        except Exception as e:
            self.log(f"Error rebalancing portfolio: {e}")
    
    def get_algorithm_time(self) -> datetime:
        """Get current algorithm time."""
        if self.frontier_manager:
            return self.frontier_manager.get_frontier_time() or datetime.now()
        return self.time
    
    def on_end_of_algorithm(self):
        """Called at the end of algorithm execution."""
        try:
            self.log("Algorithm execution completed")
            
            # Log performance metrics
            total_trades = self.performance_metrics['total_trades']
            portfolio_value = self.portfolio.total_portfolio_value
            initial_cash = 100000  # From initialization
            
            total_return = ((portfolio_value - initial_cash) / initial_cash) * 100
            
            self.log(f"Final Portfolio Value: ${portfolio_value:,.2f}")
            self.log(f"Total Return: {total_return:.2f}%")
            self.log(f"Total Trades: {total_trades}")
            
        except Exception as e:
            self.log(f"Error in end of algorithm: {e}")


class QuantConnectMisbuffetIntegrator:
    """
    Integrates QuantConnect-style components with existing misbuffet engine and services.
    """
    
    def __init__(self, database_service=None):
        """
        Initialize the integrator.
        
        Args:
            database_service: Database service for data access
        """
        self.logger = logging.getLogger("misbuffet.qc_integrator")
        self.database_service = database_service
        
        # Services
        self.entity_service: Optional[EntityService] = None
        self.factor_service: Optional[FactorService] = None
        
        # QuantConnect components
        self.qc_data_manager: Optional[QuantConnectDataManager] = None
        self.qc_history_provider: Optional[QuantConnectHistoryProvider] = None
        self.frontier_manager: Optional[FrontierTimeManager] = None
        
        # Engine
        self.misbuffet_engine: Optional[MisbuffetEngine] = None
        
    def initialize_services(self) -> bool:
        """Initialize data services."""
        try:
            if self.database_service:
                self.entity_service = EntityService(self.database_service)
                self.factor_service = FactorService(self.database_service)
                self.logger.info("Data services initialized")
                return True
            else:
                self.logger.warning("No database service provided")
                return False
                
        except Exception as e:
            self.logger.error(f"Error initializing services: {e}")
            return False
    
    def create_quantconnect_components(self) -> bool:
        """Create QuantConnect-style components."""
        try:
            # Create history provider
            self.qc_history_provider = QuantConnectHistoryProvider(
                entity_service=self.entity_service,
                factor_service=self.factor_service
            )
            
            # Create data manager (will create its own data feed)
            self.qc_data_manager = QuantConnectDataManager(
                entity_service=self.entity_service,
                factor_service=self.factor_service
            )
            
            # Initialize data manager
            if not self.qc_data_manager.initialize():
                self.logger.error("Failed to initialize QuantConnect data manager")
                return False
            
            # Create frontier time manager
            self.frontier_manager = FrontierTimeManager(
                data_manager=self.qc_data_manager,
                history_provider=self.qc_history_provider
            )
            
            self.logger.info("QuantConnect components created successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error creating QuantConnect components: {e}")
            return False
    
    def run_algorithm_with_quantconnect(self, algorithm_class, config) -> Dict[str, Any]:
        """
        Run an algorithm with QuantConnect integration.
        
        Args:
            algorithm_class: Algorithm class to run
            config: Algorithm configuration
            
        Returns:
            Dictionary with execution results
        """
        try:
            # Initialize services
            if not self.initialize_services():
                return {"success": False, "error": "Failed to initialize services"}
            
            # Create QuantConnect components
            if not self.create_quantconnect_components():
                return {"success": False, "error": "Failed to create QuantConnect components"}
            
            # Create algorithm instance
            algorithm = algorithm_class()
            
            # Inject QuantConnect components
            algorithm.qc_data = self.qc_data_manager
            algorithm.qc_history = self.qc_history_provider
            algorithm.frontier_manager = self.frontier_manager
            algorithm.time_coordinator = AlgorithmTimeCoordinator(
                self.frontier_manager, algorithm
            )
            
            # Initialize algorithm
            algorithm.initialize()
            
            # Set up frontier time manager for backtesting
            start_date = getattr(config, 'start_date', datetime(2023, 1, 1))
            end_date = getattr(config, 'end_date', datetime(2024, 1, 1))
            
            self.frontier_manager.initialize(start_date, end_date, Resolution.DAILY)
            
            # Run simulation loop
            slice_count = 0
            while True:
                slice_obj = self.frontier_manager.advance_time(algorithm.universe)
                if not slice_obj:
                    break
                
                # Process data slice
                algorithm.on_data(slice_obj)
                slice_count += 1
                
                # Progress logging
                if slice_count % 50 == 0:
                    stats = self.frontier_manager.get_statistics()
                    progress = stats.get('progress_percentage', 0)
                    self.logger.info(f"Backtest progress: {progress:.1f}% ({slice_count} slices)")
            
            # End of algorithm
            algorithm.on_end_of_algorithm()
            
            # Get final statistics
            final_stats = self.frontier_manager.get_statistics()
            
            self.logger.info("Algorithm execution completed successfully")
            
            return {
                "success": True,
                "slices_processed": slice_count,
                "final_time": final_stats.get('current_frontier_time'),
                "algorithm_performance": algorithm.performance_metrics
            }
            
        except Exception as e:
            self.logger.error(f"Error running algorithm with QuantConnect: {e}")
            return {"success": False, "error": str(e)}
        
        finally:
            # Cleanup
            try:
                if self.qc_data_manager:
                    self.qc_data_manager.dispose()
                if self.frontier_manager:
                    self.frontier_manager.dispose()
            except Exception as e:
                self.logger.error(f"Error during cleanup: {e}")


def run_quantconnect_example():
    """
    Example function showing how to run QuantConnect-style algorithm with misbuffet.
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("example")
    
    try:
        # Example configuration
        class ExampleConfig:
            start_date = datetime(2023, 1, 1)
            end_date = datetime(2023, 12, 31)
            initial_capital = 100000
        
        # Create integrator (would normally pass real database_service)
        integrator = QuantConnectMisbuffetIntegrator(database_service=None)
        
        # Run algorithm
        config = ExampleConfig()
        result = integrator.run_algorithm_with_quantconnect(
            QuantConnectIntegratedAlgorithm, 
            config
        )
        
        if result["success"]:
            logger.info("QuantConnect integration example completed successfully")
            logger.info(f"Result: {result}")
        else:
            logger.error(f"Example failed: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Error in QuantConnect example: {e}")


if __name__ == "__main__":
    run_quantconnect_example()