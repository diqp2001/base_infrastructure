"""
Security Factor Port - Repository interface for SecurityFactor entities.

This port defines the contract for repositories that handle SecurityFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.security_factor import SecurityFactor


class SecurityFactorPort(ABC):
    """Port interface for SecurityFactor repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[SecurityFactor]:
        """
        Get security factor by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            SecurityFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[SecurityFactor]:
        """
        Get security factor by name.
        
        Args:
            name: The factor name
            
        Returns:
            SecurityFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_symbol(self, symbol: str) -> List[SecurityFactor]:
        """
        Get security factors by symbol.
        
        Args:
            symbol: The security symbol (e.g., 'AAPL', 'GOOGL')
            
        Returns:
            List of SecurityFactor entities for the symbol
        """
        pass
    
    @abstractmethod
    def get_by_exchange(self, exchange: str) -> List[SecurityFactor]:
        """
        Get security factors by exchange.
        
        Args:
            exchange: The exchange (e.g., 'NASDAQ', 'NYSE', 'LSE')
            
        Returns:
            List of SecurityFactor entities traded on the exchange
        """
        pass
    
    @abstractmethod
    def get_by_sector(self, sector: str) -> List[SecurityFactor]:
        """
        Get security factors by sector.
        
        Args:
            sector: The sector (e.g., 'Technology', 'Healthcare', 'Finance')
            
        Returns:
            List of SecurityFactor entities in the sector
        """
        pass
    
    @abstractmethod
    def get_by_market_cap_range(self, min_cap: Optional[float] = None, max_cap: Optional[float] = None) -> List[SecurityFactor]:
        """
        Get security factors by market capitalization range.
        
        Args:
            min_cap: Minimum market cap
            max_cap: Maximum market cap
            
        Returns:
            List of SecurityFactor entities within the market cap range
        """
        pass
    
    @abstractmethod
    def get_by_security_type(self, security_type: str) -> List[SecurityFactor]:
        """
        Get security factors by security type.
        
        Args:
            security_type: The security type (e.g., 'stock', 'etf', 'reit')
            
        Returns:
            List of SecurityFactor entities of the specified type
        """
        pass
    
    @abstractmethod
    def get_by_group(self, group: str) -> List[SecurityFactor]:
        """
        Get security factors by group.
        
        Args:
            group: The factor group
            
        Returns:
            List of SecurityFactor entities in the group
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[SecurityFactor]:
        """
        Get all security factors.
        
        Returns:
            List of SecurityFactor entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: SecurityFactor) -> Optional[SecurityFactor]:
        """
        Add/persist a security factor entity.
        
        Args:
            entity: The SecurityFactor entity to persist
            
        Returns:
            Persisted SecurityFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: SecurityFactor) -> Optional[SecurityFactor]:
        """
        Update a security factor entity.
        
        Args:
            entity: The SecurityFactor entity to update
            
        Returns:
            Updated SecurityFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete a security factor entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass