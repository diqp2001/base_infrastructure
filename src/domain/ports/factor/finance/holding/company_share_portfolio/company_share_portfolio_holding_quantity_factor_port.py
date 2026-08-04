from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.holding.company_share_portfolio.company_share_portfolio_holding_quantity_factor import CompanySharePortfolioHoldingQuantityFactor


class CompanySharePortfolioHoldingQuantityFactorPort(ABC):
    """Port interface for CompanySharePortfolioHoldingQuantityFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioHoldingQuantityFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioHoldingQuantityFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioHoldingQuantityFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioHoldingQuantityFactor) -> Optional[CompanySharePortfolioHoldingQuantityFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioHoldingQuantityFactor) -> Optional[CompanySharePortfolioHoldingQuantityFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioHoldingQuantityFactor]: ...
