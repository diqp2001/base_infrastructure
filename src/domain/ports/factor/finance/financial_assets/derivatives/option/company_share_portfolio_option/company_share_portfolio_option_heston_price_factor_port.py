from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_heston_price_factor import CompanySharePortfolioOptionHestonPriceFactor


class CompanySharePortfolioOptionHestonPriceFactorPort(ABC):
    """Port interface for CompanySharePortfolioOptionHestonPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioOptionHestonPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionHestonPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioOptionHestonPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioOptionHestonPriceFactor) -> Optional[CompanySharePortfolioOptionHestonPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioOptionHestonPriceFactor) -> Optional[CompanySharePortfolioOptionHestonPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioOptionHestonPriceFactor]: ...
