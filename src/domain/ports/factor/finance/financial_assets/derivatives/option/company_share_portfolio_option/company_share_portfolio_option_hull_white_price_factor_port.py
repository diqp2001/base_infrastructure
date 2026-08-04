from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_hull_white_price_factor import CompanySharePortfolioOptionHullWhitePriceFactor


class CompanySharePortfolioOptionHullWhitePriceFactorPort(ABC):
    """Port interface for CompanySharePortfolioOptionHullWhitePriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioOptionHullWhitePriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionHullWhitePriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioOptionHullWhitePriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioOptionHullWhitePriceFactor) -> Optional[CompanySharePortfolioOptionHullWhitePriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioOptionHullWhitePriceFactor) -> Optional[CompanySharePortfolioOptionHullWhitePriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioOptionHullWhitePriceFactor]: ...
