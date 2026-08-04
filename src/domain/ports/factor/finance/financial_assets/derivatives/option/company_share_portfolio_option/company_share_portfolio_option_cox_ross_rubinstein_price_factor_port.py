from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_cox_ross_rubinstein_price_factor import CompanySharePortfolioOptionCoxRossRubinsteinPriceFactor


class CompanySharePortfolioOptionCoxRossRubinsteinPriceFactorPort(ABC):
    """Port interface for CompanySharePortfolioOptionCoxRossRubinsteinPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioOptionCoxRossRubinsteinPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionCoxRossRubinsteinPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioOptionCoxRossRubinsteinPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioOptionCoxRossRubinsteinPriceFactor) -> Optional[CompanySharePortfolioOptionCoxRossRubinsteinPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioOptionCoxRossRubinsteinPriceFactor) -> Optional[CompanySharePortfolioOptionCoxRossRubinsteinPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioOptionCoxRossRubinsteinPriceFactor]: ...
