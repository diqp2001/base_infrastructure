"""
Currency Port - Repository interface for Currency entities.

This port defines the contract for repositories that handle Currency
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from decimal import Decimal

from src.domain.entities.finance.financial_assets.currency import Currency


class CurrencyPort(ABC):
    """Port interface for Currency repositories"""
    
    @abstractmethod
    def get_or_create(self, symbol: str) -> Optional[Currency]:
        """
        Get or create a currency by symbol.
        
        Args:
            symbol: The currency symbol (e.g., 'USD', 'EUR', 'GBP')
            
        Returns:
            Currency entity or None if creation/retrieval failed
        """
        pass
    
    @abstractmethod
    def get_by_symbol(self, symbol: str) -> Optional[Currency]:
        """
        Get currency by symbol.
        
        Args:
            symbol: The currency symbol
            
        Returns:
            Currency entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_iso_code(self, iso_code: str) -> Optional[Currency]:
        """
        Get currency by ISO code.
        
        Args:
            iso_code: The ISO currency code
            
        Returns:
            Currency entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[Currency]:
        """
        Get currency by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            Currency entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[Currency]:
        """
        Get all currencies.
        
        Returns:
            List of Currency entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: Currency) -> Optional[Currency]:
        """
        Add/persist a currency entity.
        
        Args:
            entity: The Currency entity to persist
            
        Returns:
            Persisted Currency entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: Currency) -> Optional[Currency]:
        """
        Update a currency entity.
        
        Args:
            entity: The Currency entity to update
            
        Returns:
            Updated Currency entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete a currency entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass