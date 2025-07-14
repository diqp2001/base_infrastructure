"""
IDataFeed interface for data feed implementations.
"""

from abc import ABC, abstractmethod
from typing import List


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