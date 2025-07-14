"""
SecurityDataFilter class for filtering security data.
"""

from abc import ABC, abstractmethod
from typing import List
from ..data_types import BaseData


class SecurityDataFilter(ABC):
    """
    Abstract base class for filtering security data.
    """
    
    @abstractmethod
    def filter(self, data: List[BaseData]) -> List[BaseData]:
        """
        Filter the provided data and return the filtered result.
        
        Args:
            data: The data to filter
            
        Returns:
            The filtered data
        """
        pass


class DefaultSecurityDataFilter(SecurityDataFilter):
    """
    Default implementation that passes through all data.
    """
    
    def filter(self, data: List[BaseData]) -> List[BaseData]:
        """Return all data without filtering."""
        return data


class PriceRangeFilter(SecurityDataFilter):
    """
    Filter that removes data outside of a specified price range.
    """
    
    def __init__(self, min_price: float = 0.0, max_price: float = float('inf')):
        self.min_price = min_price
        self.max_price = max_price
    
    def filter(self, data: List[BaseData]) -> List[BaseData]:
        """Filter data based on price range."""
        return [
            d for d in data 
            if self.min_price <= float(d.price) <= self.max_price
        ]


class VolumeFilter(SecurityDataFilter):
    """
    Filter that removes data with volume below a threshold.
    """
    
    def __init__(self, min_volume: int = 0):
        self.min_volume = min_volume
    
    def filter(self, data: List[BaseData]) -> List[BaseData]:
        """Filter data based on minimum volume."""
        return [
            d for d in data 
            if hasattr(d, 'volume') and d.volume >= self.min_volume
        ]