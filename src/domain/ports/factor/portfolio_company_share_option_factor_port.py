"""
Portfolio Company Share Option Factor Port - Repository interface for PortfolioCompanyShareOptionFactor entities.

This port defines the contract for repositories that handle PortfolioCompanyShareOptionFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_factor import PortfolioCompanyShareOptionFactor


class PortfolioCompanyShareOptionFactorPort(ABC):
    """Port interface for PortfolioCompanyShareOptionFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[PortfolioCompanyShareOptionFactor]:
    #     """
    #     Get portfolio company share option factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         PortfolioCompanyShareOptionFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[PortfolioCompanyShareOptionFactor]:
    #     """
    #     Get portfolio company share option factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         PortfolioCompanyShareOptionFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_underlying_symbol(self, underlying_symbol: str) -> List[PortfolioCompanyShareOptionFactor]:
    #     """
    #     Get portfolio company share option factors by underlying portfolio symbol.
        
    #     Args:
    #         underlying_symbol: The underlying portfolio symbol
            
    #     Returns:
    #         List of PortfolioCompanyShareOptionFactor entities for the underlying portfolio
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_date_range(self, start_date: str, end_date: str) -> List[PortfolioCompanyShareOptionFactor]:
    #     """
    #     Get portfolio company share option factors by date range.
        
    #     Args:
    #         start_date: Start date (ISO format YYYY-MM-DD)
    #         end_date: End date (ISO format YYYY-MM-DD)
            
    #     Returns:
    #         List of PortfolioCompanyShareOptionFactor entities within the date range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[PortfolioCompanyShareOptionFactor]:
    #     """
    #     Get all portfolio company share option factors.
        
    #     Returns:
    #         List of PortfolioCompanyShareOptionFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: PortfolioCompanyShareOptionFactor) -> Optional[PortfolioCompanyShareOptionFactor]:
    #     """
    #     Add/persist a portfolio company share option factor entity.
        
    #     Args:
    #         entity: The PortfolioCompanyShareOptionFactor entity to persist
            
    #     Returns:
    #         Persisted PortfolioCompanyShareOptionFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: PortfolioCompanyShareOptionFactor) -> Optional[PortfolioCompanyShareOptionFactor]:
    #     """
    #     Update a portfolio company share option factor entity.
        
    #     Args:
    #         entity: The PortfolioCompanyShareOptionFactor entity to update
            
    #     Returns:
    #         Updated PortfolioCompanyShareOptionFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete a portfolio company share option factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass