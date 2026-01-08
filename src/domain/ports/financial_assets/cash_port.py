from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.cash import Cash


class CashPort(ABC):
    """Port interface for Cash entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, cash_id: int) -> Optional[Cash]:
        """Retrieve a cash entity by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[Cash]:
        """Retrieve all cash entities."""
        pass
    
    @abstractmethod
    def get_active_cash(self) -> List[Cash]:
        """Retrieve all active cash entities (end_date is None or in the future)."""
        pass
    
    @abstractmethod
    def add(self, cash: Cash) -> Cash:
        """Add a new cash entity."""
        pass
    
    @abstractmethod
    def update(self, cash: Cash) -> Cash:
        """Update an existing cash entity."""
        pass
    
    @abstractmethod
    def delete(self, cash_id: int) -> bool:
        """Delete a cash entity by its ID."""
        pass