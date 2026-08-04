from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_portfolio_option.company_share_portfolio_option_gamma_factor import CompanySharePortfolioOptionGammaFactor


class CompanySharePortfolioOptionGammaFactorPort(ABC):
    """Port interface for CompanySharePortfolioOptionGammaFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePortfolioOptionGammaFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePortfolioOptionGammaFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePortfolioOptionGammaFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePortfolioOptionGammaFactor) -> Optional[CompanySharePortfolioOptionGammaFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePortfolioOptionGammaFactor) -> Optional[CompanySharePortfolioOptionGammaFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePortfolioOptionGammaFactor]: ...
