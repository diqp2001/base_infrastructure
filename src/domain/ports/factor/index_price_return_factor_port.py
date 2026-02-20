"""
Index Price Return Factor Port - Domain interface for IndexPriceReturnFactor repository operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.factor.finance.financial_assets.index.index_price_return_factor import IndexPriceReturnFactor


class IndexPriceReturnFactorPort(ABC):
    """Abstract interface for IndexPriceReturnFactor repository operations."""

    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[IndexPriceReturnFactor]:
        """Get IndexPriceReturnFactor by ID."""
        pass

    @abstractmethod  
    def get_by_name(self, name: str) -> Optional[IndexPriceReturnFactor]:
        """Get IndexPriceReturnFactor by name."""
        pass

    @abstractmethod
    def get_by_group(self, group: str) -> List[IndexPriceReturnFactor]:
        """Get IndexPriceReturnFactor entities by group."""
        pass

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[IndexPriceReturnFactor]:
        """Get IndexPriceReturnFactor entities by subgroup."""
        pass

    @abstractmethod
    def get_all(self) -> List[IndexPriceReturnFactor]:
        """Get all IndexPriceReturnFactor entities."""
        pass

    @abstractmethod
    def add(self, entity: IndexPriceReturnFactor) -> Optional[IndexPriceReturnFactor]:
        """Add IndexPriceReturnFactor entity."""
        pass

    @abstractmethod
    def update(self, entity_id: int, **kwargs) -> Optional[IndexPriceReturnFactor]:
        """Update IndexPriceReturnFactor entity."""
        pass

    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """Delete IndexPriceReturnFactor entity."""
        pass