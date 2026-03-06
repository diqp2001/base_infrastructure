"""
CompanyShareOptionPriceReturnFactor Port - Repository interface for CompanyShareOptionPriceReturnFactor entities.

This port defines the contract for repositories that handle CompanyShareOptionPriceReturnFactor
entities, ensuring both local and external data source repositories implement the same interface.
Follows the same pattern as other factor ports in the system.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_price_return_factor import CompanyShareOptionPriceReturnFactor


class CompanyShareOptionPriceReturnFactorPort(ABC):
    """Port interface for CompanyShareOptionPriceReturnFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[CompanyShareOptionPriceReturnFactor]:
    #     """
    #     Get company share option price return factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         CompanyShareOptionPriceReturnFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[CompanyShareOptionPriceReturnFactor]:
    #     """
    #     Get company share option price return factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         CompanyShareOptionPriceReturnFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_group(self, group: str) -> List[CompanyShareOptionPriceReturnFactor]:
    #     """
    #     Get company share option price return factors by group.
        
    #     Args:
    #         group: The factor group
            
    #     Returns:
    #         List of CompanyShareOptionPriceReturnFactor entities in the group
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_subgroup(self, subgroup: str) -> List[CompanyShareOptionPriceReturnFactor]:
    #     """
    #     Get company share option price return factors by subgroup.
        
    #     Args:
    #         subgroup: The factor subgroup
            
    #     Returns:
    #         List of CompanyShareOptionPriceReturnFactor entities in the subgroup
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[CompanyShareOptionPriceReturnFactor]:
    #     """
    #     Get all company share option price return factors.
        
    #     Returns:
    #         List of CompanyShareOptionPriceReturnFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: CompanyShareOptionPriceReturnFactor) -> Optional[CompanyShareOptionPriceReturnFactor]:
    #     """
    #     Add/persist a company share option price return factor entity.
        
    #     Args:
    #         entity: The CompanyShareOptionPriceReturnFactor entity to persist
            
    #     Returns:
    #         Persisted CompanyShareOptionPriceReturnFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: CompanyShareOptionPriceReturnFactor) -> Optional[CompanyShareOptionPriceReturnFactor]:
    #     """
    #     Update a company share option price return factor entity.
        
    #     Args:
    #         entity: The CompanyShareOptionPriceReturnFactor entity to update
            
    #     Returns:
    #         Updated CompanyShareOptionPriceReturnFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete a company share option price return factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass