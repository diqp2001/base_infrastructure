"""
CompanyShareFactor Port - Repository interface for CompanyShareFactor entities.

This port defines the contract for repositories that handle CompanyShareFactor
entities, ensuring both local and external data source repositories implement the same interface.
Mirrors the structure of IndexFactorPort.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor


class CompanyShareFactorPort(ABC):
    """Port interface for CompanyShareFactor repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[CompanyShareFactor]:
        """
        Get company share factor by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            CompanyShareFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareFactor]:
        """
        Get company share factor by name.
        
        Args:
            name: The factor name
            
        Returns:
            CompanyShareFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_group(self, group: str) -> List[CompanyShareFactor]:
        """
        Get company share factors by group.
        
        Args:
            group: The factor group
            
        Returns:
            List of CompanyShareFactor entities in the group
        """
        pass
    
    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[CompanyShareFactor]:
        """
        Get company share factors by subgroup.
        
        Args:
            subgroup: The factor subgroup
            
        Returns:
            List of CompanyShareFactor entities in the subgroup
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[CompanyShareFactor]:
        """
        Get all company share factors.
        
        Returns:
            List of CompanyShareFactor entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: CompanyShareFactor) -> Optional[CompanyShareFactor]:
        """
        Add/persist a company share factor entity.
        
        Args:
            entity: The CompanyShareFactor entity to persist
            
        Returns:
            Persisted CompanyShareFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: CompanyShareFactor) -> Optional[CompanyShareFactor]:
        """
        Update a company share factor entity.
        
        Args:
            entity: The CompanyShareFactor entity to update
            
        Returns:
            Updated CompanyShareFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete a company share factor entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass