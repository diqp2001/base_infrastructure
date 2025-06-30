"""
Core interfaces for the QuantConnect Lean Engine Python implementation.
These define the contracts that various engine components must implement.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Callable
from decimal import Decimal

# Import from common module using relative imports
from ..common import IAlgorithm, BaseData, Symbol, Order, OrderEvent


class IEngine(ABC):
    """
    Interface for the main engine implementations.
    Defines the contract for both backtesting and live trading engines.
    """
    
    @abstractmethod
    def run(self, job: 'EngineNodePacket', algorithm_manager: 'AlgorithmManager') -> None:
        """Run the engine with the specified job and algorithm manager."""
        pass
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the engine and all its components."""
        pass
    
    @abstractmethod
    def dispose(self) -> None:
        """Clean up engine resources."""
        pass


class IDataFeed(ABC):
    """
    Interface for data feed implementations.
    Manages data subscriptions and delivery to algorithms.
    """
    
    @abstractmethod
    def initialize(self, algorithm: IAlgorithm, job: 'EngineNodePacket') -> bool:
        """Initialize the data feed with algorithm and job parameters."""
        pass
    
    @abstractmethod
    def create_subscription(self, symbol: Symbol, resolution: 'Resolution') -> 'SubscriptionDataConfig':
        """Create a data subscription for the given symbol and resolution."""
        pass
    
    @abstractmethod
    def remove_subscription(self, config: 'SubscriptionDataConfig') -> bool:
        """Remove a data subscription."""
        pass
    
    @abstractmethod
    def get_next_ticks(self) -> List[BaseData]:
        """Get the next batch of data ticks."""
        pass
    
    @abstractmethod
    def is_active(self) -> bool:
        """Check if the data feed is active and running."""
        pass
    
    @abstractmethod
    def exit(self) -> None:
        """Exit and cleanup the data feed."""
        pass


class ITransactionHandler(ABC):
    """
    Interface for transaction handling implementations.
    Processes orders and manages order execution.
    """
    
    @abstractmethod
    def initialize(self, algorithm: IAlgorithm, brokerage: 'IBrokerage') -> None:
        """Initialize the transaction handler with algorithm and brokerage."""
        pass
    
    @abstractmethod
    def process_order(self, order: Order) -> bool:
        """Process an order for execution."""
        pass
    
    @abstractmethod
    def get_open_orders(self, symbol: Optional[Symbol] = None) -> List[Order]:
        """Get all open orders, optionally filtered by symbol."""
        pass
    
    @abstractmethod
    def get_order_tickets(self) -> List['OrderTicket']:
        """Get all order tickets."""
        pass
    
    @abstractmethod
    def cancel_order(self, order_id: int) -> bool:
        """Cancel an existing order."""
        pass
    
    @abstractmethod
    def update_order(self, order: Order) -> bool:
        """Update an existing order."""
        pass
    
    @abstractmethod
    def handle_fills(self, fills: List['OrderEvent']) -> None:
        """Handle order fill events."""
        pass


class IResultHandler(ABC):
    """
    Interface for result handling implementations.
    Manages performance tracking, charts, and result storage.
    """
    
    @abstractmethod
    def initialize(self, algorithm: IAlgorithm, job: 'EngineNodePacket') -> None:
        """Initialize the result handler with algorithm and job parameters."""
        pass
    
    @abstractmethod
    def process_synchronous_events(self, algorithm: IAlgorithm) -> None:
        """Process algorithm events synchronously."""
        pass
    
    @abstractmethod
    def send_status_update(self, status: str, message: str = "") -> None:
        """Send a status update message."""
        pass
    
    @abstractmethod
    def runtime_statistic(self, key: str, value: str) -> None:
        """Set a runtime statistic."""
        pass
    
    @abstractmethod
    def debug_message(self, message: str) -> None:
        """Send a debug message."""
        pass
    
    @abstractmethod
    def error_message(self, error: str, stack_trace: str = "") -> None:
        """Send an error message."""
        pass
    
    @abstractmethod
    def log_message(self, message: str) -> None:
        """Log a message."""
        pass
    
    @abstractmethod
    def chart(self, name: str, chart_type: str, series: str, 
              time: datetime, value: Union[float, Decimal]) -> None:
        """Add a point to a chart series."""
        pass
    
    @abstractmethod
    def store_result(self, packet: Dict[str, Any]) -> None:
        """Store a result packet."""
        pass
    
    @abstractmethod
    def send_final_result(self) -> None:
        """Send the final results."""
        pass
    
    @abstractmethod
    def exit(self) -> None:
        """Exit and cleanup the result handler."""
        pass


class ISetupHandler(ABC):
    """
    Interface for setup handler implementations.
    Manages algorithm initialization and universe setup.
    """
    
    @abstractmethod
    def setup(self, job: 'EngineNodePacket') -> IAlgorithm:
        """Setup and return the algorithm instance."""
        pass
    
    @abstractmethod
    def create_algorithm_instance(self, job: 'EngineNodePacket') -> IAlgorithm:
        """Create an algorithm instance from the job specification."""
        pass
    
    @abstractmethod
    def setup_algorithm(self, algorithm: IAlgorithm, job: 'EngineNodePacket') -> None:
        """Setup the algorithm with initial parameters."""
        pass
    
    @abstractmethod
    def get_start_date(self) -> datetime:
        """Get the algorithm start date."""
        pass
    
    @abstractmethod
    def get_end_date(self) -> datetime:
        """Get the algorithm end date."""
        pass
    
    @abstractmethod
    def get_cash(self) -> Decimal:
        """Get the initial cash amount."""
        pass
    
    @abstractmethod
    def dispose(self) -> None:
        """Dispose of setup handler resources."""
        pass


class IRealTimeHandler(ABC):
    """
    Interface for real-time handler implementations.
    Manages time-based events and scheduling.
    """
    
    @abstractmethod
    def initialize(self, algorithm: IAlgorithm, job: 'EngineNodePacket') -> None:
        """Initialize the real-time handler."""
        pass
    
    @abstractmethod
    def set_time(self, time: datetime) -> None:
        """Set the current algorithm time."""
        pass
    
    @abstractmethod
    def scan_past_events(self, time: datetime) -> None:
        """Scan for past events that should be triggered."""
        pass
    
    @abstractmethod
    def add(self, scheduled_event: 'ScheduledEvent') -> None:
        """Add a scheduled event."""
        pass
    
    @abstractmethod
    def remove(self, scheduled_event: 'ScheduledEvent') -> None:
        """Remove a scheduled event."""
        pass
    
    @abstractmethod
    def is_active(self) -> bool:
        """Check if the real-time handler is active."""
        pass
    
    @abstractmethod
    def exit(self) -> None:
        """Exit and cleanup the real-time handler."""
        pass


class IAlgorithmHandler(ABC):
    """
    Interface for algorithm lifecycle management.
    Manages algorithm execution state and lifecycle events.
    """
    
    @abstractmethod
    def initialize(self, job: 'EngineNodePacket', algorithm: IAlgorithm) -> bool:
        """Initialize the algorithm handler."""
        pass
    
    @abstractmethod
    def run(self) -> None:
        """Run the algorithm handler."""
        pass
    
    @abstractmethod
    def on_data(self, data: 'Slice') -> None:
        """Handle new market data."""
        pass
    
    @abstractmethod
    def on_order_event(self, order_event: OrderEvent) -> None:
        """Handle order events."""
        pass
    
    @abstractmethod
    def sample_performance(self, time: datetime, value: Decimal) -> None:
        """Sample algorithm performance at a given time."""
        pass
    
    @abstractmethod
    def set_status(self, status: 'AlgorithmStatus') -> None:
        """Set the algorithm status."""
        pass
    
    @abstractmethod
    def get_status(self) -> 'AlgorithmStatus':
        """Get the current algorithm status."""
        pass
    
    @abstractmethod
    def exit(self) -> None:
        """Exit and cleanup the algorithm handler."""
        pass


class IBrokerage(ABC):
    """
    Interface for brokerage implementations.
    Handles communication with external trading platforms.
    """
    
    @abstractmethod
    def connect(self) -> bool:
        """Connect to the brokerage."""
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Disconnect from the brokerage."""
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        """Check if connected to the brokerage."""
        pass
    
    @abstractmethod
    def place_order(self, order: Order) -> bool:
        """Place an order with the brokerage."""
        pass
    
    @abstractmethod
    def update_order(self, order: Order) -> bool:
        """Update an existing order."""
        pass
    
    @abstractmethod
    def cancel_order(self, order: Order) -> bool:
        """Cancel an order."""
        pass
    
    @abstractmethod
    def get_cash_balance(self) -> Dict[str, Decimal]:
        """Get cash balances by currency."""
        pass
    
    @abstractmethod
    def get_holdings(self) -> Dict[Symbol, 'Holding']:
        """Get current holdings."""
        pass


class IHistoryProvider(ABC):
    """
    Interface for history data providers.
    Provides historical market data for backtesting and research.
    """
    
    @abstractmethod
    def get_history(self, symbol: Symbol, start: datetime, end: datetime, 
                   resolution: 'Resolution') -> List[BaseData]:
        """Get historical data for a symbol."""
        pass
    
    @abstractmethod
    def initialize(self, parameters: Dict[str, Any]) -> None:
        """Initialize the history provider."""
        pass
    
    @abstractmethod
    def initialize_subscription_manager(self, subscription_manager: 'SubscriptionManager') -> None:
        """Initialize with subscription manager."""
        pass