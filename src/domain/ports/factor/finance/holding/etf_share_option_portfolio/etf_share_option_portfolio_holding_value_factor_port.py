from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.factor.finance.holding.etf_share_option_portfolio.etf_share_option_portfolio_holding_value_factor import ETFShareOptionPortfolioHoldingValueFactor


class ETFShareOptionPortfolioHoldingValueFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[ETFShareOptionPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[ETFShareOptionPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[ETFShareOptionPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def add(self, entity: ETFShareOptionPortfolioHoldingValueFactor) -> Optional[ETFShareOptionPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def update(self, entity: ETFShareOptionPortfolioHoldingValueFactor) -> Optional[ETFShareOptionPortfolioHoldingValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ETFShareOptionPortfolioHoldingValueFactor]: ...
