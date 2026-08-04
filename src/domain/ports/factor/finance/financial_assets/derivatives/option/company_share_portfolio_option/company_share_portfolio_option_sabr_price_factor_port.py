from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_sabr_price_factor import CompanySharePortfolioOptionSABRPriceFactor


class CompanySharePortfolioOptionSABRPriceFactorPort(ABC):
    """Port interface for CompanySharePortfolioOptionSABRPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioOptionSABRPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionSABRPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioOptionSABRPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioOptionSABRPriceFactor) -> Optional[CompanySharePortfolioOptionSABRPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioOptionSABRPriceFactor) -> Optional[CompanySharePortfolioOptionSABRPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioOptionSABRPriceFactor]: ...
