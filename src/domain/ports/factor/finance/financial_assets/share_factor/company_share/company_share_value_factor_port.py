from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_value_factor import CompanyShareValueFactor


class CompanyShareValueFactorPort(ABC):
    """Port interface for CompanyShareValueFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareValueFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareValueFactor) -> Optional[CompanyShareValueFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareValueFactor) -> Optional[CompanyShareValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareValueFactor]: ...
