from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_theta_factor import CompanySharePortfolioOptionThetaFactor


class CompanySharePortfolioOptionThetaFactorPort(ABC):
    """Port interface for CompanySharePortfolioOptionThetaFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioOptionThetaFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionThetaFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioOptionThetaFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioOptionThetaFactor) -> Optional[CompanySharePortfolioOptionThetaFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioOptionThetaFactor) -> Optional[CompanySharePortfolioOptionThetaFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioOptionThetaFactor]: ...
