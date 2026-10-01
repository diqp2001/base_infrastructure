from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.holding.company_share_option_portfolio_portfolio.company_share_option_portfolio_portfolio_holding_value_factor import CompanyShareOptionPortfolioPortfolioHoldingValueFactor


class CompanyShareOptionPortfolioPortfolioHoldingValueFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionPortfolioPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionPortfolioPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionPortfolioPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionPortfolioPortfolioHoldingValueFactor) -> Optional[CompanyShareOptionPortfolioPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionPortfolioPortfolioHoldingValueFactor) -> Optional[CompanyShareOptionPortfolioPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionPortfolioPortfolioHoldingValueFactor]: ...
