"""
Continent Factor Port - Repository interface for ContinentFactor entities.

This port defines the contract for repositories that handle ContinentFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.continent_factor import ContinentFactor


class ContinentFactorPort(ABC):
    """Port interface for ContinentFactor repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[ContinentFactor]:
        """
        Get continent factor by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            ContinentFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[ContinentFactor]:
        """
        Get continent factor by name.
        
        Args:
            name: The factor name
            
        Returns:
            ContinentFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_continent_code(self, continent_code: str) -> List[ContinentFactor]:
        """
        Get continent factors by continent code.
        
        Args:
            continent_code: The continent code (e.g., 'NA', 'EU')
            
        Returns:
            List of ContinentFactor entities for the continent
        """
        pass
    
    @abstractmethod
    def get_by_hemisphere(self, hemisphere: str) -> List[ContinentFactor]:
        """
        Get continent factors by hemisphere.
        
        Args:
            hemisphere: The hemisphere ('northern', 'southern', 'both')
            
        Returns:
            List of ContinentFactor entities in the hemisphere
        """
        pass
    
    @abstractmethod
    def get_by_group(self, group: str) -> List[ContinentFactor]:
        """
        Get continent factors by group.
        
        Args:
            group: The factor group
            
        Returns:
            List of ContinentFactor entities in the group
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[ContinentFactor]:
        """
        Get all continent factors.
        
        Returns:
            List of ContinentFactor entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: ContinentFactor) -> Optional[ContinentFactor]:
        """
        Add/persist a continent factor entity.
        
        Args:
            entity: The ContinentFactor entity to persist
            
        Returns:
            Persisted ContinentFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: ContinentFactor) -> Optional[ContinentFactor]:
        """
        Update a continent factor entity.
        
        Args:
            entity: The ContinentFactor entity to update
            
        Returns:
            Updated ContinentFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete a continent factor entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass