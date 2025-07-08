"""
IBrokerageModel interface for brokerage models.
"""

from abc import ABC, abstractmethod
from decimal import Decimal


class IBrokerageModel(ABC):
    """
    Interface for brokerage models.
    Defines commission, fees, and order execution rules.
    """
    
    @abstractmethod
    def get_order_fee(self, order: 'Order') -> Decimal:
        """Calculate the order fee for the given order."""
        pass
    
    @abstractmethod
    def can_submit_order(self, security: 'Security', order: 'Order') -> bool:
        """Determine if the order can be submitted."""
        pass
    
    @abstractmethod
    def can_update_order(self, security: 'Security', order: 'Order') -> bool:
        """Determine if the order can be updated."""
        pass
    
    @abstractmethod
    def can_execute_order(self, security: 'Security', order: 'Order') -> bool:
        """Determine if the order can be executed."""
        pass