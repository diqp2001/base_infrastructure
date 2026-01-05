"""
Index Future Port - Repository interface for Index Future entities.

This port defines the contract for repositories that handle Index Future
entities, ensuring both local and IBKR repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import date
from decimal import Decimal

from src.domain.entities.finance.financial_assets.derivatives.future.index_future import IndexFuture


class IndexFuturePort(ABC):
    """Port interface for Index Future repositories"""
    
    @abstractmethod
    def get_or_create(self, symbol: str) -> Optional[IndexFuture]:
        """
        Get or create an index future by symbol.
        
        Args:
            symbol: The future symbol (e.g., 'ESZ25', 'NQH25')
            
        Returns:
            IndexFuture entity or None if creation/retrieval failed
        """
        pass
    
    @abstractmethod
    def get_by_symbol(self, symbol: str) -> Optional[IndexFuture]:
        """
        Get index future by symbol.
        
        Args:
            symbol: The future symbol
            
        Returns:
            IndexFuture entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[IndexFuture]:
        """
        Get index future by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            IndexFuture entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[IndexFuture]:
        """
        Get all index futures.
        
        Returns:
            List of IndexFuture entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: IndexFuture) -> Optional[IndexFuture]:
        """
        Add/persist an index future entity.
        
        Args:
            entity: The IndexFuture entity to persist
            
        Returns:
            Persisted IndexFuture entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: IndexFuture) -> Optional[IndexFuture]:
        """
        Update an index future entity.
        
        Args:
            entity: The IndexFuture entity to update
            
        Returns:
            Updated IndexFuture entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete an index future entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass