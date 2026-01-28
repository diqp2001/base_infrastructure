"""
Currency Factor Port - Domain interface for CurrencyFactor repository operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.factor.finance.financial_assets.currency_factor import CurrencyFactor


class CurrencyFactorPort(ABC):
    """Abstract interface for CurrencyFactor repository operations."""

    # @abstractmethod
    # def get_by_id(self, entity_id: int) -> Optional[CurrencyFactor]:
    #     """Get CurrencyFactor by ID."""
    #     pass

    # @abstractmethod  
    # def get_by_name(self, name: str) -> Optional[CurrencyFactor]:
    #     """Get CurrencyFactor by name."""
    #     pass

    # @abstractmethod
    # def get_by_group(self, group: str) -> List[CurrencyFactor]:
    #     """Get CurrencyFactor entities by group."""
    #     pass

    # @abstractmethod
    # def get_by_subgroup(self, subgroup: str) -> List[CurrencyFactor]:
    #     """Get CurrencyFactor entities by subgroup."""
    #     pass

    # @abstractmethod
    # def get_all(self) -> List[CurrencyFactor]:
    #     """Get all CurrencyFactor entities."""
    #     pass

    # @abstractmethod
    # def add(self, entity: CurrencyFactor) -> Optional[CurrencyFactor]:
    #     """Add CurrencyFactor entity."""
    #     pass

    # @abstractmethod
    # def update(self, entity_id: int, **kwargs) -> Optional[CurrencyFactor]:
    #     """Update CurrencyFactor entity."""
    #     pass

    # @abstractmethod
    # def delete(self, entity_id: int) -> bool:
    #     """Delete CurrencyFactor entity."""
    #     pass