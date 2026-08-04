from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.portfolio.portfolio_factor import PortfolioFactor


class PortfolioFactorPort(ABC):
    """Port interface for PortfolioFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[PortfolioFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[PortfolioFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[PortfolioFactor]: ...

    @abstractmethod
    def get_all(self) -> List[PortfolioFactor]: ...

    @abstractmethod
    def add(self, entity: PortfolioFactor) -> Optional[PortfolioFactor]: ...

    @abstractmethod
    def update(self, entity: PortfolioFactor) -> Optional[PortfolioFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[PortfolioFactor]: ...
