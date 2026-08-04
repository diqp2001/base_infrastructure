from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.position.company_share_position_value_factor import CompanySharePositionValueFactor


class CompanySharePositionValueFactorPort(ABC):
    """Port interface for CompanySharePositionValueFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanySharePositionValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanySharePositionValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanySharePositionValueFactor]: ...

    @abstractmethod
    def add(self, entity: CompanySharePositionValueFactor) -> Optional[CompanySharePositionValueFactor]: ...

    @abstractmethod
    def update(self, entity: CompanySharePositionValueFactor) -> Optional[CompanySharePositionValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanySharePositionValueFactor]: ...
