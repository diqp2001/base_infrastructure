from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_factor import CompanySharePortfolioFactor


class CompanySharePortfolioFactorPort(ABC):
    """Port interface for CompanySharePortfolioFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[CompanySharePortfolioFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioFactor) -> Optional[CompanySharePortfolioFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioFactor) -> Optional[CompanySharePortfolioFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioFactor]: ...
