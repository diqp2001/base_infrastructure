from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.holding.company_share_portfolio_portfolio.company_share_portfolio_portfolio_holding_value_factor import CompanySharePortfolioPortfolioHoldingValueFactor


class CompanySharePortfolioPortfolioHoldingValueFactorPort(ABC):
    """Port interface for CompanySharePortfolioPortfolioHoldingValueFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioPortfolioHoldingValueFactor) -> Optional[CompanySharePortfolioPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioPortfolioHoldingValueFactor) -> Optional[CompanySharePortfolioPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioPortfolioHoldingValueFactor]: ...
