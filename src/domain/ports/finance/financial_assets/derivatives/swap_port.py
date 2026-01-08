from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.derivatives.swap import Swap


class SwapPort(ABC):
    """Port interface for Swap entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, swap_id: int) -> Optional[Swap]:
        """Retrieve a swap by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[Swap]:
        """Retrieve all swaps."""
        pass
    
    @abstractmethod
    def get_by_swap_type(self, swap_type: str) -> List[Swap]:
        """Retrieve swaps by their type (e.g., 'interest_rate', 'currency', 'credit')."""
        pass
    
    @abstractmethod
    def get_by_maturity_range(self, start_date: str, end_date: str) -> List[Swap]:
        """Retrieve swaps within a maturity date range."""
        pass
    
    @abstractmethod
    def get_active_swaps(self) -> List[Swap]:
        """Retrieve all active swaps (end_date is None or in the future)."""
        pass
    
    @abstractmethod
    def add(self, swap: Swap) -> Swap:
        """Add a new swap."""
        pass
    
    @abstractmethod
    def update(self, swap: Swap) -> Swap:
        """Update an existing swap."""
        pass
    
    @abstractmethod
    def delete(self, swap_id: int) -> bool:
        """Delete a swap by its ID."""
        pass