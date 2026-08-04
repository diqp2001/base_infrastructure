from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_factor import CompanyShareFactor


class CompanyShareFactorPort(ABC):
    """Port interface for CompanyShareFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[CompanyShareFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[CompanyShareFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareFactor) -> Optional[CompanyShareFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareFactor) -> Optional[CompanyShareFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareFactor]: ...
