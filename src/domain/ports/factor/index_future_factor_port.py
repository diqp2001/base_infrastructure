"""
Port (interface) for Index Future Factor operations.
Defines the contract for index future factor repositories in different contexts.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.future.index_future_factor import IndexFutureFactor


class IndexFutureFactorPort(ABC):
    """
    Port defining the interface for index future factor operations.
    
    This port can be implemented by:
    - Local repositories (database persistence)
    - IBKR repositories (API data enhancement + local persistence)
    - Mock repositories (testing)
    """

    @abstractmethod
    def get_or_create(self, primary_key: str, **kwargs) -> Optional[IndexFutureFactor]:
        """
        Get an existing index future factor by primary key or create if not exists.
        
        Args:
            primary_key: The primary identifier (typically factor name)
            **kwargs: Additional parameters for factor creation
            
        Returns:
            IndexFutureFactor entity if successful, None otherwise
        """
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[IndexFutureFactor]:
        """
        Get index future factor by name.
        
        Args:
            name: Factor name
            
        Returns:
            IndexFutureFactor entity if found, None otherwise
        """
        pass

    @abstractmethod
    def get_by_id(self, factor_id: int) -> Optional[IndexFutureFactor]:
        """
        Get index future factor by ID.
        
        Args:
            factor_id: Factor ID
            
        Returns:
            IndexFutureFactor entity if found, None otherwise
        """
        pass

    @abstractmethod
    def get_all(self) -> List[IndexFutureFactor]:
        """
        Get all index future factors.
        
        Returns:
            List of IndexFutureFactor entities
        """
        pass

    @abstractmethod
    def add(self, entity: IndexFutureFactor) -> Optional[IndexFutureFactor]:
        """
        Add a new index future factor.
        
        Args:
            entity: IndexFutureFactor entity to add
            
        Returns:
            Added IndexFutureFactor entity if successful, None otherwise
        """
        pass

    @abstractmethod
    def update(self, entity: IndexFutureFactor) -> Optional[IndexFutureFactor]:
        """
        Update an existing index future factor.
        
        Args:
            entity: IndexFutureFactor entity to update
            
        Returns:
            Updated IndexFutureFactor entity if successful, None otherwise
        """
        pass

    @abstractmethod
    def delete(self, factor_id: int) -> bool:
        """
        Delete an index future factor by ID.
        
        Args:
            factor_id: Factor ID to delete
            
        Returns:
            True if successful, False otherwise
        """
        pass