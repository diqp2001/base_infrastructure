from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.derivatives.future.future import Future


class FuturePort(ABC):
    """Port interface for Future entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, future_id: int) -> Optional[Future]:
    #     """Retrieve a future by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[Future]:
    #     """Retrieve all futures."""
    #     pass
    
    # @abstractmethod
    # def get_by_expiration_date(self, expiration_date: str) -> List[Future]:
    #     """Retrieve futures by their expiration date."""
    #     pass
    
    # @abstractmethod
    # def get_by_contract_size(self, contract_size: float) -> List[Future]:
    #     """Retrieve futures by their contract size."""
    #     pass
    
    # @abstractmethod
    # def get_by_exchange_id(self, exchange_id: int) -> List[Future]:
    #     """Retrieve futures by their exchange ID."""
    #     pass
    
    # @abstractmethod
    # def get_active_futures(self) -> List[Future]:
    #     """Retrieve all active futures (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, future: Future) -> Future:
    #     """Add a new future."""
    #     pass
    
    # @abstractmethod
    # def update(self, future: Future) -> Future:
    #     """Update an existing future."""
    #     pass
    
    # @abstractmethod
    # def delete(self, future_id: int) -> bool:
    #     """Delete a future by its ID."""
    #     pass