from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_vega_factor import CompanySharePortfolioOptionVegaFactor


class CompanySharePortfolioOptionVegaFactorPort(ABC):
    """Port interface for CompanySharePortfolioOptionVegaFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioOptionVegaFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionVegaFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioOptionVegaFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioOptionVegaFactor) -> Optional[CompanySharePortfolioOptionVegaFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioOptionVegaFactor) -> Optional[CompanySharePortfolioOptionVegaFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioOptionVegaFactor]: ...
