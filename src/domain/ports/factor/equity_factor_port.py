"""
Equity Factor Port - Domain interface for EquityFactor repository operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.factor.finance.financial_assets.equity_factor import EquityFactor


class EquityFactorPort(ABC):
    """Abstract interface for EquityFactor repository operations."""

    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[EquityFactor]:
    #     """Get EquityFactor by ID."""
    #     pass

    # @abstractmethod  
    # def get_by_name(self, name: str) -> Optional[EquityFactor]:
    #     """Get EquityFactor by name."""
    #     pass

    # @abstractmethod
    # def get_by_group(self, group: str) -> List[EquityFactor]:
    #     """Get EquityFactor entities by group."""
    #     pass

    # @abstractmethod
    # def get_by_subgroup(self, subgroup: str) -> List[EquityFactor]:
    #     """Get EquityFactor entities by subgroup."""
    #     pass

    # @abstractmethod
    # def get_all(self) -> List[EquityFactor]:
    #     """Get all EquityFactor entities."""
    #     pass

    # @abstractmethod
    # def add(self, entity: EquityFactor) -> Optional[EquityFactor]:
    #     """Add EquityFactor entity."""
    #     pass

    # @abstractmethod
    # def update(self, entity_id: int, **kwargs) -> Optional[EquityFactor]:
    #     """Update EquityFactor entity."""
    #     pass

    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """Delete EquityFactor entity."""
    #     pass