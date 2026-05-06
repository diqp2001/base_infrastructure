"""
Company Share Portfolio Option Price Return Factor Port - Repository interface for CompanySharePortfolioOptionPriceReturnFactor entities.

This port defines the contract for repositories that handle CompanySharePortfolioOptionPriceReturnFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_price_return_factor import CompanySharePortfolioOptionPriceReturnFactor


class CompanySharePortfolioOptionPriceReturnFactorPort(ABC):
    """Port interface for CompanySharePortfolioOptionPriceReturnFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[CompanySharePortfolioOptionPriceReturnFactor]:
    #     """
    #     Get company share portfolio option price return factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         CompanySharePortfolioOptionPriceReturnFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionPriceReturnFactor]:
    #     """
    #     Get company share portfolio option price return factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         CompanySharePortfolioOptionPriceReturnFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_underlying_symbol(self, underlying_symbol: str) -> List[CompanySharePortfolioOptionPriceReturnFactor]:
    #     """
    #     Get company share portfolio option price return factors by underlying portfolio symbol.
        
    #     Args:
    #         underlying_symbol: The underlying portfolio symbol
            
    #     Returns:
    #         List of CompanySharePortfolioOptionPriceReturnFactor entities for the underlying portfolio
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_date_range(self, start_date: str, end_date: str) -> List[CompanySharePortfolioOptionPriceReturnFactor]:
    #     """
    #     Get company share portfolio option price return factors by date range.
        
    #     Args:
    #         start_date: Start date (ISO format YYYY-MM-DD)
    #         end_date: End date (ISO format YYYY-MM-DD)
            
    #     Returns:
    #         List of CompanySharePortfolioOptionPriceReturnFactor entities within the date range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[CompanySharePortfolioOptionPriceReturnFactor]:
    #     """
    #     Get all company share portfolio option price return factors.
        
    #     Returns:
    #         List of CompanySharePortfolioOptionPriceReturnFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: CompanySharePortfolioOptionPriceReturnFactor) -> Optional[CompanySharePortfolioOptionPriceReturnFactor]:
    #     """
    #     Add/persist a company share portfolio option price return factor entity.
        
    #     Args:
    #         entity: The CompanySharePortfolioOptionPriceReturnFactor entity to persist
            
    #     Returns:
    #         Persisted CompanySharePortfolioOptionPriceReturnFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: CompanySharePortfolioOptionPriceReturnFactor) -> Optional[CompanySharePortfolioOptionPriceReturnFactor]:
    #     """
    #     Update a company share portfolio option price return factor entity.
        
    #     Args:
    #         entity: The CompanySharePortfolioOptionPriceReturnFactor entity to update
            
    #     Returns:
    #         Updated CompanySharePortfolioOptionPriceReturnFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete a company share portfolio option price return factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass