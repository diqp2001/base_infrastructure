from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_price_return_factor import CompanySharePortfolioOptionPriceReturnFactor


class CompanySharePortfolioOptionPriceReturnFactorPort(ABC):
    """Port interface for CompanySharePortfolioOptionPriceReturnFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioOptionPriceReturnFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionPriceReturnFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[CompanySharePortfolioOptionPriceReturnFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioOptionPriceReturnFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioOptionPriceReturnFactor) -> Optional[CompanySharePortfolioOptionPriceReturnFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioOptionPriceReturnFactor) -> Optional[CompanySharePortfolioOptionPriceReturnFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioOptionPriceReturnFactor]: ...
