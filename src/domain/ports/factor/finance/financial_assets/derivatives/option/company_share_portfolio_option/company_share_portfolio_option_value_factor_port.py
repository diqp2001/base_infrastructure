from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_value_factor import CompanySharePortfolioOptionValueFactor


class CompanySharePortfolioOptionValueFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioOptionValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioOptionValueFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioOptionValueFactor) -> Optional[CompanySharePortfolioOptionValueFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioOptionValueFactor) -> Optional[CompanySharePortfolioOptionValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioOptionValueFactor]: ...
