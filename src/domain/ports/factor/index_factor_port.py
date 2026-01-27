"""
Index Factor Port - Domain interface for IndexFactor repository operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.factor.finance.financial_assets.index_factor import IndexFactor


class IndexFactorPort(ABC):
    """Abstract interface for IndexFactor repository operations."""

    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[IndexFactor]:
        """Get IndexFactor by ID."""
        pass

    @abstractmethod  
    def get_by_name(self, name: str) -> Optional[IndexFactor]:
        """Get IndexFactor by name."""
        pass

    @abstractmethod
    def get_by_group(self, group: str) -> List[IndexFactor]:
        """Get IndexFactor entities by group."""
        pass

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[IndexFactor]:
        """Get IndexFactor entities by subgroup."""
        pass

    @abstractmethod
    def get_all(self) -> List[IndexFactor]:
        """Get all IndexFactor entities."""
        pass

    @abstractmethod
    def add(self, entity: IndexFactor) -> Optional[IndexFactor]:
        """Add IndexFactor entity."""
        pass

    @abstractmethod
    def update(self, entity_id: int, **kwargs) -> Optional[IndexFactor]:
        """Update IndexFactor entity."""
        pass

    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """Delete IndexFactor entity."""
        pass