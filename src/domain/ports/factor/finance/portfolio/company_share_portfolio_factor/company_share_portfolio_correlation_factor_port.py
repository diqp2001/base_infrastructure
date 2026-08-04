from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_correlation_factor import CompanySharePortfolioCorrelationFactor


class CompanySharePortfolioCorrelationFactorPort(ABC):
    """Port interface for CompanySharePortfolioCorrelationFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioCorrelationFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioCorrelationFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioCorrelationFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioCorrelationFactor) -> Optional[CompanySharePortfolioCorrelationFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioCorrelationFactor) -> Optional[CompanySharePortfolioCorrelationFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioCorrelationFactor]: ...
