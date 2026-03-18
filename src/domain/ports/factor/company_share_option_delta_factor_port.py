"""
Company Share Option Delta Factor Port - Repository interface for CompanyShareOptionDeltaFactor entities.

This port defines the contract for repositories that handle CompanyShareOptionDeltaFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_delta_factor import CompanyShareOptionDeltaFactor


class CompanyShareOptionDeltaFactorPort(ABC):
    """Port interface for CompanyShareOptionDeltaFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[CompanyShareOptionDeltaFactor]:
    #     """
    #     Get company share option delta factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         CompanyShareOptionDeltaFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[CompanyShareOptionDeltaFactor]:
    #     """
    #     Get company share option delta factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         CompanyShareOptionDeltaFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_underlying_symbol(self, underlying_symbol: str) -> List[CompanyShareOptionDeltaFactor]:
    #     """
    #     Get company share option delta factors by underlying company share symbol.
        
    #     Args:
    #         underlying_symbol: The underlying company share symbol
            
    #     Returns:
    #         List of CompanyShareOptionDeltaFactor entities for the underlying company share
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_date_range(self, start_date: str, end_date: str) -> List[CompanyShareOptionDeltaFactor]:
    #     """
    #     Get company share option delta factors by date range.
        
    #     Args:
    #         start_date: Start date (ISO format YYYY-MM-DD)
    #         end_date: End date (ISO format YYYY-MM-DD)
            
    #     Returns:
    #         List of CompanyShareOptionDeltaFactor entities within the date range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[CompanyShareOptionDeltaFactor]:
    #     """
    #     Get all company share option delta factors.
        
    #     Returns:
    #         List of CompanyShareOptionDeltaFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: CompanyShareOptionDeltaFactor) -> Optional[CompanyShareOptionDeltaFactor]:
    #     """
    #     Add/persist a company share option delta factor entity.
        
    #     Args:
    #         entity: The CompanyShareOptionDeltaFactor entity to persist
            
    #     Returns:
    #         Persisted CompanyShareOptionDeltaFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: CompanyShareOptionDeltaFactor) -> Optional[CompanyShareOptionDeltaFactor]:
    #     """
    #     Update a company share option delta factor entity.
        
    #     Args:
    #         entity: The CompanyShareOptionDeltaFactor entity to update
            
    #     Returns:
    #         Updated CompanyShareOptionDeltaFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete a company share option delta factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass