"""
ETF Share Portfolio Company Share Option Factor Port - Repository interface for ETFSharePortfolioCompanyShareOptionFactor entities.

This port defines the contract for repositories that handle ETFSharePortfolioCompanyShareOptionFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_portfolio_company_share_option.etf_share_portfolio_company_share_option_factor import ETFSharePortfolioCompanyShareOptionFactor


class ETFSharePortfolioCompanyShareOptionFactorPort(ABC):
    """Port interface for ETFSharePortfolioCompanyShareOptionFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[ETFSharePortfolioCompanyShareOptionFactor]:
    #     """
    #     Get ETF share portfolio company share option factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         ETFSharePortfolioCompanyShareOptionFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[ETFSharePortfolioCompanyShareOptionFactor]:
    #     """
    #     Get ETF share portfolio company share option factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         ETFSharePortfolioCompanyShareOptionFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_underlying_symbol(self, underlying_symbol: str) -> List[ETFSharePortfolioCompanyShareOptionFactor]:
    #     """
    #     Get ETF share portfolio company share option factors by underlying ETF symbol.
        
    #     Args:
    #         underlying_symbol: The underlying ETF symbol
            
    #     Returns:
    #         List of ETFSharePortfolioCompanyShareOptionFactor entities for the underlying ETF
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_date_range(self, start_date: str, end_date: str) -> List[ETFSharePortfolioCompanyShareOptionFactor]:
    #     """
    #     Get ETF share portfolio company share option factors by date range.
        
    #     Args:
    #         start_date: Start date (ISO format YYYY-MM-DD)
    #         end_date: End date (ISO format YYYY-MM-DD)
            
    #     Returns:
    #         List of ETFSharePortfolioCompanyShareOptionFactor entities within the date range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[ETFSharePortfolioCompanyShareOptionFactor]:
    #     """
    #     Get all ETF share portfolio company share option factors.
        
    #     Returns:
    #         List of ETFSharePortfolioCompanyShareOptionFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: ETFSharePortfolioCompanyShareOptionFactor) -> Optional[ETFSharePortfolioCompanyShareOptionFactor]:
    #     """
    #     Add/persist an ETF share portfolio company share option factor entity.
        
    #     Args:
    #         entity: The ETFSharePortfolioCompanyShareOptionFactor entity to persist
            
    #     Returns:
    #         Persisted ETFSharePortfolioCompanyShareOptionFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: ETFSharePortfolioCompanyShareOptionFactor) -> Optional[ETFSharePortfolioCompanyShareOptionFactor]:
    #     """
    #     Update an ETF share portfolio company share option factor entity.
        
    #     Args:
    #         entity: The ETFSharePortfolioCompanyShareOptionFactor entity to update
            
    #     Returns:
    #         Updated ETFSharePortfolioCompanyShareOptionFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete an ETF share portfolio company share option factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass