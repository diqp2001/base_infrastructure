from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.holding.company_share_option_portfolio.company_share_option_portfolio_holding_value_factor import CompanyShareOptionPortfolioHoldingValueFactor


class CompanyShareOptionPortfolioHoldingValueFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionPortfolioHoldingValueFactor) -> Optional[CompanyShareOptionPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionPortfolioHoldingValueFactor) -> Optional[CompanyShareOptionPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionPortfolioHoldingValueFactor]: ...
