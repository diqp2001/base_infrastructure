"""
Portfolio Company Share Option Price Return Factor Port - Repository interface for PortfolioCompanyShareOptionPriceReturnFactor entities.

This port defines the contract for repositories that handle PortfolioCompanyShareOptionPriceReturnFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_price_return_factor import PortfolioCompanyShareOptionPriceReturnFactor


class PortfolioCompanyShareOptionPriceReturnFactorPort(ABC):
    """Port interface for PortfolioCompanyShareOptionPriceReturnFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[PortfolioCompanyShareOptionPriceReturnFactor]:
    #     """
    #     Get portfolio company share option price return factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         PortfolioCompanyShareOptionPriceReturnFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[PortfolioCompanyShareOptionPriceReturnFactor]:
    #     """
    #     Get portfolio company share option price return factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         PortfolioCompanyShareOptionPriceReturnFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_underlying_symbol(self, underlying_symbol: str) -> List[PortfolioCompanyShareOptionPriceReturnFactor]:
    #     """
    #     Get portfolio company share option price return factors by underlying portfolio symbol.
        
    #     Args:
    #         underlying_symbol: The underlying portfolio symbol
            
    #     Returns:
    #         List of PortfolioCompanyShareOptionPriceReturnFactor entities for the underlying portfolio
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_date_range(self, start_date: str, end_date: str) -> List[PortfolioCompanyShareOptionPriceReturnFactor]:
    #     """
    #     Get portfolio company share option price return factors by date range.
        
    #     Args:
    #         start_date: Start date (ISO format YYYY-MM-DD)
    #         end_date: End date (ISO format YYYY-MM-DD)
            
    #     Returns:
    #         List of PortfolioCompanyShareOptionPriceReturnFactor entities within the date range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[PortfolioCompanyShareOptionPriceReturnFactor]:
    #     """
    #     Get all portfolio company share option price return factors.
        
    #     Returns:
    #         List of PortfolioCompanyShareOptionPriceReturnFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: PortfolioCompanyShareOptionPriceReturnFactor) -> Optional[PortfolioCompanyShareOptionPriceReturnFactor]:
    #     """
    #     Add/persist a portfolio company share option price return factor entity.
        
    #     Args:
    #         entity: The PortfolioCompanyShareOptionPriceReturnFactor entity to persist
            
    #     Returns:
    #         Persisted PortfolioCompanyShareOptionPriceReturnFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: PortfolioCompanyShareOptionPriceReturnFactor) -> Optional[PortfolioCompanyShareOptionPriceReturnFactor]:
    #     """
    #     Update a portfolio company share option price return factor entity.
        
    #     Args:
    #         entity: The PortfolioCompanyShareOptionPriceReturnFactor entity to update
            
    #     Returns:
    #         Updated PortfolioCompanyShareOptionPriceReturnFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete a portfolio company share option price return factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass