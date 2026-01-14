from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.index.vix import Vix


class VixPort(ABC):
    """Port interface for Vix entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, vix_id: int) -> Optional[Vix]:
    #     """Retrieve a VIX by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[Vix]:
    #     """Retrieve all VIX entities."""
    #     pass
    
    # @abstractmethod
    # def get_active_vix(self) -> List[Vix]:
    #     """Retrieve all active VIX entities (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, vix: Vix) -> Vix:
    #     """Add a new VIX entity."""
    #     pass
    
    # @abstractmethod
    # def update(self, vix: Vix) -> Vix:
    #     """Update an existing VIX entity."""
    #     pass
    
    # @abstractmethod
    # def delete(self, vix_id: int) -> bool:
    #     """Delete a VIX entity by its ID."""
    #     pass