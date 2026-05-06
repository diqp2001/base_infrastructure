"""
Company Share Portfolio Option Factor Port - Repository interface for CompanySharePortfolioOptionFactor entities.

This port defines the contract for repositories that handle CompanySharePortfolioOptionFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_factor import CompanySharePortfolioOptionFactor


class CompanySharePortfolioOptionFactorPort(ABC):
    """Port interface for CompanySharePortfolioOptionFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[CompanySharePortfolioOptionFactor]:
    #     """
    #     Get company share portfolio option factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         CompanySharePortfolioOptionFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionFactor]:
    #     """
    #     Get company share portfolio option factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         CompanySharePortfolioOptionFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_underlying_symbol(self, underlying_symbol: str) -> List[CompanySharePortfolioOptionFactor]:
    #     """
    #     Get company share portfolio option factors by underlying portfolio symbol.
        
    #     Args:
    #         underlying_symbol: The underlying portfolio symbol
            
    #     Returns:
    #         List of CompanySharePortfolioOptionFactor entities for the underlying portfolio
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_date_range(self, start_date: str, end_date: str) -> List[CompanySharePortfolioOptionFactor]:
    #     """
    #     Get company share portfolio option factors by date range.
        
    #     Args:
    #         start_date: Start date (ISO format YYYY-MM-DD)
    #         end_date: End date (ISO format YYYY-MM-DD)
            
    #     Returns:
    #         List of CompanySharePortfolioOptionFactor entities within the date range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[CompanySharePortfolioOptionFactor]:
    #     """
    #     Get all company share portfolio option factors.
        
    #     Returns:
    #         List of CompanySharePortfolioOptionFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: CompanySharePortfolioOptionFactor) -> Optional[CompanySharePortfolioOptionFactor]:
    #     """
    #     Add/persist a company share portfolio option factor entity.
        
    #     Args:
    #         entity: The CompanySharePortfolioOptionFactor entity to persist
            
    #     Returns:
    #         Persisted CompanySharePortfolioOptionFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: CompanySharePortfolioOptionFactor) -> Optional[CompanySharePortfolioOptionFactor]:
    #     """
    #     Update a company share portfolio option factor entity.
        
    #     Args:
    #         entity: The CompanySharePortfolioOptionFactor entity to update
            
    #     Returns:
    #         Updated CompanySharePortfolioOptionFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete a company share portfolio option factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass