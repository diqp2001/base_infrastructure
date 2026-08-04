from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_discounted_value_factor import FutureDiscountedValueFactor


class FutureDiscountedValueFactorPort(ABC):
    """Port interface for FutureDiscountedValueFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[FutureDiscountedValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[FutureDiscountedValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[FutureDiscountedValueFactor]: ...

    @abstractmethod
    def add(self, entity: FutureDiscountedValueFactor) -> Optional[FutureDiscountedValueFactor]: ...

    @abstractmethod
    def update(self, entity: FutureDiscountedValueFactor) -> Optional[FutureDiscountedValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[FutureDiscountedValueFactor]: ...
