"""
Core interfaces for the QuantConnect Lean Python implementation.
These define the contracts that various components must implement.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Callable
from decimal import Decimal


class IAlgorithm(ABC):
    """
    Main interface defining the contract for trading algorithms.
    This is the core interface that all algorithms must implement.
    """
    
    @abstractmethod
    def initialize(self) -> None:
        """Called once at the start of the algorithm to setup initial state."""
        pass
    
    @abstractmethod
    def on_data(self, data: 'Slice') -> None:
        """Called when new market data arrives."""
        pass
    
    @abstractmethod
    def on_order_event(self, order_event: 'OrderEvent') -> None:
        """Called when an order event occurs."""
        pass


class IDataFeed(ABC):
    """
    Interface for data feed implementations.
    Defines contract for both live and backtesting data feeds.
    """
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the data feed."""
        pass
    
    @abstractmethod
    def create_subscription(self, symbol: 'Symbol', resolution: 'Resolution') -> 'SubscriptionDataConfig':
        """Create a data subscription for the given symbol and resolution."""
        pass
    
    @abstractmethod
    def remove_subscription(self, config: 'SubscriptionDataConfig') -> bool:
        """Remove a data subscription."""
        pass
    
    @abstractmethod
    def get_next_ticks(self) -> List['BaseData']:
        """Get the next batch of data ticks."""
        pass


class IResultHandler(ABC):
    """
    Interface for handling algorithm results.
    Processes trades, portfolio updates, and performance metrics.
    """
    
    @abstractmethod
    def initialize(self) -> None:
        """Initialize the result handler."""
        pass
    
    @abstractmethod
    def process_synchronous_events(self, algorithm: IAlgorithm) -> None:
        """Process algorithm events synchronously."""
        pass
    
    @abstractmethod
    def store_result(self, packet: Dict[str, Any]) -> None:
        """Store a result packet."""
        pass
    
    @abstractmethod
    def send_final_result(self) -> None:
        """Send the final results."""
        pass


class IApi(ABC):
    """
    Interface for API communication with external services.
    Handles authentication, project management, and data upload/download.
    """
    
    @abstractmethod
    def authenticate(self, token: str) -> bool:
        """Authenticate with the API using the provided token."""
        pass
    
    @abstractmethod
    def create_project(self, name: str, language: str) -> Dict[str, Any]:
        """Create a new project."""
        pass
    
    @abstractmethod
    def read_project(self, project_id: int) -> Dict[str, Any]:
        """Read project details."""
        pass
    
    @abstractmethod
    def update_project(self, project_id: int, **kwargs) -> Dict[str, Any]:
        """Update project details."""
        pass
    
    @abstractmethod
    def delete_project(self, project_id: int) -> bool:
        """Delete a project."""
        pass


class IHistoryProvider(ABC):
    """
    Interface for historical data providers.
    Provides historical market data for backtesting.
    """
    
    @abstractmethod
    def get_history(self, symbol: 'Symbol', start: datetime, end: datetime, 
                   resolution: 'Resolution') -> List['BaseData']:
        """Get historical data for the specified parameters."""
        pass
    
    @abstractmethod
    def initialize(self, parameters: Dict[str, Any]) -> None:
        """Initialize the history provider with configuration parameters."""
        pass


class IDataReader(ABC):
    """
    Interface for data readers.
    Reads data from various sources and formats.
    """
    
    @abstractmethod
    def read(self, config: 'SubscriptionDataConfig') -> List['BaseData']:
        """Read data based on the subscription configuration."""
        pass
    
    @abstractmethod
    def supports_mapping(self) -> bool:
        """Returns true if this reader supports symbol mapping."""
        pass


class IOrderProcessor(ABC):
    """
    Interface for order processing.
    Handles order validation, execution, and fills.
    """
    
    @abstractmethod
    def process_order(self, order: 'Order') -> 'OrderEvent':
        """Process an order and return the resulting order event."""
        pass
    
    @abstractmethod
    def scan_for_fills(self, orders: List['Order'], bars: Dict['Symbol', 'BaseData']) -> List['OrderEvent']:
        """Scan for order fills based on current market data."""
        pass


class IAlgorithmFactory(ABC):
    """
    Interface for algorithm factories.
    Creates and loads algorithm instances.
    """
    
    @abstractmethod
    def create_algorithm_instance(self, algorithm_name: str, **kwargs) -> IAlgorithm:
        """Create an instance of the specified algorithm."""
        pass
    
    @abstractmethod
    def load_algorithm(self, path: str) -> IAlgorithm:
        """Load an algorithm from the specified path."""
        pass


class IEngine(ABC):
    """
    Interface for the main execution engine.
    Orchestrates algorithm execution, data feeds, and result processing.
    """
    
    @abstractmethod
    def initialize_algorithm(self, algorithm: IAlgorithm) -> None:
        """Initialize the algorithm for execution."""
        pass
    
    @abstractmethod
    def run(self) -> None:
        """Run the algorithm."""
        pass
    
    @abstractmethod
    def stop(self) -> None:
        """Stop the algorithm execution."""
        pass
    
    @abstractmethod
    def dispose(self) -> None:
        """Clean up engine resources."""
        pass


class ISubscriptionDataConfigService(ABC):
    """
    Interface for managing subscription data configurations.
    """
    
    @abstractmethod
    def add(self, symbol: 'Symbol', resolution: 'Resolution', 
           fill_forward: bool = True, extended_hours: bool = False) -> 'SubscriptionDataConfig':
        """Add a new subscription configuration."""
        pass
    
    @abstractmethod
    def remove(self, symbol: 'Symbol') -> bool:
        """Remove a subscription configuration."""
        pass
    
    @abstractmethod
    def get_subscriptions(self) -> List['SubscriptionDataConfig']:
        """Get all active subscription configurations."""
        pass


class IBrokerageModel(ABC):
    """
    Interface for brokerage models.
    Defines commission, fees, and order execution rules.
    """
    
    @abstractmethod
    def get_order_fee(self, order: 'Order') -> Decimal:
        """Calculate the order fee for the given order."""
        pass
    
    @abstractmethod
    def can_submit_order(self, security: 'Security', order: 'Order') -> bool:
        """Determine if the order can be submitted."""
        pass
    
    @abstractmethod
    def can_update_order(self, security: 'Security', order: 'Order') -> bool:
        """Determine if the order can be updated."""
        pass
    
    @abstractmethod
    def can_execute_order(self, security: 'Security', order: 'Order') -> bool:
        """Determine if the order can be executed."""
        pass