"""
Continent Port - Repository interface for Continent entities.

This port defines the contract for repositories that handle Continent
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.continent import Continent


class ContinentPort(ABC):
    """Port interface for Continent repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[Continent]:
        """
        Get continent by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            Continent entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Continent]:
        """
        Get continent by name.
        
        Args:
            name: The continent name
            
        Returns:
            Continent entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[Continent]:
        """
        Get all continents.
        
        Returns:
            List of Continent entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: Continent) -> Optional[Continent]:
        """
        Add/persist a continent entity.
        
        Args:
            entity: The Continent entity to persist
            
        Returns:
            Persisted Continent entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: Continent) -> Optional[Continent]:
        """
        Update a continent entity.
        
        Args:
            entity: The Continent entity to update
            
        Returns:
            Updated Continent entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete a continent entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass