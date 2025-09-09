"""
Portfolio Construction Model Base Class

This module provides the base class for all portfolio construction models
in the backtesting framework. It defines the interface that all portfolio
construction models must implement.

Based on QuantConnect Lean's portfolio construction model pattern.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import the IAlgorithm interface to ensure proper relationship
from ...common.interfaces.ialgorithm import IAlgorithm


class PortfolioConstructionModel(IAlgorithm):
    """
    Base class for portfolio construction models.
    
    Portfolio construction models are responsible for determining how to 
    allocate capital across selected securities based on alpha signals,
    risk constraints, and optimization objectives.
    
    This class provides the common interface that all portfolio construction
    models must implement, ensuring consistency across different optimization
    strategies.
    
    Inherits from IAlgorithm to ensure proper algorithm lifecycle management.
    """
    
    def __init__(self):
        """Initialize the portfolio construction model."""
        self.name = self.__class__.__name__
        self.is_initialized = False
        self.last_rebalance_time = None
        self.rebalance_frequency = 30  # Default rebalance frequency in days
        
    @abstractmethod
    def create_targets(self, alpha_signals: Dict[str, float]) -> Dict[str, float]:
        """
        Create portfolio targets based on alpha signals.
        
        Args:
            alpha_signals: Dictionary mapping symbols to alpha values
            
        Returns:
            Dictionary mapping symbols to target portfolio weights
        """
        pass
    
    # IAlgorithm interface methods that must be implemented by concrete classes
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
    def on_securities_changed(self, changes: 'SecurityChanges') -> None:
        """
        Handle changes in the security universe.
        
        This method is called whenever securities are added or removed
        from the algorithm's universe.
        
        Args:
            changes: SecurityChanges object containing added/removed securities
        """
        pass
    
    @abstractmethod
    def on_assignment(self, assignment_event: 'AssignmentEvent') -> None:
        """
        Handle option assignment events.
        
        Args:
            assignment_event: The assignment event details
        """
        pass
    
    @abstractmethod
    def on_delistings(self, delistings: 'Delistings') -> None:
        """
        Handle security delistings.
        
        Args:
            delistings: The delisting notifications
        """
        pass
    
    @abstractmethod
    def on_dividend_events(self, dividend_events: 'DividendEvents') -> None:
        """
        Handle dividend events.
        
        Args:
            dividend_events: The dividend events
        """
        pass
    
    @abstractmethod
    def on_end_of_algorithm(self) -> None:
        """
        Handle end of algorithm execution.
        
        This method is called when the algorithm is shutting down.
        Use this for cleanup or final calculations.
        """
        pass
    
    @abstractmethod
    def on_end_of_day(self, symbol: 'Symbol') -> None:
        """
        Handle end of day events.
        
        Args:
            symbol: The symbol for which the trading day has ended
        """
        pass
    
    @abstractmethod
    def on_margin_call(self, requests: List['SubmitOrderRequest']) -> List['SubmitOrderRequest']:
        """
        Handle margin call events.
        
        Args:
            requests: List of order requests to handle margin call
            
        Returns:
            Modified list of order requests
        """
        pass
    
    @abstractmethod
    def on_split_events(self, split_events: 'SplitEvents') -> None:
        """
        Handle stock split events.
        
        Args:
            split_events: The split events
        """
        pass
    
    @abstractmethod
    def on_symbol_changed_events(self, symbol_changed_events: 'SymbolChangedEvents') -> None:
        """
        Handle symbol change events.
        
        Args:
            symbol_changed_events: The symbol change events
        """
        pass
    
    def should_rebalance(self) -> bool:
        """
        Determine if the portfolio should be rebalanced.
        
        Default implementation uses a simple time-based approach.
        Subclasses can override this method to implement custom logic.
        
        Returns:
            True if rebalancing is needed, False otherwise
        """
        if self.last_rebalance_time is None:
            return True
        
        # Simple time-based rebalancing
        days_since_rebalance = (datetime.now() - self.last_rebalance_time).days
        return days_since_rebalance >= self.rebalance_frequency
    
    def get_name(self) -> str:
        """
        Get the name of the portfolio construction model.
        
        Returns:
            The model name
        """
        return self.name
    
    def is_model_initialized(self) -> bool:
        """
        Check if the model has been initialized.
        
        Returns:
            True if initialized, False otherwise
        """
        return self.is_initialized
    
    def set_rebalance_frequency(self, frequency: int) -> None:
        """
        Set the rebalancing frequency.
        
        Args:
            frequency: Rebalance frequency in days
        """
        self.rebalance_frequency = frequency
    
    def get_rebalance_frequency(self) -> int:
        """
        Get the current rebalancing frequency.
        
        Returns:
            Rebalance frequency in days
        """
        return self.rebalance_frequency
    
    def mark_rebalanced(self) -> None:
        """
        Mark that a rebalance has occurred.
        
        This updates the last rebalance time to the current time.
        """
        self.last_rebalance_time = datetime.now()
    
    def get_last_rebalance_time(self) -> Optional[datetime]:
        """
        Get the time of the last rebalance.
        
        Returns:
            DateTime of last rebalance, or None if never rebalanced
        """
        return self.last_rebalance_time
    
    def validate_targets(self, targets: Dict[str, float]) -> Dict[str, float]:
        """
        Validate and normalize portfolio targets.
        
        This method ensures targets are valid and sum to 1.0.
        
        Args:
            targets: Dictionary of target portfolio weights
            
        Returns:
            Validated and normalized targets
        """
        if not targets:
            return {}
        
        # Remove any None or invalid values
        valid_targets = {k: v for k, v in targets.items() if v is not None and isinstance(v, (int, float))}
        
        # Ensure non-negative weights (can be overridden by subclasses for long-short)
        positive_targets = {k: max(0.0, v) for k, v in valid_targets.items()}
        
        # Normalize to sum to 1.0
        total_weight = sum(positive_targets.values())
        if total_weight > 0:
            normalized_targets = {k: v / total_weight for k, v in positive_targets.items()}
        else:
            normalized_targets = {}
        
        return normalized_targets
    
    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about the portfolio construction model.
        
        Returns:
            Dictionary containing model information
        """
        return {
            'name': self.name,
            'is_initialized': self.is_initialized,
            'rebalance_frequency': self.rebalance_frequency,
            'last_rebalance_time': self.last_rebalance_time,
            'model_type': 'PortfolioConstructionModel'
        }


class EqualWeightPortfolioConstructionModel(PortfolioConstructionModel):
    """
    Simple equal weight portfolio construction model.
    
    This model allocates equal weights to all securities in the universe.
    Useful as a baseline or for simple diversification strategies.
    """
    
    def __init__(self):
        super().__init__()
        self.is_initialized = True
    
    def create_targets(self, alpha_signals: Dict[str, float]) -> Dict[str, float]:
        """
        Create equal weight targets for all securities.
        
        Args:
            alpha_signals: Dictionary mapping symbols to alpha values
            
        Returns:
            Dictionary with equal weights for all symbols
        """
        if not alpha_signals:
            return {}
        
        num_securities = len(alpha_signals)
        equal_weight = 1.0 / num_securities
        
        targets = {symbol: equal_weight for symbol in alpha_signals.keys()}
        return self.validate_targets(targets)
    
    def initialize(self) -> None:
        """Initialize the equal weight portfolio construction model."""
        self.is_initialized = True
        
    def on_data(self, data: 'Slice') -> None:
        """Process market data for equal weight model."""
        pass
        
    def on_order_event(self, order_event: 'OrderEvent') -> None:
        """Handle order events."""
        pass
    
    def on_securities_changed(self, changes: 'SecurityChanges') -> None:
        """Handle security universe changes."""
        pass
    
    def on_assignment(self, assignment_event: 'AssignmentEvent') -> None:
        """Handle option assignment events."""
        pass
    
    def on_delistings(self, delistings: 'Delistings') -> None:
        """Handle security delistings."""
        pass
    
    def on_dividend_events(self, dividend_events: 'DividendEvents') -> None:
        """Handle dividend events."""
        pass
    
    def on_end_of_algorithm(self) -> None:
        """Handle end of algorithm execution."""
        pass
    
    def on_end_of_day(self, symbol: 'Symbol') -> None:
        """Handle end of day events."""
        pass
    
    def on_margin_call(self, requests: List['SubmitOrderRequest']) -> List['SubmitOrderRequest']:
        """Handle margin call events."""
        return requests
    
    def on_split_events(self, split_events: 'SplitEvents') -> None:
        """Handle stock split events."""
        pass
    
    def on_symbol_changed_events(self, symbol_changed_events: 'SymbolChangedEvents') -> None:
        """Handle symbol change events."""
        pass