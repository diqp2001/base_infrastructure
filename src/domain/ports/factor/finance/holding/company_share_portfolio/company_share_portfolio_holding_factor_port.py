from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.holding.company_share_portfolio.company_share_portfolio_holding_factor import CompanySharePortfolioHoldingFactor


class CompanySharePortfolioHoldingFactorPort(ABC):
    """Port interface for CompanySharePortfolioHoldingFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioHoldingFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioHoldingFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[CompanySharePortfolioHoldingFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioHoldingFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioHoldingFactor) -> Optional[CompanySharePortfolioHoldingFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioHoldingFactor) -> Optional[CompanySharePortfolioHoldingFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioHoldingFactor]: ...
