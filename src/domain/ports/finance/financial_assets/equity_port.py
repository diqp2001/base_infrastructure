from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.equity import Equity


class EquityPort(ABC):
    """Port interface for Equity entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, equity_id: int) -> Optional[Equity]:
    #     """Retrieve an equity entity by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[Equity]:
    #     """Retrieve all equity entities."""
    #     pass
    
    # @abstractmethod
    # def get_active_equities(self) -> List[Equity]:
    #     """Retrieve all active equity entities (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, equity: Equity) -> Equity:
    #     """Add a new equity entity."""
    #     pass
    
    # @abstractmethod
    # def update(self, equity: Equity) -> Equity:
    #     """Update an existing equity entity."""
    #     pass
    
    # @abstractmethod
    # def delete(self, equity_id: int) -> bool:
    #     """Delete an equity entity by its ID."""
    #     pass