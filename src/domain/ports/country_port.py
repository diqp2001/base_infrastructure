"""
Country Port - Repository interface for Country entities.

This port defines the contract for repositories that handle Country
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.country import Country


class CountryPort(ABC):
    """Port interface for Country repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[Country]:
    #     """
    #     Get country by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         Country entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[Country]:
    #     """
    #     Get country by name.
        
    #     Args:
    #         name: The country name
            
    #     Returns:
    #         Country entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_continent_id(self, continent_id: int) -> List[Country]:
    #     """
    #     Get countries by continent ID.
        
    #     Args:
    #         continent_id: The continent ID
            
    #     Returns:
    #         List of Country entities in the continent
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[Country]:
    #     """
    #     Get all countries.
        
    #     Returns:
    #         List of Country entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: Country) -> Optional[Country]:
    #     """
    #     Add/persist a country entity.
        
    #     Args:
    #         entity: The Country entity to persist
            
    #     Returns:
    #         Persisted Country entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: Country) -> Optional[Country]:
    #     """
    #     Update a country entity.
        
    #     Args:
    #         entity: The Country entity to update
            
    #     Returns:
    #         Updated Country entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete a country entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass