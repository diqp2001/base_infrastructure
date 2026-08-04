from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_bates_price_factor import CompanySharePortfolioOptionBatesPriceFactor


class CompanySharePortfolioOptionBatesPriceFactorPort(ABC):
    """Port interface for CompanySharePortfolioOptionBatesPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioOptionBatesPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionBatesPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioOptionBatesPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioOptionBatesPriceFactor) -> Optional[CompanySharePortfolioOptionBatesPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioOptionBatesPriceFactor) -> Optional[CompanySharePortfolioOptionBatesPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioOptionBatesPriceFactor]: ...
