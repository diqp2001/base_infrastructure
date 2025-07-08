"""
IHistoryProvider interface for historical data providers.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any


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