from abc import ABC, abstractmethod
from typing import Optional, List

from src.domain.entities.factor.finance.portfolio.company_share_portfolio_factor.company_share_portfolio_equal_weight_return_factor import CompanySharePortfolioEqualWeightReturnFactor


class CompanySharePortfolioEqualWeightReturnFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioEqualWeightReturnFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioEqualWeightReturnFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[CompanySharePortfolioEqualWeightReturnFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioEqualWeightReturnFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioEqualWeightReturnFactor) -> Optional[CompanySharePortfolioEqualWeightReturnFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioEqualWeightReturnFactor) -> Optional[CompanySharePortfolioEqualWeightReturnFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioEqualWeightReturnFactor]: ...
