from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.derivatives.future.treasury_bond_future import TreasuryBondFuture


class TreasuryBondFuturePort(ABC):
    """Port interface for TreasuryBondFuture entity operations following repository pattern."""
    
    @abstractmethod
    def get_by_id(self, future_id: int) -> Optional[TreasuryBondFuture]:
        """Retrieve a treasury bond future by its ID."""
        pass
    
    @abstractmethod
    def get_all(self) -> List[TreasuryBondFuture]:
        """Retrieve all treasury bond futures."""
        pass
    
    @abstractmethod
    def get_by_treasury_type(self, treasury_type: str) -> List[TreasuryBondFuture]:
        """Retrieve treasury bond futures by their underlying treasury type."""
        pass
    
    @abstractmethod
    def get_by_maturity_range(self, start_date: str, end_date: str) -> List[TreasuryBondFuture]:
        """Retrieve treasury bond futures within a maturity date range."""
        pass
    
    @abstractmethod
    def get_by_conversion_factor_range(self, min_factor: float, max_factor: float) -> List[TreasuryBondFuture]:
        """Retrieve treasury bond futures by their conversion factor range."""
        pass
    
    @abstractmethod
    def get_active_futures(self) -> List[TreasuryBondFuture]:
        """Retrieve all active treasury bond futures (end_date is None or in the future)."""
        pass
    
    @abstractmethod
    def add(self, future: TreasuryBondFuture) -> TreasuryBondFuture:
        """Add a new treasury bond future."""
        pass
    
    @abstractmethod
    def update(self, future: TreasuryBondFuture) -> TreasuryBondFuture:
        """Update an existing treasury bond future."""
        pass
    
    @abstractmethod
    def delete(self, future_id: int) -> bool:
        """Delete a treasury bond future by its ID."""
        pass