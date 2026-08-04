from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.holding.company_share_portfolio.company_share_portfolio_holding_weight_factor import CompanySharePortfolioHoldingWeightFactor


class CompanySharePortfolioHoldingWeightFactorPort(ABC):
    """Port interface for CompanySharePortfolioHoldingWeightFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioHoldingWeightFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioHoldingWeightFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioHoldingWeightFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioHoldingWeightFactor) -> Optional[CompanySharePortfolioHoldingWeightFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioHoldingWeightFactor) -> Optional[CompanySharePortfolioHoldingWeightFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioHoldingWeightFactor]: ...
