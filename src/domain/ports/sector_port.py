"""
Sector Port - Repository interface for Sector entities.

This port defines the contract for repositories that handle Sector
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.sector import Sector


class SectorPort(ABC):
    """Port interface for Sector repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[Sector]:
    #     """
    #     Get sector by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         Sector entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[Sector]:
    #     """
    #     Get sector by name.
        
    #     Args:
    #         name: The sector name
            
    #     Returns:
    #         Sector entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[Sector]:
    #     """
    #     Get all sectors.
        
    #     Returns:
    #         List of Sector entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: Sector) -> Optional[Sector]:
    #     """
    #     Add/persist a sector entity.
        
    #     Args:
    #         entity: The Sector entity to persist
            
    #     Returns:
    #         Persisted Sector entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: Sector) -> Optional[Sector]:
    #     """
    #     Update a sector entity.
        
    #     Args:
    #         entity: The Sector entity to update
            
    #     Returns:
    #         Updated Sector entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete a sector entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass