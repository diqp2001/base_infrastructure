"""
Company Share Option Factor Port - Repository interface for CompanyShareOptionFactor entities.

This port defines the contract for repositories that handle CompanyShareOptionFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionFactorPort(ABC):
    """Port interface for CompanyShareOptionFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[CompanyShareOptionFactor]:
    #     """
    #     Get company share option factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         CompanyShareOptionFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[CompanyShareOptionFactor]:
    #     """
    #     Get company share option factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         CompanyShareOptionFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_underlying_symbol(self, underlying_symbol: str) -> List[CompanyShareOptionFactor]:
    #     """
    #     Get company share option factors by underlying company share symbol.
        
    #     Args:
    #         underlying_symbol: The underlying company share symbol
            
    #     Returns:
    #         List of CompanyShareOptionFactor entities for the underlying company share
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_date_range(self, start_date: str, end_date: str) -> List[CompanyShareOptionFactor]:
    #     """
    #     Get company share option factors by date range.
        
    #     Args:
    #         start_date: Start date (ISO format YYYY-MM-DD)
    #         end_date: End date (ISO format YYYY-MM-DD)
            
    #     Returns:
    #         List of CompanyShareOptionFactor entities within the date range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[CompanyShareOptionFactor]:
    #     """
    #     Get all company share option factors.
        
    #     Returns:
    #         List of CompanyShareOptionFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: CompanyShareOptionFactor) -> Optional[CompanyShareOptionFactor]:
    #     """
    #     Add/persist a company share option factor entity.
        
    #     Args:
    #         entity: The CompanyShareOptionFactor entity to persist
            
    #     Returns:
    #         Persisted CompanyShareOptionFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: CompanyShareOptionFactor) -> Optional[CompanyShareOptionFactor]:
    #     """
    #     Update a company share option factor entity.
        
    #     Args:
    #         entity: The CompanyShareOptionFactor entity to update
            
    #     Returns:
    #         Updated CompanyShareOptionFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete a company share option factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass