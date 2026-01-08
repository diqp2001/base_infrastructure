from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.derivatives.future.index_future import IndexFuture


class IndexFuturePort(ABC):
    """Port interface for IndexFuture entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, future_id: int) -> Optional[IndexFuture]:
        """Retrieve an index future by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[IndexFuture]:
        """Retrieve all index futures."""
        pass
    
    @abstractmethod
    def get_by_index_id(self, index_id: int) -> List[IndexFuture]:
        """Retrieve index futures by their underlying index ID."""
        pass
    
    @abstractmethod
    def get_by_tick_size(self, tick_size: float) -> List[IndexFuture]:
        """Retrieve index futures by their tick size."""
        pass
    
    @abstractmethod
    def get_by_settlement_type(self, settlement_type: str) -> List[IndexFuture]:
        """Retrieve index futures by their settlement type (cash or physical)."""
        pass
    
    @abstractmethod
    def get_active_futures(self) -> List[IndexFuture]:
        """Retrieve all active index futures (end_date is None or in the future)."""
        pass
    
    @abstractmethod
    def add(self, future: IndexFuture) -> IndexFuture:
        """Add a new index future."""
        pass
    
    @abstractmethod
    def update(self, future: IndexFuture) -> IndexFuture:
        """Update an existing index future."""
        pass
    
    @abstractmethod
    def delete(self, future_id: int) -> bool:
        """Delete an index future by its ID."""
        pass