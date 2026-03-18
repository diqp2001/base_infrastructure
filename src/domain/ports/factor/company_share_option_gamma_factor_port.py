"""
Company Share Option Gamma Factor Port - Repository interface for CompanyShareOptionGammaFactor entities.

This port defines the contract for repositories that handle CompanyShareOptionGammaFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_gamma_factor import CompanyShareOptionGammaFactor


class CompanyShareOptionGammaFactorPort(ABC):
    """Port interface for CompanyShareOptionGammaFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[CompanyShareOptionGammaFactor]:
    #     """
    #     Get company share option gamma factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         CompanyShareOptionGammaFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[CompanyShareOptionGammaFactor]:
    #     """
    #     Get company share option gamma factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         CompanyShareOptionGammaFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_underlying_symbol(self, underlying_symbol: str) -> List[CompanyShareOptionGammaFactor]:
    #     """
    #     Get company share option gamma factors by underlying company share symbol.
        
    #     Args:
    #         underlying_symbol: The underlying company share symbol
            
    #     Returns:
    #         List of CompanyShareOptionGammaFactor entities for the underlying company share
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_date_range(self, start_date: str, end_date: str) -> List[CompanyShareOptionGammaFactor]:
    #     """
    #     Get company share option gamma factors by date range.
        
    #     Args:
    #         start_date: Start date (ISO format YYYY-MM-DD)
    #         end_date: End date (ISO format YYYY-MM-DD)
            
    #     Returns:
    #         List of CompanyShareOptionGammaFactor entities within the date range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[CompanyShareOptionGammaFactor]:
    #     """
    #     Get all company share option gamma factors.
        
    #     Returns:
    #         List of CompanyShareOptionGammaFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: CompanyShareOptionGammaFactor) -> Optional[CompanyShareOptionGammaFactor]:
    #     """
    #     Add/persist a company share option gamma factor entity.
        
    #     Args:
    #         entity: The CompanyShareOptionGammaFactor entity to persist
            
    #     Returns:
    #         Persisted CompanyShareOptionGammaFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: CompanyShareOptionGammaFactor) -> Optional[CompanyShareOptionGammaFactor]:
    #     """
    #     Update a company share option gamma factor entity.
        
    #     Args:
    #         entity: The CompanyShareOptionGammaFactor entity to update
            
    #     Returns:
    #         Updated CompanyShareOptionGammaFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete a company share option gamma factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass