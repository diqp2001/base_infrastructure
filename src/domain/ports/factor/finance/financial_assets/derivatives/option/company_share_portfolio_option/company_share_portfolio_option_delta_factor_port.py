from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_delta_factor import CompanySharePortfolioOptionDeltaFactor


class CompanySharePortfolioOptionDeltaFactorPort(ABC):
    """Port interface for CompanySharePortfolioOptionDeltaFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioOptionDeltaFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionDeltaFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioOptionDeltaFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioOptionDeltaFactor) -> Optional[CompanySharePortfolioOptionDeltaFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioOptionDeltaFactor) -> Optional[CompanySharePortfolioOptionDeltaFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioOptionDeltaFactor]: ...
