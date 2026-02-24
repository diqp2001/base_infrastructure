"""
Index Future Option Price Factor Port - Repository interface for IndexFutureOptionPriceFactor entities.

This port defines the contract for repositories that handle IndexFutureOptionPriceFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.index_future_option_price_factor import IndexFutureOptionPriceFactor


class IndexFutureOptionPriceFactorPort(ABC):
    """Port interface for IndexFutureOptionPriceFactor repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[IndexFutureOptionPriceFactor]:
        """
        Get index future option price factor by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            IndexFutureOptionPriceFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[IndexFutureOptionPriceFactor]:
        """
        Get index future option price factor by name.
        
        Args:
            name: The factor name
            
        Returns:
            IndexFutureOptionPriceFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_index_symbol(self, index_symbol: str) -> List[IndexFutureOptionPriceFactor]:
        """
        Get index future option price factors by underlying index symbol.
        
        Args:
            index_symbol: The underlying index symbol (e.g., 'SPX', 'NDX', 'RUT')
            
        Returns:
            List of IndexFutureOptionPriceFactor entities for the underlying index
        """
        pass
    
    @abstractmethod
    def get_by_date_range(self, start_date: str, end_date: str) -> List[IndexFutureOptionPriceFactor]:
        """
        Get index future option price factors by date range.
        
        Args:
            start_date: Start date (ISO format YYYY-MM-DD)
            end_date: End date (ISO format YYYY-MM-DD)
            
        Returns:
            List of IndexFutureOptionPriceFactor entities within the date range
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[IndexFutureOptionPriceFactor]:
        """
        Get all index future option price factors.
        
        Returns:
            List of IndexFutureOptionPriceFactor entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: IndexFutureOptionPriceFactor) -> Optional[IndexFutureOptionPriceFactor]:
        """
        Add/persist an index future option price factor entity.
        
        Args:
            entity: The IndexFutureOptionPriceFactor entity to persist
            
        Returns:
            Persisted IndexFutureOptionPriceFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: IndexFutureOptionPriceFactor) -> Optional[IndexFutureOptionPriceFactor]:
        """
        Update an index future option price factor entity.
        
        Args:
            entity: The IndexFutureOptionPriceFactor entity to update
            
        Returns:
            Updated IndexFutureOptionPriceFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete an index future option price factor entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass