from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.derivatives.future.bond_future import BondFuture


class BondFuturePort(ABC):
    """Port interface for BondFuture entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, future_id: int) -> Optional[BondFuture]:
        """Retrieve a bond future by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[BondFuture]:
        """Retrieve all bond futures."""
        pass
    
    @abstractmethod
    def get_by_bond_type(self, bond_type: str) -> List[BondFuture]:
        """Retrieve bond futures by their underlying bond type."""
        pass
    
    @abstractmethod
    def get_by_maturity_range(self, start_date: str, end_date: str) -> List[BondFuture]:
        """Retrieve bond futures within a maturity date range."""
        pass
    
    @abstractmethod
    def get_by_duration_range(self, min_duration: float, max_duration: float) -> List[BondFuture]:
        """Retrieve bond futures by their duration range."""
        pass
    
    @abstractmethod
    def get_active_futures(self) -> List[BondFuture]:
        """Retrieve all active bond futures (end_date is None or in the future)."""
        pass
    
    @abstractmethod
    def add(self, future: BondFuture) -> BondFuture:
        """Add a new bond future."""
        pass
    
    @abstractmethod
    def update(self, future: BondFuture) -> BondFuture:
        """Update an existing bond future."""
        pass
    
    @abstractmethod
    def delete(self, future_id: int) -> bool:
        """Delete a bond future by its ID."""
        pass