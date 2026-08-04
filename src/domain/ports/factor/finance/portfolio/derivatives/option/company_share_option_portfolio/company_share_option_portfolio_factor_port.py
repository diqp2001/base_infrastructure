from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.portfolio.derivatives.option.company_share_option_portfolio.company_share_option_portfolio_factor import CompanyShareOptionPortfolioFactor


class CompanyShareOptionPortfolioFactorPort(ABC):
    """Port interface for CompanyShareOptionPortfolioFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionPortfolioFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionPortfolioFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[CompanyShareOptionPortfolioFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionPortfolioFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionPortfolioFactor) -> Optional[CompanyShareOptionPortfolioFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionPortfolioFactor) -> Optional[CompanyShareOptionPortfolioFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionPortfolioFactor]: ...
