from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.future.bond_future.bond_future_discounted_value_factor import BondFutureDiscountedValueFactor


class BondFutureDiscountedValueFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[BondFutureDiscountedValueFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[BondFutureDiscountedValueFactor]: ...

    @abstractmethod
    def get_all(self) -> List[BondFutureDiscountedValueFactor]: ...

    @abstractmethod
    def add(self, entity: BondFutureDiscountedValueFactor) -> Optional[BondFutureDiscountedValueFactor]: ...

    @abstractmethod
    def update(self, entity: BondFutureDiscountedValueFactor) -> Optional[BondFutureDiscountedValueFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[BondFutureDiscountedValueFactor]: ...
