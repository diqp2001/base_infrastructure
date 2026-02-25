"""
Index Future Option Delta Factor Port - Repository interface for IndexFutureOptionDeltaFactor entities.

This port defines the contract for repositories that handle IndexFutureOptionDeltaFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.option.index_future_option_delta_factor import IndexFutureOptionDeltaFactor


class IndexFutureOptionDeltaFactorPort(ABC):
    """Port interface for IndexFutureOptionDeltaFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[IndexFutureOptionDeltaFactor]:
    #     """
    #     Get index future option delta factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         IndexFutureOptionDeltaFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[IndexFutureOptionDeltaFactor]:
    #     """
    #     Get index future option delta factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         IndexFutureOptionDeltaFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_index_symbol(self, index_symbol: str) -> List[IndexFutureOptionDeltaFactor]:
    #     """
    #     Get index future option delta factors by underlying index symbol.
        
    #     Args:
    #         index_symbol: The underlying index symbol (e.g., 'SPX', 'NDX', 'RUT')
            
    #     Returns:
    #         List of IndexFutureOptionDeltaFactor entities for the underlying index
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_delta_range(self, min_delta: Optional[float] = None, max_delta: Optional[float] = None) -> List[IndexFutureOptionDeltaFactor]:
    #     """
    #     Get index future option delta factors by delta range.
        
    #     Args:
    #         min_delta: Minimum delta value
    #         max_delta: Maximum delta value
            
    #     Returns:
    #         List of IndexFutureOptionDeltaFactor entities within the delta range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_option_type(self, option_type: str) -> List[IndexFutureOptionDeltaFactor]:
    #     """
    #     Get index future option delta factors by option type.
        
    #     Args:
    #         option_type: The option type ('call' or 'put')
            
    #     Returns:
    #         List of IndexFutureOptionDeltaFactor entities for the option type
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[IndexFutureOptionDeltaFactor]:
    #     """
    #     Get all index future option delta factors.
        
    #     Returns:
    #         List of IndexFutureOptionDeltaFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: IndexFutureOptionDeltaFactor) -> Optional[IndexFutureOptionDeltaFactor]:
    #     """
    #     Add/persist an index future option delta factor entity.
        
    #     Args:
    #         entity: The IndexFutureOptionDeltaFactor entity to persist
            
    #     Returns:
    #         Persisted IndexFutureOptionDeltaFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: IndexFutureOptionDeltaFactor) -> Optional[IndexFutureOptionDeltaFactor]:
    #     """
    #     Update an index future option delta factor entity.
        
    #     Args:
    #         entity: The IndexFutureOptionDeltaFactor entity to update
            
    #     Returns:
    #         Updated IndexFutureOptionDeltaFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete an index future option delta factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass