"""
Industry Port - Repository interface for Industry entities.

This port defines the contract for repositories that handle Industry
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.industry import Industry


class IndustryPort(ABC):
    """Port interface for Industry repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[Industry]:
    #     """
    #     Get industry by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         Industry entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[Industry]:
    #     """
    #     Get industry by name.
        
    #     Args:
    #         name: The industry name
            
    #     Returns:
    #         Industry entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_sector_id(self, sector_id: int) -> List[Industry]:
    #     """
    #     Get industries by sector ID.
        
    #     Args:
    #         sector_id: The sector ID
            
    #     Returns:
    #         List of Industry entities in the sector
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[Industry]:
    #     """
    #     Get all industries.
        
    #     Returns:
    #         List of Industry entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: Industry) -> Optional[Industry]:
    #     """
    #     Add/persist an industry entity.
        
    #     Args:
    #         entity: The Industry entity to persist
            
    #     Returns:
    #         Persisted Industry entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: Industry) -> Optional[Industry]:
    #     """
    #     Update an industry entity.
        
    #     Args:
    #         entity: The Industry entity to update
            
    #     Returns:
    #         Updated Industry entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete an industry entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass