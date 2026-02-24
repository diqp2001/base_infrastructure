"""
Portfolio Company Share Option Price Factor Port - Repository interface for PortfolioCompanyShareOptionPriceFactor entities.

This port defines the contract for repositories that handle PortfolioCompanyShareOptionPriceFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_price_factor import PortfolioCompanyShareOptionPriceFactor


class PortfolioCompanyShareOptionPriceFactorPort(ABC):
    """Port interface for PortfolioCompanyShareOptionPriceFactor repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[PortfolioCompanyShareOptionPriceFactor]:
        """
        Get portfolio company share option price factor by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            PortfolioCompanyShareOptionPriceFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[PortfolioCompanyShareOptionPriceFactor]:
        """
        Get portfolio company share option price factor by name.
        
        Args:
            name: The factor name
            
        Returns:
            PortfolioCompanyShareOptionPriceFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_underlying_symbol(self, underlying_symbol: str) -> List[PortfolioCompanyShareOptionPriceFactor]:
        """
        Get portfolio company share option price factors by underlying portfolio symbol.
        
        Args:
            underlying_symbol: The underlying portfolio symbol
            
        Returns:
            List of PortfolioCompanyShareOptionPriceFactor entities for the underlying portfolio
        """
        pass
    
    @abstractmethod
    def get_by_date_range(self, start_date: str, end_date: str) -> List[PortfolioCompanyShareOptionPriceFactor]:
        """
        Get portfolio company share option price factors by date range.
        
        Args:
            start_date: Start date (ISO format YYYY-MM-DD)
            end_date: End date (ISO format YYYY-MM-DD)
            
        Returns:
            List of PortfolioCompanyShareOptionPriceFactor entities within the date range
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[PortfolioCompanyShareOptionPriceFactor]:
        """
        Get all portfolio company share option price factors.
        
        Returns:
            List of PortfolioCompanyShareOptionPriceFactor entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: PortfolioCompanyShareOptionPriceFactor) -> Optional[PortfolioCompanyShareOptionPriceFactor]:
        """
        Add/persist a portfolio company share option price factor entity.
        
        Args:
            entity: The PortfolioCompanyShareOptionPriceFactor entity to persist
            
        Returns:
            Persisted PortfolioCompanyShareOptionPriceFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: PortfolioCompanyShareOptionPriceFactor) -> Optional[PortfolioCompanyShareOptionPriceFactor]:
        """
        Update a portfolio company share option price factor entity.
        
        Args:
            entity: The PortfolioCompanyShareOptionPriceFactor entity to update
            
        Returns:
            Updated PortfolioCompanyShareOptionPriceFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete a portfolio company share option price factor entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass