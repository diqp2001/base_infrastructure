"""
Company Share Option Vega Factor Port - Repository interface for CompanyShareOptionVegaFactor entities.

This port defines the contract for repositories that handle CompanyShareOptionVegaFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_vega_factor import CompanyShareOptionVegaFactor


class CompanyShareOptionVegaFactorPort(ABC):
    """Port interface for CompanyShareOptionVegaFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[CompanyShareOptionVegaFactor]:
    #     """
    #     Get company share option vega factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         CompanyShareOptionVegaFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[CompanyShareOptionVegaFactor]:
    #     """
    #     Get company share option vega factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         CompanyShareOptionVegaFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_underlying_symbol(self, underlying_symbol: str) -> List[CompanyShareOptionVegaFactor]:
    #     """
    #     Get company share option vega factors by underlying company share symbol.
        
    #     Args:
    #         underlying_symbol: The underlying company share symbol
            
    #     Returns:
    #         List of CompanyShareOptionVegaFactor entities for the underlying company share
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_date_range(self, start_date: str, end_date: str) -> List[CompanyShareOptionVegaFactor]:
    #     """
    #     Get company share option vega factors by date range.
        
    #     Args:
    #         start_date: Start date (ISO format YYYY-MM-DD)
    #         end_date: End date (ISO format YYYY-MM-DD)
            
    #     Returns:
    #         List of CompanyShareOptionVegaFactor entities within the date range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[CompanyShareOptionVegaFactor]:
    #     """
    #     Get all company share option vega factors.
        
    #     Returns:
    #         List of CompanyShareOptionVegaFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: CompanyShareOptionVegaFactor) -> Optional[CompanyShareOptionVegaFactor]:
    #     """
    #     Add/persist a company share option vega factor entity.
        
    #     Args:
    #         entity: The CompanyShareOptionVegaFactor entity to persist
            
    #     Returns:
    #         Persisted CompanyShareOptionVegaFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: CompanyShareOptionVegaFactor) -> Optional[CompanyShareOptionVegaFactor]:
    #     """
    #     Update a company share option vega factor entity.
        
    #     Args:
    #         entity: The CompanyShareOptionVegaFactor entity to update
            
    #     Returns:
    #         Updated CompanyShareOptionVegaFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete a company share option vega factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass