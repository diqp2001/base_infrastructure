from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.future.future_price_return_factor import FuturePriceReturnFactor


class FuturePriceReturnFactorPort(ABC):
    """Port interface for FuturePriceReturnFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[FuturePriceReturnFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[FuturePriceReturnFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[FuturePriceReturnFactor]: ...

    @abstractmethod
    def get_all(self) -> List[FuturePriceReturnFactor]: ...

    @abstractmethod
    def add(self, entity: FuturePriceReturnFactor) -> Optional[FuturePriceReturnFactor]: ...

    @abstractmethod
    def update(self, entity: FuturePriceReturnFactor) -> Optional[FuturePriceReturnFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[FuturePriceReturnFactor]: ...
