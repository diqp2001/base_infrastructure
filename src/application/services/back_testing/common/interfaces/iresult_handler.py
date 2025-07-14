"""
IResultHandler interface for handling algorithm results.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any


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
    def process_synchronous_events(self, algorithm: 'IAlgorithm') -> None:
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