"""
Index Future Option Port - Repository interface for IndexFutureOption entities.

This port defines the contract for repositories that handle IndexFutureOption
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.finance.financial_assets.derivatives.option.index_future_option import IndexFutureOption


class IndexFutureOptionPort(ABC):
    """Port interface for IndexFutureOption repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[IndexFutureOption]:
    #     """
    #     Get index future option by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         IndexFutureOption entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_symbol(self, symbol: str) -> Optional[IndexFutureOption]:
    #     """
    #     Get index future option by symbol.
        
    #     Args:
    #         symbol: The option symbol
            
    #     Returns:
    #         IndexFutureOption entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_index_symbol(self, index_symbol: str) -> List[IndexFutureOption]:
    #     """
    #     Get index future options by underlying index symbol.
        
    #     Args:
    #         index_symbol: The underlying index symbol (e.g., 'SPX', 'NDX', 'RUT')
            
    #     Returns:
    #         List of IndexFutureOption entities for the underlying index
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_strike_range(self, min_strike: Optional[float] = None, max_strike: Optional[float] = None) -> List[IndexFutureOption]:
    #     """
    #     Get index future options by strike price range.
        
    #     Args:
    #         min_strike: Minimum strike price
    #         max_strike: Maximum strike price
            
    #     Returns:
    #         List of IndexFutureOption entities within the strike range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_expiration_date(self, expiration_date: str) -> List[IndexFutureOption]:
    #     """
    #     Get index future options by expiration date.
        
    #     Args:
    #         expiration_date: Expiration date (ISO format YYYY-MM-DD)
            
    #     Returns:
    #         List of IndexFutureOption entities with the specified expiration date
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[IndexFutureOption]:
    #     """
    #     Get all index future options.
        
    #     Returns:
    #         List of IndexFutureOption entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: IndexFutureOption) -> Optional[IndexFutureOption]:
    #     """
    #     Add/persist an index future option entity.
        
    #     Args:
    #         entity: The IndexFutureOption entity to persist
            
    #     Returns:
    #         Persisted IndexFutureOption entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: IndexFutureOption) -> Optional[IndexFutureOption]:
    #     """
    #     Update an index future option entity.
        
    #     Args:
    #         entity: The IndexFutureOption entity to update
            
    #     Returns:
    #         Updated IndexFutureOption entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete an index future option entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass