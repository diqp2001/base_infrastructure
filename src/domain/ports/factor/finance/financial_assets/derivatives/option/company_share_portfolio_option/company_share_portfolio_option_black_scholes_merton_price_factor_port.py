from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_black_scholes_merton_price_factor import CompanySharePortfolioOptionBlackScholesMertonPriceFactor


class CompanySharePortfolioOptionBlackScholesMertonPriceFactorPort(ABC):
    """Port interface for CompanySharePortfolioOptionBlackScholesMertonPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioOptionBlackScholesMertonPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionBlackScholesMertonPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioOptionBlackScholesMertonPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioOptionBlackScholesMertonPriceFactor) -> Optional[CompanySharePortfolioOptionBlackScholesMertonPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioOptionBlackScholesMertonPriceFactor) -> Optional[CompanySharePortfolioOptionBlackScholesMertonPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioOptionBlackScholesMertonPriceFactor]: ...
