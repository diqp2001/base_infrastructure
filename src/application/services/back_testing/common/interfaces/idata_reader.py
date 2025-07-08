"""
IDataReader interface for data readers.
"""

from abc import ABC, abstractmethod
from typing import List


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