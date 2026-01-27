"""
Share Factor Port - Domain interface for ShareFactor repository operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor


class ShareFactorPort(ABC):
    """Abstract interface for ShareFactor repository operations."""

    @abstractmethod
    def get_by_id(self, entity_id: int) -> Optional[ShareFactor]:
        """Get ShareFactor by ID."""
        pass

    @abstractmethod  
    def get_by_name(self, name: str) -> Optional[ShareFactor]:
        """Get ShareFactor by name."""
        pass

    @abstractmethod
    def get_by_group(self, group: str) -> List[ShareFactor]:
        """Get ShareFactor entities by group."""
        pass

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[ShareFactor]:
        """Get ShareFactor entities by subgroup."""
        pass

    @abstractmethod
    def get_all(self) -> List[ShareFactor]:
        """Get all ShareFactor entities."""
        pass

    @abstractmethod
    def add(self, entity: ShareFactor) -> Optional[ShareFactor]:
        """Add ShareFactor entity."""
        pass

    @abstractmethod
    def update(self, entity_id: int, **kwargs) -> Optional[ShareFactor]:
        """Update ShareFactor entity."""
        pass

    @abstractmethod
    def delete(self, entity_id: int) -> bool:
        """Delete ShareFactor entity."""
        pass