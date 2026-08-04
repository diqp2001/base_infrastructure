from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.holding.currency_portfolio_holding_value_factor import CurrencyPortfolioHoldingValueFactor


class CurrencyPortfolioHoldingValueFactorPort(ABC):
    """Port interface for CurrencyPortfolioHoldingValueFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CurrencyPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CurrencyPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CurrencyPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def add(self, entity: CurrencyPortfolioHoldingValueFactor) -> Optional[CurrencyPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def update(self, entity: CurrencyPortfolioHoldingValueFactor) -> Optional[CurrencyPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CurrencyPortfolioHoldingValueFactor]: ...
