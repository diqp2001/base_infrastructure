"""
Core interfaces for the backtesting framework.
Defines the main algorithm interface that all trading algorithms must implement.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
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