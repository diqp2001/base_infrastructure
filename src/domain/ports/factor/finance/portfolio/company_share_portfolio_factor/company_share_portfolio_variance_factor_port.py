from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_variance_factor import CompanySharePortfolioVarianceFactor


class CompanySharePortfolioVarianceFactorPort(ABC):
    """Port interface for CompanySharePortfolioVarianceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioVarianceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioVarianceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioVarianceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioVarianceFactor) -> Optional[CompanySharePortfolioVarianceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioVarianceFactor) -> Optional[CompanySharePortfolioVarianceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioVarianceFactor]: ...
