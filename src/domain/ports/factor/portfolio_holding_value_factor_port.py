"""
Portfolio Holding Value Factor Port

Port interface for portfolio holding value factor repository operations.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.factor.finance.holding.portfolio_holding_value_factor import PortfolioHoldingValueFactor


class PortfolioHoldingValueFactorPort(ABC):
    """Port interface for portfolio holding value factor repository operations."""

    # @abstractmethod
    # def get_by_id(self, factor_id: int) -> Optional[PortfolioHoldingValueFactor]:
    #     """Get portfolio holding value factor by ID."""
    #     pass

    # @abstractmethod
    # def get_by_name(self, name: str) -> Optional[PortfolioHoldingValueFactor]:
    #     """Get portfolio holding value factor by name."""
    #     pass

    # @abstractmethod
    # def get_by_group(self, group: str) -> List[PortfolioHoldingValueFactor]:
    #     """Get portfolio holding value factors by group."""
    #     pass

    # @abstractmethod
    # def get_by_subgroup(self, subgroup: str) -> List[PortfolioHoldingValueFactor]:
    #     """Get portfolio holding value factors by subgroup."""
    #     pass

    # @abstractmethod
    # def get_all(self) -> List[PortfolioHoldingValueFactor]:
    #     """Get all portfolio holding value factors."""
    #     pass

    # @abstractmethod
    # def add(self, entity: PortfolioHoldingValueFactor) -> Optional[PortfolioHoldingValueFactor]:
    #     """Add portfolio holding value factor entity."""
    #     pass

    # @abstractmethod
    # def update(self, entity: PortfolioHoldingValueFactor) -> Optional[PortfolioHoldingValueFactor]:
    #     """Update portfolio holding value factor entity."""
    #     pass

    # @abstractmethod
    # def delete(self, factor_id: int) -> bool:
    #     """Delete portfolio holding value factor entity."""
    #     pass