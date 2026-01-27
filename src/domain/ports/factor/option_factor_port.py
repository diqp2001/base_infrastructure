"""
Option Factor Port - Repository interface for OptionFactor entities.

This port defines the contract for repositories that handle OptionFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.option_factor import OptionFactor


class OptionFactorPort(ABC):
    """Port interface for OptionFactor repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[OptionFactor]:
        """
        Get option factor by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            OptionFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[OptionFactor]:
        """
        Get option factor by name.
        
        Args:
            name: The factor name
            
        Returns:
            OptionFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_underlying_symbol(self, symbol: str) -> List[OptionFactor]:
        """
        Get option factors by underlying asset symbol.
        
        Args:
            symbol: The underlying asset symbol (e.g., 'AAPL', 'SPY')
            
        Returns:
            List of OptionFactor entities for the underlying asset
        """
        pass
    
    @abstractmethod
    def get_by_option_type(self, option_type: str) -> List[OptionFactor]:
        """
        Get option factors by option type.
        
        Args:
            option_type: The option type ('call' or 'put')
            
        Returns:
            List of OptionFactor entities for the option type
        """
        pass
    
    @abstractmethod
    def get_by_strike_range(self, min_strike: Optional[float] = None, max_strike: Optional[float] = None) -> List[OptionFactor]:
        """
        Get option factors by strike price range.
        
        Args:
            min_strike: Minimum strike price
            max_strike: Maximum strike price
            
        Returns:
            List of OptionFactor entities within the strike range
        """
        pass
    
    @abstractmethod
    def get_by_expiration_range(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[OptionFactor]:
        """
        Get option factors by expiration date range.
        
        Args:
            start_date: Start date (ISO format YYYY-MM-DD)
            end_date: End date (ISO format YYYY-MM-DD)
            
        Returns:
            List of OptionFactor entities within the expiration range
        """
        pass
    
    @abstractmethod
    def get_by_moneyness(self, moneyness_type: str) -> List[OptionFactor]:
        """
        Get option factors by moneyness.
        
        Args:
            moneyness_type: The moneyness type ('ITM', 'ATM', 'OTM')
            
        Returns:
            List of OptionFactor entities with the specified moneyness
        """
        pass
    
    @abstractmethod
    def get_by_group(self, group: str) -> List[OptionFactor]:
        """
        Get option factors by group.
        
        Args:
            group: The factor group
            
        Returns:
            List of OptionFactor entities in the group
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[OptionFactor]:
        """
        Get all option factors.
        
        Returns:
            List of OptionFactor entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: OptionFactor) -> Optional[OptionFactor]:
        """
        Add/persist an option factor entity.
        
        Args:
            entity: The OptionFactor entity to persist
            
        Returns:
            Persisted OptionFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: OptionFactor) -> Optional[OptionFactor]:
        """
        Update an option factor entity.
        
        Args:
            entity: The OptionFactor entity to update
            
        Returns:
            Updated OptionFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete an option factor entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass