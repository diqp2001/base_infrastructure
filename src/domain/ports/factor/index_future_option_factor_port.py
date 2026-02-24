"""
Index Future Option Factor Port - Repository interface for IndexFutureOptionFactor entities.

This port defines the contract for repositories that handle IndexFutureOptionFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.index_future_option_factor import IndexFutureOptionFactor


class IndexFutureOptionFactorPort(ABC):
    """Port interface for IndexFutureOptionFactor repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[IndexFutureOptionFactor]:
        """
        Get index future option factor by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            IndexFutureOptionFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[IndexFutureOptionFactor]:
        """
        Get index future option factor by name.
        
        Args:
            name: The factor name
            
        Returns:
            IndexFutureOptionFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_group(self, group: str) -> List[IndexFutureOptionFactor]:
        """
        Get index future option factors by group.
        
        Args:
            group: The factor group
            
        Returns:
            List of IndexFutureOptionFactor entities in the group
        """
        pass
    
    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[IndexFutureOptionFactor]:
        """
        Get index future option factors by subgroup.
        
        Args:
            subgroup: The factor subgroup
            
        Returns:
            List of IndexFutureOptionFactor entities in the subgroup
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[IndexFutureOptionFactor]:
        """
        Get all index future option factors.
        
        Returns:
            List of IndexFutureOptionFactor entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: IndexFutureOptionFactor) -> Optional[IndexFutureOptionFactor]:
        """
        Add/persist an index future option factor entity.
        
        Args:
            entity: The IndexFutureOptionFactor entity to persist
            
        Returns:
            Persisted IndexFutureOptionFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: IndexFutureOptionFactor) -> Optional[IndexFutureOptionFactor]:
        """
        Update an index future option factor entity.
        
        Args:
            entity: The IndexFutureOptionFactor entity to update
            
        Returns:
            Updated IndexFutureOptionFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete an index future option factor entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass