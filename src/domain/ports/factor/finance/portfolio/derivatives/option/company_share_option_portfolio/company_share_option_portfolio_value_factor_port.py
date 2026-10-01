from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.portfolio.derivatives.option.company_share_option_portfolio.company_share_option_portfolio_value_factor import CompanyShareOptionPortfolioValueFactor


class CompanyShareOptionPortfolioValueFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionPortfolioValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionPortfolioValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionPortfolioValueFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionPortfolioValueFactor) -> Optional[CompanyShareOptionPortfolioValueFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionPortfolioValueFactor) -> Optional[CompanyShareOptionPortfolioValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionPortfolioValueFactor]: ...
