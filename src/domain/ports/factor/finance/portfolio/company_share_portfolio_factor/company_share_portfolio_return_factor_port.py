from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_return_factor import CompanySharePortfolioReturnFactor


class CompanySharePortfolioReturnFactorPort(ABC):
    """Port interface for CompanySharePortfolioReturnFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioReturnFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioReturnFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[CompanySharePortfolioReturnFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioReturnFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioReturnFactor) -> Optional[CompanySharePortfolioReturnFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioReturnFactor) -> Optional[CompanySharePortfolioReturnFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioReturnFactor]: ...
