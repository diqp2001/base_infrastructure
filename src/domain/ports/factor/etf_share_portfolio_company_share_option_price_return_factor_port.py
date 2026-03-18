"""
ETF Share Portfolio Company Share Option Price Return Factor Port - Repository interface for ETFSharePortfolioCompanyShareOptionPriceReturnFactor entities.

This port defines the contract for repositories that handle ETFSharePortfolioCompanyShareOptionPriceReturnFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_portfolio_company_share_option.etf_share_portfolio_company_share_option_price_return_factor import ETFSharePortfolioCompanyShareOptionPriceReturnFactor


class ETFSharePortfolioCompanyShareOptionPriceReturnFactorPort(ABC):
    """Port interface for ETFSharePortfolioCompanyShareOptionPriceReturnFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[ETFSharePortfolioCompanyShareOptionPriceReturnFactor]:
    #     """
    #     Get ETF share portfolio company share option price return factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         ETFSharePortfolioCompanyShareOptionPriceReturnFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[ETFSharePortfolioCompanyShareOptionPriceReturnFactor]:
    #     """
    #     Get ETF share portfolio company share option price return factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         ETFSharePortfolioCompanyShareOptionPriceReturnFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_underlying_symbol(self, underlying_symbol: str) -> List[ETFSharePortfolioCompanyShareOptionPriceReturnFactor]:
    #     """
    #     Get ETF share portfolio company share option price return factors by underlying ETF symbol.
        
    #     Args:
    #         underlying_symbol: The underlying ETF symbol
            
    #     Returns:
    #         List of ETFSharePortfolioCompanyShareOptionPriceReturnFactor entities for the underlying ETF
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_date_range(self, start_date: str, end_date: str) -> List[ETFSharePortfolioCompanyShareOptionPriceReturnFactor]:
    #     """
    #     Get ETF share portfolio company share option price return factors by date range.
        
    #     Args:
    #         start_date: Start date (ISO format YYYY-MM-DD)
    #         end_date: End date (ISO format YYYY-MM-DD)
            
    #     Returns:
    #         List of ETFSharePortfolioCompanyShareOptionPriceReturnFactor entities within the date range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[ETFSharePortfolioCompanyShareOptionPriceReturnFactor]:
    #     """
    #     Get all ETF share portfolio company share option price return factors.
        
    #     Returns:
    #         List of ETFSharePortfolioCompanyShareOptionPriceReturnFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: ETFSharePortfolioCompanyShareOptionPriceReturnFactor) -> Optional[ETFSharePortfolioCompanyShareOptionPriceReturnFactor]:
    #     """
    #     Add/persist an ETF share portfolio company share option price return factor entity.
        
    #     Args:
    #         entity: The ETFSharePortfolioCompanyShareOptionPriceReturnFactor entity to persist
            
    #     Returns:
    #         Persisted ETFSharePortfolioCompanyShareOptionPriceReturnFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: ETFSharePortfolioCompanyShareOptionPriceReturnFactor) -> Optional[ETFSharePortfolioCompanyShareOptionPriceReturnFactor]:
    #     """
    #     Update an ETF share portfolio company share option price return factor entity.
        
    #     Args:
    #         entity: The ETFSharePortfolioCompanyShareOptionPriceReturnFactor entity to update
            
    #     Returns:
    #         Updated ETFSharePortfolioCompanyShareOptionPriceReturnFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete an ETF share portfolio company share option price return factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass