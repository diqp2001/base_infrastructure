from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.portfolio.currency_portfolio_value_factor import CurrencyPortfolioValueFactor


class CurrencyPortfolioValueFactorPort(ABC):
    """Port interface for CurrencyPortfolioValueFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CurrencyPortfolioValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CurrencyPortfolioValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CurrencyPortfolioValueFactor]: ...

    @abstractmethod
    def add(self, entity: CurrencyPortfolioValueFactor) -> Optional[CurrencyPortfolioValueFactor]: ...

    @abstractmethod
    def update(self, entity: CurrencyPortfolioValueFactor) -> Optional[CurrencyPortfolioValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CurrencyPortfolioValueFactor]: ...
