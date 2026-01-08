from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.stock import Stock


class StockPort(ABC):
    """Port interface for Stock entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, stock_id: int) -> Optional[Stock]:
        """Retrieve a stock by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[Stock]:
        """Retrieve all stocks."""
        pass
    
    @abstractmethod
    def get_active_stocks(self) -> List[Stock]:
        """Retrieve all active stocks (end_date is None or in the future)."""
        pass
    
    @abstractmethod
    def add(self, stock: Stock) -> Stock:
        """Add a new stock."""
        pass
    
    @abstractmethod
    def update(self, stock: Stock) -> Stock:
        """Update an existing stock."""
        pass
    
    @abstractmethod
    def delete(self, stock_id: int) -> bool:
        """Delete a stock by its ID."""
        pass