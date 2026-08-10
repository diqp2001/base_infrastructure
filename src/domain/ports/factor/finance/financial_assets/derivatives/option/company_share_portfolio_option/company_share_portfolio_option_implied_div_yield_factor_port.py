from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_implied_div_yield_factor import CompanySharePortfolioOptionImpliedDivYieldFactor


class CompanySharePortfolioOptionImpliedDivYieldFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioOptionImpliedDivYieldFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionImpliedDivYieldFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioOptionImpliedDivYieldFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioOptionImpliedDivYieldFactor) -> Optional[CompanySharePortfolioOptionImpliedDivYieldFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioOptionImpliedDivYieldFactor) -> Optional[CompanySharePortfolioOptionImpliedDivYieldFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioOptionImpliedDivYieldFactor]: ...
