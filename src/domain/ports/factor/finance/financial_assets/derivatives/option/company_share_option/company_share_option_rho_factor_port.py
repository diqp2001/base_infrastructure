from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_rho_factor import CompanyShareOptionRhoFactor


class CompanyShareOptionRhoFactorPort(ABC):
    """Port interface for CompanyShareOptionRhoFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionRhoFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionRhoFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionRhoFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionRhoFactor) -> Optional[CompanyShareOptionRhoFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionRhoFactor) -> Optional[CompanyShareOptionRhoFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionRhoFactor]: ...
