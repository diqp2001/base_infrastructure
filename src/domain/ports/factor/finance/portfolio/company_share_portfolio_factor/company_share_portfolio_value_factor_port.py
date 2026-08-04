from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_value_factor import CompanySharePortfolioValueFactor


class CompanySharePortfolioValueFactorPort(ABC):
    """Port interface for CompanySharePortfolioValueFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioValueFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioValueFactor) -> Optional[CompanySharePortfolioValueFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioValueFactor) -> Optional[CompanySharePortfolioValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioValueFactor]: ...
