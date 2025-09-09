"""
Base algorithm implementation for the infrastructure layer.
"""

from abc import ABC
from typing import List

from ...application.services.misbuffet.common.interfaces import IAlgorithm
from ...application.services.misbuffet.common.symbol import Symbol
from ...application.services.misbuffet.common.data_types import BaseData
from ...application.services.misbuffet.algorithm.data_handlers import Slice
from ...application.services.misbuffet.algorithm.order import OrderEvent


class BaseAlgorithm(IAlgorithm, ABC):
    """
    Base implementation of IAlgorithm interface for infrastructure layer.
    
    This class provides a concrete implementation of the IAlgorithm interface
    and can be extended by specific algorithm implementations in the infrastructure.
    """
    
    def __init__(self):
        """Initialize the base algorithm."""
        self._initialized = False
        self._symbols: List[Symbol] = []
        self._data_history: List[BaseData] = []
    
    def initialize(self) -> None:
        """
        Called once at the start of the algorithm to setup initial state.
        Override this method in derived classes to implement specific initialization logic.
        """
        self._initialized = True
    
    def on_data(self, data: Slice) -> None:
        """
        Called when new market data arrives.
        Override this method in derived classes to implement trading logic.
        
        Args:
            data: The current data slice containing market data for subscribed securities
        """
        pass
    
    def on_order_event(self, order_event: OrderEvent) -> None:
        """
        Called when an order event occurs.
        Override this method in derived classes to handle order events.
        
        Args:
            order_event: The order event containing details about the order status change
        """
        pass
    
    def on_end_of_day(self, symbol: Symbol) -> None:
        """
        Called at the end of each trading day.
        Override this method in derived classes to handle end-of-day processing.
        
        Args:
            symbol: The symbol for which the trading day has ended
        """
        pass
    
    def on_end_of_algorithm(self) -> None:
        """
        Called at the end of the algorithm execution.
        Override this method in derived classes for cleanup or final calculations.
        """
        pass
    
    def on_securities_changed(self, changes: 'SecurityChanges') -> None:
        """
        Called when securities are added or removed from the algorithm.
        Override this method in derived classes to handle security changes.
        
        Args:
            changes: The security changes that occurred
        """
        pass
    
    def on_margin_call(self, requests: List['SubmitOrderRequest']) -> List['SubmitOrderRequest']:
        """
        Called when a margin call occurs.
        Override this method in derived classes to handle margin calls.
        
        Args:
            requests: The list of orders to be submitted to handle the margin call
            
        Returns:
            List of orders to submit to handle the margin call
        """
        return requests
    
    def on_assignment(self, assignment_event: 'AssignmentEvent') -> None:
        """
        Called when an option assignment occurs.
        Override this method in derived classes to handle assignments.
        
        Args:
            assignment_event: The assignment event details
        """
        pass
    
    def on_delistings(self, delistings: 'Delistings') -> None:
        """
        Called when securities are delisted.
        Override this method in derived classes to handle delistings.
        
        Args:
            delistings: The delisting notifications
        """
        pass
    
    def on_symbol_changed_events(self, symbol_changed_events: 'SymbolChangedEvents') -> None:
        """
        Called when symbol changes occur.
        Override this method in derived classes to handle symbol changes.
        
        Args:
            symbol_changed_events: The symbol change events
        """
        pass
    
    def on_split_events(self, split_events: 'SplitEvents') -> None:
        """
        Called when stock splits occur.
        Override this method in derived classes to handle splits.
        
        Args:
            split_events: The split events
        """
        pass
    
    def on_dividend_events(self, dividend_events: 'DividendEvents') -> None:
        """
        Called when dividend events occur.
        Override this method in derived classes to handle dividends.
        
        Args:
            dividend_events: The dividend events
        """
        pass
    
    @property
    def is_initialized(self) -> bool:
        """Check if the algorithm has been initialized."""
        return self._initialized
    
    @property
    def symbols(self) -> List[Symbol]:
        """Get the list of symbols being tracked."""
        return self._symbols.copy()
    
    def add_symbol(self, symbol: Symbol) -> None:
        """Add a symbol to track."""
        if symbol not in self._symbols:
            self._symbols.append(symbol)
    
    def remove_symbol(self, symbol: Symbol) -> None:
        """Remove a symbol from tracking."""
        if symbol in self._symbols:
            self._symbols.remove(symbol)