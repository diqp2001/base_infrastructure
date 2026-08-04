from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_price_return_factor import CompanySharePortfolioPriceReturnFactor


class CompanySharePortfolioPriceReturnFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioPriceReturnFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioPriceReturnFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[CompanySharePortfolioPriceReturnFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioPriceReturnFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioPriceReturnFactor) -> Optional[CompanySharePortfolioPriceReturnFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioPriceReturnFactor) -> Optional[CompanySharePortfolioPriceReturnFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioPriceReturnFactor]: ...
