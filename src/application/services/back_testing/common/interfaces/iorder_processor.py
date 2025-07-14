"""
IOrderProcessor interface for order processing.
"""

from abc import ABC, abstractmethod
from typing import List, Dict


class IOrderProcessor(ABC):
    """
    Interface for order processing.
    Handles order validation, execution, and fills.
    """
    
    @abstractmethod
    def process_order(self, order: 'Order') -> 'OrderEvent':
        """Process an order and return the resulting order event."""
        pass
    
    @abstractmethod
    def scan_for_fills(self, orders: List['Order'], bars: Dict['Symbol', 'BaseData']) -> List['OrderEvent']:
        """Scan for order fills based on current market data."""
        pass