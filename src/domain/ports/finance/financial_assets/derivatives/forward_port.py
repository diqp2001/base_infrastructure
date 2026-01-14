from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.derivatives.forward import Forward


class ForwardPort(ABC):
    """Port interface for Forward entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, forward_id: int) -> Optional[Forward]:
    #     """Retrieve a forward by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[Forward]:
    #     """Retrieve all forwards."""
    #     pass
    
    # @abstractmethod
    # def get_by_delivery_date(self, delivery_date: str) -> List[Forward]:
    #     """Retrieve forwards by their delivery date."""
    #     pass
    
    # @abstractmethod
    # def get_by_contract_type(self, contract_type: str) -> List[Forward]:
    #     """Retrieve forwards by their contract type."""
    #     pass
    
    # @abstractmethod
    # def get_active_forwards(self) -> List[Forward]:
    #     """Retrieve all active forwards (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, forward: Forward) -> Forward:
    #     """Add a new forward."""
    #     pass
    
    # @abstractmethod
    # def update(self, forward: Forward) -> Forward:
    #     """Update an existing forward."""
    #     pass
    
    # @abstractmethod
    # def delete(self, forward_id: int) -> bool:
    #     """Delete a forward by its ID."""
    #     pass