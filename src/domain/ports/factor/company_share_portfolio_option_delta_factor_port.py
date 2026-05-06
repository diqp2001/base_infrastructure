"""
Company Share Portfolio Option Delta Factor Port - Repository interface for CompanySharePortfolioOptionDeltaFactor entities.

This port defines the contract for repositories that handle CompanySharePortfolioOptionDeltaFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_delta_factor import CompanySharePortfolioOptionDeltaFactor


class CompanySharePortfolioOptionDeltaFactorPort(ABC):
    """Port interface for CompanySharePortfolioOptionDeltaFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[CompanySharePortfolioOptionDeltaFactor]:
    #     """
    #     Get company share portfolio option delta factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         CompanySharePortfolioOptionDeltaFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionDeltaFactor]:
    #     """
    #     Get company share portfolio option delta factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         CompanySharePortfolioOptionDeltaFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_underlying_symbol(self, underlying_symbol: str) -> List[CompanySharePortfolioOptionDeltaFactor]:
    #     """
    #     Get company share portfolio option delta factors by underlying portfolio symbol.
        
    #     Args:
    #         underlying_symbol: The underlying portfolio symbol
            
    #     Returns:
    #         List of CompanySharePortfolioOptionDeltaFactor entities for the underlying portfolio
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_date_range(self, start_date: str, end_date: str) -> List[CompanySharePortfolioOptionDeltaFactor]:
    #     """
    #     Get company share portfolio option delta factors by date range.
        
    #     Args:
    #         start_date: Start date (ISO format YYYY-MM-DD)
    #         end_date: End date (ISO format YYYY-MM-DD)
            
    #     Returns:
    #         List of CompanySharePortfolioOptionDeltaFactor entities within the date range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[CompanySharePortfolioOptionDeltaFactor]:
    #     """
    #     Get all company share portfolio option delta factors.
        
    #     Returns:
    #         List of CompanySharePortfolioOptionDeltaFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: CompanySharePortfolioOptionDeltaFactor) -> Optional[CompanySharePortfolioOptionDeltaFactor]:
    #     """
    #     Add/persist a company share portfolio option delta factor entity.
        
    #     Args:
    #         entity: The CompanySharePortfolioOptionDeltaFactor entity to persist
            
    #     Returns:
    #         Persisted CompanySharePortfolioOptionDeltaFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: CompanySharePortfolioOptionDeltaFactor) -> Optional[CompanySharePortfolioOptionDeltaFactor]:
    #     """
    #     Update a company share portfolio option delta factor entity.
        
    #     Args:
    #         entity: The CompanySharePortfolioOptionDeltaFactor entity to update
            
    #     Returns:
    #         Updated CompanySharePortfolioOptionDeltaFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete a company share portfolio option delta factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass