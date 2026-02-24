"""
Index Future Option Price Return Factor Port - Repository interface for IndexFutureOptionPriceReturnFactor entities.

This port defines the contract for repositories that handle IndexFutureOptionPriceReturnFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.index_future_option_price_return_factor import IndexFutureOptionPriceReturnFactor


class IndexFutureOptionPriceReturnFactorPort(ABC):
    """Port interface for IndexFutureOptionPriceReturnFactor repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[IndexFutureOptionPriceReturnFactor]:
        """
        Get index future option price return factor by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            IndexFutureOptionPriceReturnFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[IndexFutureOptionPriceReturnFactor]:
        """
        Get index future option price return factor by name.
        
        Args:
            name: The factor name
            
        Returns:
            IndexFutureOptionPriceReturnFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_index_symbol(self, index_symbol: str) -> List[IndexFutureOptionPriceReturnFactor]:
        """
        Get index future option price return factors by underlying index symbol.
        
        Args:
            index_symbol: The underlying index symbol (e.g., 'SPX', 'NDX', 'RUT')
            
        Returns:
            List of IndexFutureOptionPriceReturnFactor entities for the underlying index
        """
        pass
    
    @abstractmethod
    def get_by_return_type(self, return_type: str) -> List[IndexFutureOptionPriceReturnFactor]:
        """
        Get index future option price return factors by return type.
        
        Args:
            return_type: The return type ('simple', 'log', 'volatility_adjusted')
            
        Returns:
            List of IndexFutureOptionPriceReturnFactor entities for the return type
        """
        pass
    
    @abstractmethod
    def get_by_date_range(self, start_date: str, end_date: str) -> List[IndexFutureOptionPriceReturnFactor]:
        """
        Get index future option price return factors by date range.
        
        Args:
            start_date: Start date (ISO format YYYY-MM-DD)
            end_date: End date (ISO format YYYY-MM-DD)
            
        Returns:
            List of IndexFutureOptionPriceReturnFactor entities within the date range
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[IndexFutureOptionPriceReturnFactor]:
        """
        Get all index future option price return factors.
        
        Returns:
            List of IndexFutureOptionPriceReturnFactor entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: IndexFutureOptionPriceReturnFactor) -> Optional[IndexFutureOptionPriceReturnFactor]:
        """
        Add/persist an index future option price return factor entity.
        
        Args:
            entity: The IndexFutureOptionPriceReturnFactor entity to persist
            
        Returns:
            Persisted IndexFutureOptionPriceReturnFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: IndexFutureOptionPriceReturnFactor) -> Optional[IndexFutureOptionPriceReturnFactor]:
        """
        Update an index future option price return factor entity.
        
        Args:
            entity: The IndexFutureOptionPriceReturnFactor entity to update
            
        Returns:
            Updated IndexFutureOptionPriceReturnFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete an index future option price return factor entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass