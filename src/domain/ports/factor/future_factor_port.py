"""
Future Factor Port - Repository interface for FutureFactor entities.

This port defines the contract for repositories that handle FutureFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_factor import FutureFactor


class FutureFactorPort(ABC):
    """Port interface for FutureFactor repositories"""
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[FutureFactor]:
    #     """
    #     Get future factor by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         FutureFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[FutureFactor]:
    #     """
    #     Get future factor by name.
        
    #     Args:
    #         name: The factor name
            
    #     Returns:
    #         FutureFactor entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_underlying_symbol(self, symbol: str) -> List[FutureFactor]:
    #     """
    #     Get future factors by underlying asset symbol.
        
    #     Args:
    #         symbol: The underlying asset symbol (e.g., 'ES', 'CL', 'GC')
            
    #     Returns:
    #         List of FutureFactor entities for the underlying asset
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_contract_month(self, contract_month: str) -> List[FutureFactor]:
    #     """
    #     Get future factors by contract month.
        
    #     Args:
    #         contract_month: The contract month (e.g., 'M26' for June 2026)
            
    #     Returns:
    #         List of FutureFactor entities for the contract month
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_exchange(self, exchange: str) -> List[FutureFactor]:
    #     """
    #     Get future factors by exchange.
        
    #     Args:
    #         exchange: The exchange (e.g., 'CME', 'CBOT', 'NYMEX')
            
    #     Returns:
    #         List of FutureFactor entities traded on the exchange
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_roll_yield_range(self, min_yield: Optional[float] = None, max_yield: Optional[float] = None) -> List[FutureFactor]:
    #     """
    #     Get future factors by roll yield range.
        
    #     Args:
    #         min_yield: Minimum roll yield
    #         max_yield: Maximum roll yield
            
    #     Returns:
    #         List of FutureFactor entities within the roll yield range
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_group(self, group: str) -> List[FutureFactor]:
    #     """
    #     Get future factors by group.
        
    #     Args:
    #         group: The factor group
            
    #     Returns:
    #         List of FutureFactor entities in the group
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[FutureFactor]:
    #     """
    #     Get all future factors.
        
    #     Returns:
    #         List of FutureFactor entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: FutureFactor) -> Optional[FutureFactor]:
    #     """
    #     Add/persist a future factor entity.
        
    #     Args:
    #         entity: The FutureFactor entity to persist
            
    #     Returns:
    #         Persisted FutureFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: FutureFactor) -> Optional[FutureFactor]:
    #     """
    #     Update a future factor entity.
        
    #     Args:
    #         entity: The FutureFactor entity to update
            
    #     Returns:
    #         Updated FutureFactor entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete a future factor entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass