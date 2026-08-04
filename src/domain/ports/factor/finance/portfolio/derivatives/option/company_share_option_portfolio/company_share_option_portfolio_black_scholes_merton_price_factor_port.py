from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.portfolio.derivatives.option.company_share_option_portfolio.company_share_option_portfolio_black_scholes_merton_price_factor import CompanyShareOptionPortfolioBlackScholesMertonPriceFactor


class CompanyShareOptionPortfolioBlackScholesMertonPriceFactorPort(ABC):
    """Port interface for CompanyShareOptionPortfolioBlackScholesMertonPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionPortfolioBlackScholesMertonPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionPortfolioBlackScholesMertonPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionPortfolioBlackScholesMertonPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionPortfolioBlackScholesMertonPriceFactor) -> Optional[CompanyShareOptionPortfolioBlackScholesMertonPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionPortfolioBlackScholesMertonPriceFactor) -> Optional[CompanyShareOptionPortfolioBlackScholesMertonPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionPortfolioBlackScholesMertonPriceFactor]: ...
