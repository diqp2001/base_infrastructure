from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.future.index_future_price_return_factor import IndexFuturePriceReturnFactor


class IndexFuturePriceReturnFactorPort(ABC):
    """Port interface for IndexFuturePriceReturnFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[IndexFuturePriceReturnFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[IndexFuturePriceReturnFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[IndexFuturePriceReturnFactor]: ...

    @abstractmethod
    def get_all(self) -> List[IndexFuturePriceReturnFactor]: ...

    @abstractmethod
    def add(self, entity: IndexFuturePriceReturnFactor) -> Optional[IndexFuturePriceReturnFactor]: ...

    @abstractmethod
    def update(self, entity: IndexFuturePriceReturnFactor) -> Optional[IndexFuturePriceReturnFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[IndexFuturePriceReturnFactor]: ...
