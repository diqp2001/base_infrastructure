from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.company_share_option.company_share_option_factor import CompanyShareOptionFactor


class CompanyShareOptionFactorPort(ABC):
    """Port interface for CompanyShareOptionFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOptionFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOptionFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[CompanyShareOptionFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOptionFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOptionFactor) -> Optional[CompanyShareOptionFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOptionFactor) -> Optional[CompanyShareOptionFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOptionFactor]: ...
