"""
Company Share Port - Repository interface for Company Share entities.

This port defines the contract for repositories that handle Company Share
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from decimal import Decimal

from src.domain.entities.finance.financial_assets.share.company_share.company_share import CompanyShare


class CompanySharePort(ABC):
    """Port interface for Company Share repositories"""
    
    @abstractmethod
    def get_or_create(self, symbol: str) -> Optional[CompanyShare]:
        """
        Get or create a company share by symbol.
        
        Args:
            symbol: The share symbol (e.g., 'AAPL', 'TSLA')
            
        Returns:
            CompanyShare entity or None if creation/retrieval failed
        """
        pass
    
    @abstractmethod
    def get_by_symbol(self, symbol: str) -> Optional[CompanyShare]:
        """
        Get company share by symbol.
        
        Args:
            symbol: The share symbol
            
        Returns:
            CompanyShare entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_ticker(self, ticker: str) -> Optional[CompanyShare]:
        """
        Get company share by ticker (alias for get_by_symbol for backward compatibility).
        
        Args:
            ticker: The share ticker
            
        Returns:
            CompanyShare entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[CompanyShare]:
        """
        Get company share by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            CompanyShare entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[CompanyShare]:
        """
        Get all company shares.
        
        Returns:
            List of CompanyShare entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: CompanyShare) -> Optional[CompanyShare]:
        """
        Add/persist a company share entity.
        
        Args:
            entity: The CompanyShare entity to persist
            
        Returns:
            Persisted CompanyShare entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: CompanyShare) -> Optional[CompanyShare]:
        """
        Update a company share entity.
        
        Args:
            entity: The CompanyShare entity to update
            
        Returns:
            Updated CompanyShare entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete a company share entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass