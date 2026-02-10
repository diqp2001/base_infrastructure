"""
Factor Dependency Port - Repository interface for FactorDependency entities.

This port defines the contract for repositories that handle FactorDependency
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.factor_dependency import FactorDependency


class FactorDependencyPort(ABC):
    """Port interface for FactorDependency repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[FactorDependency]:
        """
        Get factor dependency by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            FactorDependency entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_dependent_factor_id(self, dependent_factor_id: int) -> List[FactorDependency]:
        """
        Get factor dependencies by dependent factor ID.
        
        Args:
            dependent_factor_id: The dependent factor ID
            
        Returns:
            List of FactorDependency entities for the dependent factor
        """
        pass
    
    @abstractmethod
    def get_by_independent_factor_id(self, independent_factor_id: int) -> List[FactorDependency]:
        """
        Get factor dependencies by independent factor ID.
        
        Args:
            independent_factor_id: The independent factor ID
            
        Returns:
            List of FactorDependency entities that depend on the independent factor
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[FactorDependency]:
        """
        Get all factor dependencies.
        
        Returns:
            List of all FactorDependency entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: FactorDependency) -> Optional[FactorDependency]:
        """
        Add/persist a factor dependency entity.
        
        Args:
            entity: The FactorDependency entity to persist
            
        Returns:
            Persisted FactorDependency entity with assigned ID or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: FactorDependency) -> Optional[FactorDependency]:
        """
        Update a factor dependency entity.
        
        Args:
            entity: The FactorDependency entity to update
            
        Returns:
            Updated FactorDependency entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete a factor dependency entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def exists(self, dependent_factor_id: int, independent_factor_id: int) -> bool:
        """
        Check if a dependency relationship exists between two factors.
        
        Args:
            dependent_factor_id: The dependent factor ID
            independent_factor_id: The independent factor ID
            
        Returns:
            True if dependency exists, False otherwise
        """
        pass