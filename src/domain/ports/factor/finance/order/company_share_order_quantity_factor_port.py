from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.order.company_share_order_quantity_factor import CompanyShareOrderQuantityFactor


class CompanyShareOrderQuantityFactorPort(ABC):
    """Port interface for CompanyShareOrderQuantityFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOrderQuantityFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOrderQuantityFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOrderQuantityFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOrderQuantityFactor) -> Optional[CompanyShareOrderQuantityFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOrderQuantityFactor) -> Optional[CompanyShareOrderQuantityFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOrderQuantityFactor]: ...
