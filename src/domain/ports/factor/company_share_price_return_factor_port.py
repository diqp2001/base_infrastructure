"""
CompanySharePriceReturnFactor Port - Repository interface for CompanySharePriceReturnFactor entities.

This port defines the contract for repositories that handle CompanySharePriceReturnFactor
entities, ensuring both local and external data source repositories implement the same interface.
Mirrors the structure of IndexPriceReturnFactorPort.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_price_return_factor import CompanySharePriceReturnFactor


class CompanySharePriceReturnFactorPort(ABC):
    """Port interface for CompanySharePriceReturnFactor repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[CompanySharePriceReturnFactor]:
        """
        Get company share price return factor by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            CompanySharePriceReturnFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePriceReturnFactor]:
        """
        Get company share price return factor by name.
        
        Args:
            name: The factor name
            
        Returns:
            CompanySharePriceReturnFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_group(self, group: str) -> List[CompanySharePriceReturnFactor]:
        """
        Get company share price return factors by group.
        
        Args:
            group: The factor group
            
        Returns:
            List of CompanySharePriceReturnFactor entities in the group
        """
        pass
    
    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[CompanySharePriceReturnFactor]:
        """
        Get company share price return factors by subgroup.
        
        Args:
            subgroup: The factor subgroup
            
        Returns:
            List of CompanySharePriceReturnFactor entities in the subgroup
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[CompanySharePriceReturnFactor]:
        """
        Get all company share price return factors.
        
        Returns:
            List of CompanySharePriceReturnFactor entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: CompanySharePriceReturnFactor) -> Optional[CompanySharePriceReturnFactor]:
        """
        Add/persist a company share price return factor entity.
        
        Args:
            entity: The CompanySharePriceReturnFactor entity to persist
            
        Returns:
            Persisted CompanySharePriceReturnFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: CompanySharePriceReturnFactor) -> Optional[CompanySharePriceReturnFactor]:
        """
        Update a company share price return factor entity.
        
        Args:
            entity: The CompanySharePriceReturnFactor entity to update
            
        Returns:
            Updated CompanySharePriceReturnFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete a company share price return factor entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass