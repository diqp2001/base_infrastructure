"""
Portfolio Value Factor Port

Port interface for portfolio value factor repository operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.factor.finance.portfolio.portfolio_value_factor import PortfolioValueFactor


class PortfolioValueFactorPort(ABC):
    """Port interface for portfolio value factor repository operations."""

    # @abstractmethod
    # def get_by_id(self, factor_id: int) -> Optional[PortfolioValueFactor]:
    #     """Get portfolio value factor by ID."""
    #     pass

    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[PortfolioValueFactor]:
    #     """Get portfolio value factor by name."""
    #     pass

    # @abstractmethod
    # def get_by_group(self, group: str) -> List[PortfolioValueFactor]:
    #     """Get portfolio value factors by group."""
    #     pass

    # @abstractmethod
    # def get_by_subgroup(self, subgroup: str) -> List[PortfolioValueFactor]:
    #     """Get portfolio value factors by subgroup."""
    #     pass

    # @abstractmethod
    # def get_all(self) -> List[PortfolioValueFactor]:
    #     """Get all portfolio value factors."""
    #     pass

    # @abstractmethod
    # def add(self, entity: PortfolioValueFactor) -> Optional[PortfolioValueFactor]:
    #     """Add portfolio value factor entity."""
    #     pass

    # @abstractmethod
    # def update(self, entity: PortfolioValueFactor) -> Optional[PortfolioValueFactor]:
    #     """Update portfolio value factor entity."""
    #     pass

    # @abstractmethod
    # def delete(self, factor_id: int) -> bool:
    #     """Delete portfolio value factor entity."""
    #     pass