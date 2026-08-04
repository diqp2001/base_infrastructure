from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.portfolio.derivatives.option.company_share_option_portfolio.company_share_option_portfolio_delta_factor import CompanyShareOptionPortfolioDeltaFactor


class CompanyShareOptionPortfolioDeltaFactorPort(ABC):
    """Port interface for CompanyShareOptionPortfolioDeltaFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionPortfolioDeltaFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionPortfolioDeltaFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionPortfolioDeltaFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionPortfolioDeltaFactor) -> Optional[CompanyShareOptionPortfolioDeltaFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionPortfolioDeltaFactor) -> Optional[CompanyShareOptionPortfolioDeltaFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionPortfolioDeltaFactor]: ...
