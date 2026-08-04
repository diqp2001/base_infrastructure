from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.holding.currency_portfolio_portfolio.currency_portfolio_portfolio_holding_value_factor import CurrencyPortfolioPortfolioHoldingValueFactor


class CurrencyPortfolioPortfolioHoldingValueFactorPort(ABC):
    """Port interface for CurrencyPortfolioPortfolioHoldingValueFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CurrencyPortfolioPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CurrencyPortfolioPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CurrencyPortfolioPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def add(self, entity: CurrencyPortfolioPortfolioHoldingValueFactor) -> Optional[CurrencyPortfolioPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def update(self, entity: CurrencyPortfolioPortfolioHoldingValueFactor) -> Optional[CurrencyPortfolioPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CurrencyPortfolioPortfolioHoldingValueFactor]: ...
