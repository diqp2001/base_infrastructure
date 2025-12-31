"""
Core interfaces for the backtesting framework.
Defines the main algorithm interface that all trading algorithms must implement.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Iterator, List, Optional, Any, Type, Union

from .enums import Resolution
from .data_types import Slice, BaseData
from .orders import OrderEvent, OrderTicket
from .symbol import Symbol


class IAlgorithm(ABC):
    """
    Interface that all trading algorithms must implement.
    Defines the core lifecycle methods for algorithm execution.
    """
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Called once at the start of the algorithm to setup the initial state.
        This is where you should add securities, set parameters, and configure the algorithm.
        """
        pass
    
    @abstractmethod
    def on_data(self, data: Slice) -> None:
        """
        Called when new data arrives. This is the main event handler for market data.
        
        Args:
            data: Slice containing all available market data for the current time
        """
        pass
    @abstractmethod
    def _verify_and_import_data(self) -> Dict[str, Any]:
        """
        Called when   market data needs to be updated.
        
        
        """
        pass
    
    @abstractmethod
    def on_order_event(self, order_event: OrderEvent) -> None:
        """
        Called when an order event occurs (fill, partial fill, cancellation, etc.)
        
        Args:
            order_event: The order event that occurred
        """
        pass
    
    def on_end_of_day(self, symbol: Symbol) -> None:
        """
        Called at the end of each trading day for each security.
        
        Args:
            symbol: The symbol for which the day ended
        """
        pass
    
    def on_end_of_algorithm(self) -> None:
        """
        Called when the algorithm finishes execution.
        Use this for cleanup and final calculations.
        """
        pass
    
    def on_securities_changed(self, changes: Dict[str, List[Any]]) -> None:
        """
        Called when the universe of securities changes.
        
        Args:
            changes: Dictionary with 'added' and 'removed' keys containing lists of securities
        """
        pass
    
    def on_margin_call(self, requests: List[Dict[str, Any]]) -> None:
        """
        Called when a margin call occurs.
        
        Args:
            requests: List of margin call requests
        """
        pass
    
    def on_assignment(self, assignment_event: Dict[str, Any]) -> None:
        """
        Called when an option assignment occurs.
        
        Args:
            assignment_event: Details about the assignment
        """
        pass

class IAlgorithmFactory(ABC):
    """
    Interface for a factory that creates algorithm instances.
    """

    @abstractmethod
    def create_algorithm(self, algorithm_cls: Type[IAlgorithm], *args, **kwargs) -> IAlgorithm:
        """
        Creates and returns an instance of a trading algorithm.

        Args:
            algorithm_cls (Type[IAlgorithm]): The class of the algorithm to instantiate.
            *args: Positional arguments to pass to the algorithm constructor.
            **kwargs: Keyword arguments to pass to the algorithm constructor.

        Returns:
            IAlgorithm: An instance of the requested algorithm.
        """
        pass


class IDataProvider(ABC):
    """Interface for data providers that supply market data."""
    
    @abstractmethod
    def get_data(self, symbol: Symbol, start: datetime, end: datetime) -> List[BaseData]:
        """Get historical data for a symbol."""
        pass
    
    @abstractmethod
    def is_valid_time(self, time: datetime) -> bool:
        """Check if the given time is valid for data requests."""
        pass


class IBrokerageModel(ABC):
    """Interface for brokerage models that define trading rules and fees."""
    
    @abstractmethod
    def get_commission(self, order: 'Order') -> float:
        """Calculate commission for an order."""
        pass
    
    @abstractmethod
    def get_slippage(self, order: 'Order') -> float:
        """Calculate slippage for an order."""
        pass
    
    @abstractmethod
    def can_submit_order(self, order: 'Order') -> bool:
        """Check if an order can be submitted."""
        pass


class ISecurityInitializer(ABC):
    """Interface for security initialization strategies."""
    
    @abstractmethod
    def initialize(self, security: 'Security') -> None:
        """Initialize a security with default properties."""
        pass



class IUniverseSelectionModel(ABC):
    """Interface for universe selection models."""
    
    @abstractmethod
    def select_securities(self, time: datetime, data: Slice) -> List[Symbol]:
        """Select securities for the universe at the given time."""
        pass

class IDataFeed(ABC):
    
    @abstractmethod
    def subscribe(self, symbol: Symbol) -> None:
        """
        Subscribe to data for a specific symbol.
        
        Args:
            symbol: The symbol to subscribe to
        """
        pass

    @abstractmethod
    def unsubscribe(self, symbol: Symbol) -> None:
        """
        Unsubscribe from data for a specific symbol.
        
        Args:
            symbol: The symbol to unsubscribe from
        """
        pass

    @abstractmethod
    def get_next_slice(self) -> Optional[Slice]:
        """
        Retrieve the next slice of market data.
        
        Returns:
            A Slice object containing the next set of market data,
            or None if no more data is available
        """
        pass

    @abstractmethod
    def has_data(self) -> bool:
        """
        Check if the feed has more data to provide.
        
        Returns:
            True if more data is available, False otherwise
        """
        pass

    def reset(self) -> None:
        """
        Reset the data feed to its initial state.
        Useful when restarting a backtest or simulation.
        """
        pass
"""
Interface for data readers that parse raw files/APIs into BaseData objects.
"""




class IDataReader(ABC):
    """
    Defines the interface for reading raw data into BaseData objects.
    Implementations should handle different sources (CSV, API, database).
    """

    @abstractmethod
    def read(self, symbol: Symbol, start: datetime, end: datetime) -> Iterator[BaseData]:
        """
        Reads data for a given symbol and date range.

        Args:
            symbol (Symbol): The asset symbol.
            start (datetime): Start time of data request.
            end (datetime): End time of data request.

        Returns:
            Iterator[BaseData]: A stream of BaseData objects.
        """
        pass

    @abstractmethod
    def get_latest(self, symbol: Symbol) -> Optional[BaseData]:
        """
        Gets the most recent data point available for the symbol.

        Args:
            symbol (Symbol): The asset symbol.

        Returns:
            Optional[BaseData]: Latest data object if available, otherwise None.
        """
        pass

    @abstractmethod
    def supports(self, symbol: Symbol) -> bool:
        """
        Checks if this data reader can handle the given symbol.

        Args:
            symbol (Symbol): The asset symbol.

        Returns:
            bool: True if supported, False otherwise.
        """
        pass


class IHistoryProvider(ABC):
    """
    Interface for history providers that supply historical market data.
    Algorithms will use implementations of this interface to request past data.
    """

    @abstractmethod
    def get_history(
        self,
        symbols: List[Symbol],
        start: datetime,
        end: datetime,
        resolution: Resolution
    ) -> Dict[Symbol, List[BaseData]]:
        """
        Retrieve historical market data for a list of symbols.

        Args:
            symbols: List of symbols to retrieve data for.
            start: Start datetime (inclusive).
            end: End datetime (inclusive).
            resolution: Resolution of the data (Tick, Minute, Hour, Daily, etc.)

        Returns:
            Dictionary where each symbol maps to a list of BaseData objects.
        """
        pass

    @abstractmethod
    def get_last(self, symbol: Symbol, count: int, resolution: Resolution) -> List[BaseData]:
        """
        Retrieve the most recent `count` data points for a symbol at a given resolution.

        Args:
            symbol: The symbol to retrieve data for.
            count: Number of most recent data points to retrieve.
            resolution: Resolution of the data.

        Returns:
            List of BaseData objects, most recent last.
        """
        pass

    @abstractmethod
    def has_data(self, symbol: Symbol, time: datetime) -> bool:
        """
        Check if historical data is available for a symbol at a given time.

        Args:
            symbol: Symbol to check.
            time: Datetime to check availability for.

        Returns:
            True if data is available, False otherwise.
        """
        pass




class IApi(ABC):
    """
    Interface for interacting with an algorithmic trading system via API.
    Defines methods for submitting orders, retrieving data, and managing algorithms.
    """

    @abstractmethod
    def get_algorithm_status(self, algorithm_id: str) -> str:
        """
        Get the current status of the algorithm.

        Args:
            algorithm_id (str): Identifier of the algorithm.

        Returns:
            str: Current status of the algorithm (e.g., 'Running', 'Stopped').
        """
        pass

    @abstractmethod
    def submit_order(self, algorithm_id: str, order_details: Dict[str, Any]) -> str:
        """
        Submit a new order to the trading system.

        Args:
            algorithm_id (str): Identifier of the algorithm.
            order_details (Dict[str, Any]): Order parameters (symbol, quantity, type, etc.)

        Returns:
            str: Order identifier.
        """
        pass

    @abstractmethod
    def get_orders(self, algorithm_id: str) -> List[Dict[str, Any]]:
        """
        Retrieve all orders submitted by the algorithm.

        Args:
            algorithm_id (str): Identifier of the algorithm.

        Returns:
            List[Dict[str, Any]]: List of order information dictionaries.
        """
        pass

    @abstractmethod
    def cancel_order(self, algorithm_id: str, order_id: str) -> bool:
        """
        Cancel a submitted order.

        Args:
            algorithm_id (str): Identifier of the algorithm.
            order_id (str): Identifier of the order to cancel.

        Returns:
            bool: True if cancellation succeeded, False otherwise.
        """
        pass

    @abstractmethod
    def get_algorithm_logs(self, algorithm_id: str, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None) -> List[str]:
        """
        Retrieve logs from the algorithm within a given time frame.

        Args:
            algorithm_id (str): Identifier of the algorithm.
            start_time (datetime, optional): Start of time range.
            end_time (datetime, optional): End of time range.

        Returns:
            List[str]: List of log entries.
        """
        pass

    @abstractmethod
    def get_algorithm_results(self, algorithm_id: str) -> Dict[str, Any]:
        """
        Retrieve the results and performance metrics of the algorithm.

        Args:
            algorithm_id (str): Identifier of the algorithm.

        Returns:
            Dict[str, Any]: Dictionary of result metrics (returns, drawdown, etc.)
        """
        pass

    @abstractmethod
    def upload_data(self, algorithm_id: str, data: Any) -> bool:
        """
        Upload custom data for use by the algorithm.

        Args:
            algorithm_id (str): Identifier of the algorithm.
            data (Any): Data payload (e.g., CSV, JSON, DataFrame)

        Returns:
            bool: True if upload succeeded, False otherwise.
        """
        pass
