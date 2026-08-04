from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_factor import CompanySharePortfolioOptionFactor


class CompanySharePortfolioOptionFactorPort(ABC):
    """Port interface for CompanySharePortfolioOptionFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioOptionFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[CompanySharePortfolioOptionFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioOptionFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioOptionFactor) -> Optional[CompanySharePortfolioOptionFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioOptionFactor) -> Optional[CompanySharePortfolioOptionFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioOptionFactor]: ...
