from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.index.index import Index


class IndexPort(ABC):
    """Port interface for Index entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, index_id: int) -> Optional[Index]:
    #     """Retrieve an index by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[Index]:
    #     """Retrieve all indexes."""
    #     pass
    
    # @abstractmethod
    # def get_active_indexes(self) -> List[Index]:
    #     """Retrieve all active indexes (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, index: Index) -> Index:
    #     """Add a new index."""
    #     pass
    
    # @abstractmethod
    # def update(self, index: Index) -> Index:
    #     """Update an existing index."""
    #     pass
    
    # @abstractmethod
    # def delete(self, index_id: int) -> bool:
    #     """Delete an index by its ID."""
    #     pass