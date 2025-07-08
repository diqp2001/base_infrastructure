"""
IAlgorithm interface - core interface for all trading algorithms.
Based on QuantConnect Lean's IAlgorithm.cs interface.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, Union, Callable
from decimal import Decimal


class IAlgorithm(ABC):
    """
    Main interface defining the contract for trading algorithms.
    This is the core interface that all algorithms must implement.
    
    Based on QuantConnect Lean's IAlgorithm interface, this provides
    the fundamental methods required for algorithm execution.
    """
    
    @abstractmethod
    def initialize(self) -> None:
        """
        Called once at the start of the algorithm to setup initial state.
        This is where you would configure your algorithm parameters,
        add securities, set up indicators, etc.
        """
        pass
    
    @abstractmethod
    def on_data(self, data: 'Slice') -> None:
        """
        Called when new market data arrives.
        This is the main data event handler where you implement your trading logic.
        
        Args:
            data: The current data slice containing market data for subscribed securities
        """
        pass
    
    @abstractmethod
    def on_order_event(self, order_event: 'OrderEvent') -> None:
        """
        Called when an order event occurs (fill, partial fill, cancellation, etc.).
        
        Args:
            order_event: The order event containing details about the order status change
        """
        pass
    
    @abstractmethod
    def on_end_of_day(self, symbol: 'Symbol') -> None:
        """
        Called at the end of each trading day.
        
        Args:
            symbol: The symbol for which the trading day has ended
        """
        pass
    
    @abstractmethod
    def on_end_of_algorithm(self) -> None:
        """
        Called at the end of the algorithm execution.
        Use this for any cleanup or final calculations.
        """
        pass
    
    @abstractmethod
    def on_securities_changed(self, changes: 'SecurityChanges') -> None:
        """
        Called when securities are added or removed from the algorithm.
        
        Args:
            changes: The security changes that occurred
        """
        pass
    
    @abstractmethod
    def on_margin_call(self, requests: List['SubmitOrderRequest']) -> List['SubmitOrderRequest']:
        """
        Called when a margin call occurs.
        
        Args:
            requests: The list of orders to be submitted to handle the margin call
            
        Returns:
            List of orders to submit to handle the margin call
        """
        pass
    
    @abstractmethod
    def on_assignment(self, assignment_event: 'AssignmentEvent') -> None:
        """
        Called when an option assignment occurs.
        
        Args:
            assignment_event: The assignment event details
        """
        pass
    
    @abstractmethod
    def on_delistings(self, delistings: 'Delistings') -> None:
        """
        Called when securities are delisted.
        
        Args:
            delistings: The delisting notifications
        """
        pass
    
    @abstractmethod
    def on_symbol_changed_events(self, symbol_changed_events: 'SymbolChangedEvents') -> None:
        """
        Called when symbol changes occur (e.g., ticker symbol changes).
        
        Args:
            symbol_changed_events: The symbol change events
        """
        pass
    
    @abstractmethod
    def on_split_events(self, split_events: 'SplitEvents') -> None:
        """
        Called when stock splits occur.
        
        Args:
            split_events: The split events
        """
        pass
    
    @abstractmethod
    def on_dividend_events(self, dividend_events: 'DividendEvents') -> None:
        """
        Called when dividend events occur.
        
        Args:
            dividend_events: The dividend events
        """
        pass