"""
IndexFuturePriceReturnFactor Port - Repository interface for IndexFuturePriceReturnFactor entities.

This port defines the contract for repositories that handle IndexFuturePriceReturnFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.future.index_future_price_return_factor import IndexFuturePriceReturnFactor


class IndexFuturePriceReturnFactorPort(ABC):
    """Port interface for IndexFuturePriceReturnFactor repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[IndexFuturePriceReturnFactor]:
        """
        Get index future price return factor by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            IndexFuturePriceReturnFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[IndexFuturePriceReturnFactor]:
        """
        Get index future price return factor by name.
        
        Args:
            name: The factor name
            
        Returns:
            IndexFuturePriceReturnFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_group(self, group: str) -> List[IndexFuturePriceReturnFactor]:
        """
        Get index future price return factors by group.
        
        Args:
            group: The factor group
            
        Returns:
            List of IndexFuturePriceReturnFactor entities in the group
        """
        pass
    
    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[IndexFuturePriceReturnFactor]:
        """
        Get index future price return factors by subgroup.
        
        Args:
            subgroup: The factor subgroup
            
        Returns:
            List of IndexFuturePriceReturnFactor entities in the subgroup
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[IndexFuturePriceReturnFactor]:
        """
        Get all index future price return factors.
        
        Returns:
            List of IndexFuturePriceReturnFactor entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: IndexFuturePriceReturnFactor) -> Optional[IndexFuturePriceReturnFactor]:
        """
        Add/persist an index future price return factor entity.
        
        Args:
            entity: The IndexFuturePriceReturnFactor entity to persist
            
        Returns:
            Persisted IndexFuturePriceReturnFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: IndexFuturePriceReturnFactor) -> Optional[IndexFuturePriceReturnFactor]:
        """
        Update an index future price return factor entity.
        
        Args:
            entity: The IndexFuturePriceReturnFactor entity to update
            
        Returns:
            Updated IndexFuturePriceReturnFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete an index future price return factor entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass