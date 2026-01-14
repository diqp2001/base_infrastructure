from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.finance.financial_assets.commodity import Commodity


class CommodityPort(ABC):
    """Port interface for Commodity entity operations following repository pattern."""
    
    # @abstractmethod
    # def get_by_id(self, commodity_id: int) -> Optional[Commodity]:
    #     """Retrieve a commodity entity by its ID."""
    #     pass
    
    # @abstractmethod
    # def get_all(self) -> List[Commodity]:
    #     """Retrieve all commodity entities."""
    #     pass
    
    # @abstractmethod
    # def get_active_commodities(self) -> List[Commodity]:
    #     """Retrieve all active commodity entities (end_date is None or in the future)."""
    #     pass
    
    # @abstractmethod
    # def add(self, commodity: Commodity) -> Commodity:
    #     """Add a new commodity entity."""
    #     pass
    
    # @abstractmethod
    # def update(self, commodity: Commodity) -> Commodity:
    #     """Update an existing commodity entity."""
    #     pass
    
    # @abstractmethod
    # def delete(self, commodity_id: int) -> bool:
    #     """Delete a commodity entity by its ID."""
    #     pass