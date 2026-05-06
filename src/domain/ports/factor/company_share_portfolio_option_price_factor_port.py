"""
Company Share Portfolio Option Price Factor Port - Repository interface for CompanySharePortfolioOptionPriceFactor entities.

This port defines the contract for repositories that handle CompanySharePortfolioOptionPriceFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_price_factor import CompanySharePortfolioOptionPriceFactor


class CompanySharePortfolioOptionPriceFactorPort(ABC):
    """Port interface for CompanySharePortfolioOptionPriceFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[CompanySharePortfolioOptionPriceFactor]:
    #     """
    #     Get company share portfolio option price factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         CompanySharePortfolioOptionPriceFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionPriceFactor]:
    #     """
    #     Get company share portfolio option price factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         CompanySharePortfolioOptionPriceFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_underlying_symbol(self, underlying_symbol: str) -> List[CompanySharePortfolioOptionPriceFactor]:
    #     """
    #     Get company share portfolio option price factors by underlying portfolio symbol.
        
    #     Args:
    #         underlying_symbol: The underlying portfolio symbol
            
    #     Returns:
    #         List of CompanySharePortfolioOptionPriceFactor entities for the underlying portfolio
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_date_range(self, start_date: str, end_date: str) -> List[CompanySharePortfolioOptionPriceFactor]:
    #     """
    #     Get company share portfolio option price factors by date range.
        
    #     Args:
    #         start_date: Start date (ISO format YYYY-MM-DD)
    #         end_date: End date (ISO format YYYY-MM-DD)
            
    #     Returns:
    #         List of CompanySharePortfolioOptionPriceFactor entities within the date range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[CompanySharePortfolioOptionPriceFactor]:
    #     """
    #     Get all company share portfolio option price factors.
        
    #     Returns:
    #         List of CompanySharePortfolioOptionPriceFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: CompanySharePortfolioOptionPriceFactor) -> Optional[CompanySharePortfolioOptionPriceFactor]:
    #     """
    #     Add/persist a company share portfolio option price factor entity.
        
    #     Args:
    #         entity: The CompanySharePortfolioOptionPriceFactor entity to persist
            
    #     Returns:
    #         Persisted CompanySharePortfolioOptionPriceFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: CompanySharePortfolioOptionPriceFactor) -> Optional[CompanySharePortfolioOptionPriceFactor]:
    #     """
    #     Update a company share portfolio option price factor entity.
        
    #     Args:
    #         entity: The CompanySharePortfolioOptionPriceFactor entity to update
            
    #     Returns:
    #         Updated CompanySharePortfolioOptionPriceFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete a company share portfolio option price factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass