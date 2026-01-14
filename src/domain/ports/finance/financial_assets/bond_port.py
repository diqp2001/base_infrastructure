"""
Bond Port - Repository interface for Bond entities.

This port defines the contract for repositories that handle Bond
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from datetime import date
from decimal import Decimal

from src.domain.entities.finance.financial_assets.bond import Bond


class BondPort(ABC):
    """Port interface for Bond repositories"""
    
    # @abstractmethod
    # def get_or_create(self, symbol: str) -> Optional[Bond]:
    #     """
    #     Get or create a bond by symbol.
        
    #     Args:
    #         symbol: The bond symbol/ISIN
            
    #     Returns:
    #         Bond entity or None if creation/retrieval failed
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_symbol(self, symbol: str) -> Optional[Bond]:
    #     """
    #     Get bond by symbol.
        
    #     Args:
    #         symbol: The bond symbol/ISIN
            
    #     Returns:
    #         Bond entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_isin(self, isin: str) -> Optional[Bond]:
    #     """
    #     Get bond by ISIN.
        
    #     Args:
    #         isin: The ISIN code
            
    #     Returns:
    #         Bond entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_cusip(self, cusip: str) -> Optional[Bond]:
    #     """
    #     Get bond by CUSIP.
        
    #     Args:
    #         cusip: The CUSIP code
            
    #     Returns:
    #         Bond entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[Bond]:
    #     """
    #     Get bond by ID.
        
    #     Args:
    #         entity_id: The entity ID
            
    #     Returns:
    #         Bond entity or None if not found
    #     """
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[Bond]:
    #     """
    #     Get all bonds.
        
    #     Returns:
    #         List of Bond entities
    #     """
    #     pass
    
    # @abstractmethod
    # def get_by_maturity_range(self, start_date: date, end_date: date) -> List[Bond]:
    #     """
    #     Get bonds maturing within date range.
        
    #     Args:
    #         start_date: Start of maturity date range
    #         end_date: End of maturity date range
            
    #     Returns:
    #         List of Bond entities
    #     """
    #     pass
    
    # @abstractmethod
    # def add(self, entity: Bond) -> Optional[Bond]:
    #     """
    #     Add/persist a bond entity.
        
    #     Args:
    #         entity: The Bond entity to persist
            
    #     Returns:
    #         Persisted Bond entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def update(self, entity: Bond) -> Optional[Bond]:
    #     """
    #     Update a bond entity.
        
    #     Args:
    #         entity: The Bond entity to update
            
    #     Returns:
    #         Updated Bond entity or None if failed
    #     """
    #     pass
    
    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """
    #     Delete a bond entity.
        
    #     Args:
    #         entity_id: The entity ID to delete
            
    #     Returns:
    #         True if deleted successfully, False otherwise
    #     """
    #     pass