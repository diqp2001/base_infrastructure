from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.order.company_share_order_price_factor import CompanyShareOrderPriceFactor


class CompanyShareOrderPriceFactorPort(ABC):
    """Port interface for CompanyShareOrderPriceFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CompanyShareOrderPriceFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CompanyShareOrderPriceFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CompanyShareOrderPriceFactor]: ...

    @abstractmethod
    def add(self, entity: CompanyShareOrderPriceFactor) -> Optional[CompanyShareOrderPriceFactor]: ...

    @abstractmethod
    def update(self, entity: CompanyShareOrderPriceFactor) -> Optional[CompanyShareOrderPriceFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CompanyShareOrderPriceFactor]: ...
