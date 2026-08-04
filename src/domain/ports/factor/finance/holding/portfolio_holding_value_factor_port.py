from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.holding.portfolio_holding_value_factor import PortfolioHoldingValueFactor


class PortfolioHoldingValueFactorPort(ABC):
    """Port interface for PortfolioHoldingValueFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[PortfolioHoldingValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[PortfolioHoldingValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[PortfolioHoldingValueFactor]: ...

    @abstractmethod
    def add(self, entity: PortfolioHoldingValueFactor) -> Optional[PortfolioHoldingValueFactor]: ...

    @abstractmethod
    def update(self, entity: PortfolioHoldingValueFactor) -> Optional[PortfolioHoldingValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[PortfolioHoldingValueFactor]: ...
