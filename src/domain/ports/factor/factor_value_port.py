"""
Factor Port - Repository interface for Factor entities.

This port defines the contract for repositories that handle Factor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.factor_value import FactorValue


class FactorValuePort(ABC):
    """Port interface for Factor repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[FactorValue]:
        """
        Get factor by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            Factor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[FactorValue]:
        """
        Get factor by name.
        
        Args:
            name: The factor name
            
        Returns:
            Factor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_group(self, group: str) -> List[FactorValue]:
        """
        Get factors by group.
        
        Args:
            group: The factor group
            
        Returns:
            List of Factor entities in the group
        """
        pass
    
    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[FactorValue]:
        """
        Get factors by subgroup.
        
        Args:
            subgroup: The factor subgroup
            
        Returns:
            List of Factor entities in the subgroup
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[FactorValue]:
        """
        Get all factors.
        
        Returns:
            List of Factor entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: FactorValue) -> Optional[FactorValue]:
        """
        Add/persist a factor entity.
        
        Args:
            entity: The Factor entity to persist
            
        Returns:
            Persisted Factor entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: FactorValue) -> Optional[FactorValue]:
        """
        Update a factor entity.
        
        Args:
            entity: The Factor entity to update
            
        Returns:
            Updated Factor entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete a factor entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def get_all_dates_by_id_entity_id(self, factor_id: int, entity_id: int) -> List[str]:
        """
        Get all dates for a specific factor and entity combination.
        
        Args:
            factor_id: The factor ID
            entity_id: The entity ID
            
        Returns:
            List of date strings for the factor-entity combination
        """
        pass
    
    @abstractmethod
    def get_by_factor_entity_date(self, factor_id: int, entity_id: int, date_str: str) -> Optional[FactorValue]:
        """
        Get factor value by factor ID, entity ID, and date.
        
        Args:
            factor_id: The factor ID
            entity_id: The entity ID
            date_str: The date string
            
        Returns:
            FactorValue entity or None if not found
        """
        pass