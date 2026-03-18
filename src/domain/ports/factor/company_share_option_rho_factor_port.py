"""
Company Share Option Rho Factor Port - Repository interface for CompanyShareOptionRhoFactor entities.

This port defines the contract for repositories that handle CompanyShareOptionRhoFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_rho_factor import CompanyShareOptionRhoFactor


class CompanyShareOptionRhoFactorPort(ABC):
    """Port interface for CompanyShareOptionRhoFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[CompanyShareOptionRhoFactor]:
    #     """
    #     Get company share option rho factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         CompanyShareOptionRhoFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[CompanyShareOptionRhoFactor]:
    #     """
    #     Get company share option rho factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         CompanyShareOptionRhoFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_underlying_symbol(self, underlying_symbol: str) -> List[CompanyShareOptionRhoFactor]:
    #     """
    #     Get company share option rho factors by underlying company share symbol.
        
    #     Args:
    #         underlying_symbol: The underlying company share symbol
            
    #     Returns:
    #         List of CompanyShareOptionRhoFactor entities for the underlying company share
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_date_range(self, start_date: str, end_date: str) -> List[CompanyShareOptionRhoFactor]:
    #     """
    #     Get company share option rho factors by date range.
        
    #     Args:
    #         start_date: Start date (ISO format YYYY-MM-DD)
    #         end_date: End date (ISO format YYYY-MM-DD)
            
    #     Returns:
    #         List of CompanyShareOptionRhoFactor entities within the date range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[CompanyShareOptionRhoFactor]:
    #     """
    #     Get all company share option rho factors.
        
    #     Returns:
    #         List of CompanyShareOptionRhoFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: CompanyShareOptionRhoFactor) -> Optional[CompanyShareOptionRhoFactor]:
    #     """
    #     Add/persist a company share option rho factor entity.
        
    #     Args:
    #         entity: The CompanyShareOptionRhoFactor entity to persist
            
    #     Returns:
    #         Persisted CompanyShareOptionRhoFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: CompanyShareOptionRhoFactor) -> Optional[CompanyShareOptionRhoFactor]:
    #     """
    #     Update a company share option rho factor entity.
        
    #     Args:
    #         entity: The CompanyShareOptionRhoFactor entity to update
            
    #     Returns:
    #         Updated CompanyShareOptionRhoFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete a company share option rho factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass