"""
Portfolio Company Share Option Delta Factor Port - Repository interface for PortfolioCompanyShareOptionDeltaFactor entities.

This port defines the contract for repositories that handle PortfolioCompanyShareOptionDeltaFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.portfolio_company_share_option.portfolio_company_share_option_delta_factor import PortfolioCompanyShareOptionDeltaFactor


class PortfolioCompanyShareOptionDeltaFactorPort(ABC):
    """Port interface for PortfolioCompanyShareOptionDeltaFactor repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[PortfolioCompanyShareOptionDeltaFactor]:
        """
        Get portfolio company share option delta factor by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            PortfolioCompanyShareOptionDeltaFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[PortfolioCompanyShareOptionDeltaFactor]:
        """
        Get portfolio company share option delta factor by name.
        
        Args:
            name: The factor name
            
        Returns:
            PortfolioCompanyShareOptionDeltaFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_underlying_symbol(self, underlying_symbol: str) -> List[PortfolioCompanyShareOptionDeltaFactor]:
        """
        Get portfolio company share option delta factors by underlying portfolio symbol.
        
        Args:
            underlying_symbol: The underlying portfolio symbol
            
        Returns:
            List of PortfolioCompanyShareOptionDeltaFactor entities for the underlying portfolio
        """
        pass
    
    @abstractmethod
    def get_by_date_range(self, start_date: str, end_date: str) -> List[PortfolioCompanyShareOptionDeltaFactor]:
        """
        Get portfolio company share option delta factors by date range.
        
        Args:
            start_date: Start date (ISO format YYYY-MM-DD)
            end_date: End date (ISO format YYYY-MM-DD)
            
        Returns:
            List of PortfolioCompanyShareOptionDeltaFactor entities within the date range
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[PortfolioCompanyShareOptionDeltaFactor]:
        """
        Get all portfolio company share option delta factors.
        
        Returns:
            List of PortfolioCompanyShareOptionDeltaFactor entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: PortfolioCompanyShareOptionDeltaFactor) -> Optional[PortfolioCompanyShareOptionDeltaFactor]:
        """
        Add/persist a portfolio company share option delta factor entity.
        
        Args:
            entity: The PortfolioCompanyShareOptionDeltaFactor entity to persist
            
        Returns:
            Persisted PortfolioCompanyShareOptionDeltaFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: PortfolioCompanyShareOptionDeltaFactor) -> Optional[PortfolioCompanyShareOptionDeltaFactor]:
        """
        Update a portfolio company share option delta factor entity.
        
        Args:
            entity: The PortfolioCompanyShareOptionDeltaFactor entity to update
            
        Returns:
            Updated PortfolioCompanyShareOptionDeltaFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete a portfolio company share option delta factor entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass