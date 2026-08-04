from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.portfolio.portfolio_value_factor import PortfolioValueFactor


class PortfolioValueFactorPort(ABC):
    """Port interface for PortfolioValueFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[PortfolioValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[PortfolioValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[PortfolioValueFactor]: ...

    @abstractmethod
    def add(self, entity: PortfolioValueFactor) -> Optional[PortfolioValueFactor]: ...

    @abstractmethod
    def update(self, entity: PortfolioValueFactor) -> Optional[PortfolioValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[PortfolioValueFactor]: ...
