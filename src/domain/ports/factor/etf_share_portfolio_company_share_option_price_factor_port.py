"""
ETF Share Portfolio Company Share Option Price Factor Port - Repository interface for ETFSharePortfolioCompanyShareOptionPriceFactor entities.

This port defines the contract for repositories that handle ETFSharePortfolioCompanyShareOptionPriceFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_portfolio_company_share_option.etf_share_portfolio_company_share_option_price_factor import ETFSharePortfolioCompanyShareOptionPriceFactor


class ETFSharePortfolioCompanyShareOptionPriceFactorPort(ABC):
    """Port interface for ETFSharePortfolioCompanyShareOptionPriceFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[ETFSharePortfolioCompanyShareOptionPriceFactor]:
    #     """
    #     Get ETF share portfolio company share option price factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         ETFSharePortfolioCompanyShareOptionPriceFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[ETFSharePortfolioCompanyShareOptionPriceFactor]:
    #     """
    #     Get ETF share portfolio company share option price factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         ETFSharePortfolioCompanyShareOptionPriceFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_underlying_symbol(self, underlying_symbol: str) -> List[ETFSharePortfolioCompanyShareOptionPriceFactor]:
    #     """
    #     Get ETF share portfolio company share option price factors by underlying ETF symbol.
        
    #     Args:
    #         underlying_symbol: The underlying ETF symbol
            
    #     Returns:
    #         List of ETFSharePortfolioCompanyShareOptionPriceFactor entities for the underlying ETF
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_date_range(self, start_date: str, end_date: str) -> List[ETFSharePortfolioCompanyShareOptionPriceFactor]:
    #     """
    #     Get ETF share portfolio company share option price factors by date range.
        
    #     Args:
    #         start_date: Start date (ISO format YYYY-MM-DD)
    #         end_date: End date (ISO format YYYY-MM-DD)
            
    #     Returns:
    #         List of ETFSharePortfolioCompanyShareOptionPriceFactor entities within the date range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[ETFSharePortfolioCompanyShareOptionPriceFactor]:
    #     """
    #     Get all ETF share portfolio company share option price factors.
        
    #     Returns:
    #         List of ETFSharePortfolioCompanyShareOptionPriceFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: ETFSharePortfolioCompanyShareOptionPriceFactor) -> Optional[ETFSharePortfolioCompanyShareOptionPriceFactor]:
    #     """
    #     Add/persist an ETF share portfolio company share option price factor entity.
        
    #     Args:
    #         entity: The ETFSharePortfolioCompanyShareOptionPriceFactor entity to persist
            
    #     Returns:
    #         Persisted ETFSharePortfolioCompanyShareOptionPriceFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: ETFSharePortfolioCompanyShareOptionPriceFactor) -> Optional[ETFSharePortfolioCompanyShareOptionPriceFactor]:
    #     """
    #     Update an ETF share portfolio company share option price factor entity.
        
    #     Args:
    #         entity: The ETFSharePortfolioCompanyShareOptionPriceFactor entity to update
            
    #     Returns:
    #         Updated ETFSharePortfolioCompanyShareOptionPriceFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete an ETF share portfolio company share option price factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass