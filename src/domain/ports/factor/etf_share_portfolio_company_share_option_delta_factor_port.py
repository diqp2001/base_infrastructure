"""
ETF Share Portfolio Company Share Option Delta Factor Port - Repository interface for ETFSharePortfolioCompanyShareOptionDeltaFactor entities.

This port defines the contract for repositories that handle ETFSharePortfolioCompanyShareOptionDeltaFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_portfolio_company_share_option.etf_share_portfolio_company_share_option_delta_factor import ETFSharePortfolioCompanyShareOptionDeltaFactor


class ETFSharePortfolioCompanyShareOptionDeltaFactorPort(ABC):
    """Port interface for ETFSharePortfolioCompanyShareOptionDeltaFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[ETFSharePortfolioCompanyShareOptionDeltaFactor]:
    #     """
    #     Get ETF share portfolio company share option delta factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         ETFSharePortfolioCompanyShareOptionDeltaFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[ETFSharePortfolioCompanyShareOptionDeltaFactor]:
    #     """
    #     Get ETF share portfolio company share option delta factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         ETFSharePortfolioCompanyShareOptionDeltaFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_underlying_symbol(self, underlying_symbol: str) -> List[ETFSharePortfolioCompanyShareOptionDeltaFactor]:
    #     """
    #     Get ETF share portfolio company share option delta factors by underlying ETF symbol.
        
    #     Args:
    #         underlying_symbol: The underlying ETF symbol
            
    #     Returns:
    #         List of ETFSharePortfolioCompanyShareOptionDeltaFactor entities for the underlying ETF
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_date_range(self, start_date: str, end_date: str) -> List[ETFSharePortfolioCompanyShareOptionDeltaFactor]:
    #     """
    #     Get ETF share portfolio company share option delta factors by date range.
        
    #     Args:
    #         start_date: Start date (ISO format YYYY-MM-DD)
    #         end_date: End date (ISO format YYYY-MM-DD)
            
    #     Returns:
    #         List of ETFSharePortfolioCompanyShareOptionDeltaFactor entities within the date range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[ETFSharePortfolioCompanyShareOptionDeltaFactor]:
    #     """
    #     Get all ETF share portfolio company share option delta factors.
        
    #     Returns:
    #         List of ETFSharePortfolioCompanyShareOptionDeltaFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: ETFSharePortfolioCompanyShareOptionDeltaFactor) -> Optional[ETFSharePortfolioCompanyShareOptionDeltaFactor]:
    #     """
    #     Add/persist an ETF share portfolio company share option delta factor entity.
        
    #     Args:
    #         entity: The ETFSharePortfolioCompanyShareOptionDeltaFactor entity to persist
            
    #     Returns:
    #         Persisted ETFSharePortfolioCompanyShareOptionDeltaFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: ETFSharePortfolioCompanyShareOptionDeltaFactor) -> Optional[ETFSharePortfolioCompanyShareOptionDeltaFactor]:
    #     """
    #     Update an ETF share portfolio company share option delta factor entity.
        
    #     Args:
    #         entity: The ETFSharePortfolioCompanyShareOptionDeltaFactor entity to update
            
    #     Returns:
    #         Updated ETFSharePortfolioCompanyShareOptionDeltaFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete an ETF share portfolio company share option delta factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass