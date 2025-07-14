"""
ISubscriptionDataConfigService interface for managing subscription data configurations.
"""

from abc import ABC, abstractmethod
from typing import List


class ISubscriptionDataConfigService(ABC):
    """
    Interface for managing subscription data configurations.
    """
    
    @abstractmethod
    def add(self, symbol: 'Symbol', resolution: 'Resolution', 
           fill_forward: bool = True, extended_hours: bool = False) -> 'SubscriptionDataConfig':
        """Add a new subscription configuration."""
        pass
    
    @abstractmethod
    def remove(self, symbol: 'Symbol') -> bool:
        """Remove a subscription configuration."""
        pass
    
    @abstractmethod
    def get_subscriptions(self) -> List['SubscriptionDataConfig']:
        """Get all active subscription configurations."""
        pass