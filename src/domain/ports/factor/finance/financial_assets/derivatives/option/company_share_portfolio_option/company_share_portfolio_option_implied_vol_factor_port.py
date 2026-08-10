from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_implied_vol_factor import CompanySharePortfolioOptionImpliedVolFactor


class CompanySharePortfolioOptionImpliedVolFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioOptionImpliedVolFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionImpliedVolFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioOptionImpliedVolFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioOptionImpliedVolFactor) -> Optional[CompanySharePortfolioOptionImpliedVolFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioOptionImpliedVolFactor) -> Optional[CompanySharePortfolioOptionImpliedVolFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioOptionImpliedVolFactor]: ...
