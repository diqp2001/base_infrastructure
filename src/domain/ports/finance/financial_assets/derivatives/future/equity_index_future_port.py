from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.derivatives.future.equity_index_future import EquityIndexFuture


class EquityIndexFuturePort(ABC):
    """Port interface for EquityIndexFuture entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, future_id: int) -> Optional[EquityIndexFuture]:
        """Retrieve an equity index future by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[EquityIndexFuture]:
        """Retrieve all equity index futures."""
        pass
    
    @abstractmethod
    def get_by_index_id(self, index_id: int) -> List[EquityIndexFuture]:
        """Retrieve equity index futures by their underlying index ID."""
        pass
    
    @abstractmethod
    def get_by_index_type(self, index_type: str) -> List[EquityIndexFuture]:
        """Retrieve equity index futures by their underlying index type."""
        pass
    
    @abstractmethod
    def get_by_multiplier(self, multiplier: float) -> List[EquityIndexFuture]:
        """Retrieve equity index futures by their multiplier."""
        pass
    
    @abstractmethod
    def get_active_futures(self) -> List[EquityIndexFuture]:
        """Retrieve all active equity index futures (end_date is None or in the future)."""
        pass
    
    @abstractmethod
    def add(self, future: EquityIndexFuture) -> EquityIndexFuture:
        """Add a new equity index future."""
        pass
    
    @abstractmethod
    def update(self, future: EquityIndexFuture) -> EquityIndexFuture:
        """Update an existing equity index future."""
        pass
    
    @abstractmethod
    def delete(self, future_id: int) -> bool:
        """Delete an equity index future by its ID."""
        pass