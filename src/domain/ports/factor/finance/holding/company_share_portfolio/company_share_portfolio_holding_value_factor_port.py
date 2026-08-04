from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.holding.company_share_portfolio.company_share_portfolio_holding_value_factor import CompanySharePortfolioHoldingValueFactor


class CompanySharePortfolioHoldingValueFactorPort(ABC):
    """Port interface for CompanySharePortfolioHoldingValueFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioHoldingValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioHoldingValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioHoldingValueFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioHoldingValueFactor) -> Optional[CompanySharePortfolioHoldingValueFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioHoldingValueFactor) -> Optional[CompanySharePortfolioHoldingValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioHoldingValueFactor]: ...
