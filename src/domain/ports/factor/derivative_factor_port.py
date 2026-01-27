"""
Derivative Factor Port - Repository interface for DerivativeFactor entities.

This port defines the contract for repositories that handle DerivativeFactor
entities, ensuring both local and external data source repositories implement the same interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.financial_assets.derivatives.derivative_factor import DerivativeFactor


class DerivativeFactorPort(ABC):
    """Port interface for DerivativeFactor repositories"""
    
    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[DerivativeFactor]:
        """
        Get derivative factor by ID.
        
        Args:
            entity_id: The entity ID
            
        Returns:
            DerivativeFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_name(self, name: str) -> Optional[DerivativeFactor]:
        """
        Get derivative factor by name.
        
        Args:
            name: The factor name
            
        Returns:
            DerivativeFactor entity or None if not found
        """
        pass
    
    @abstractmethod
    def get_by_derivative_type(self, derivative_type: str) -> List[DerivativeFactor]:
        """
        Get derivative factors by derivative type.
        
        Args:
            derivative_type: The derivative type (e.g., 'option', 'future', 'swap', 'forward')
            
        Returns:
            List of DerivativeFactor entities for the derivative type
        """
        pass
    
    @abstractmethod
    def get_by_underlying_symbol(self, symbol: str) -> List[DerivativeFactor]:
        """
        Get derivative factors by underlying asset symbol.
        
        Args:
            symbol: The underlying asset symbol (e.g., 'AAPL', 'SPY')
            
        Returns:
            List of DerivativeFactor entities for the underlying asset
        """
        pass
    
    @abstractmethod
    def get_by_expiration_range(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[DerivativeFactor]:
        """
        Get derivative factors by expiration date range.
        
        Args:
            start_date: Start date (ISO format YYYY-MM-DD)
            end_date: End date (ISO format YYYY-MM-DD)
            
        Returns:
            List of DerivativeFactor entities within the expiration range
        """
        pass
    
    @abstractmethod
    def get_by_group(self, group: str) -> List[DerivativeFactor]:
        """
        Get derivative factors by group.
        
        Args:
            group: The factor group
            
        Returns:
            List of DerivativeFactor entities in the group
        """
        pass
    
    @abstractmethod
    def get_all(self) -> List[DerivativeFactor]:
        """
        Get all derivative factors.
        
        Returns:
            List of DerivativeFactor entities
        """
        pass
    
    @abstractmethod
    def add(self, entity: DerivativeFactor) -> Optional[DerivativeFactor]:
        """
        Add/persist a derivative factor entity.
        
        Args:
            entity: The DerivativeFactor entity to persist
            
        Returns:
            Persisted DerivativeFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def update(self, entity: DerivativeFactor) -> Optional[DerivativeFactor]:
        """
        Update a derivative factor entity.
        
        Args:
            entity: The DerivativeFactor entity to update
            
        Returns:
            Updated DerivativeFactor entity or None if failed
        """
        pass
    
    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """
        Delete a derivative factor entity.
        
        Args:
            entity_id: The entity ID to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        pass