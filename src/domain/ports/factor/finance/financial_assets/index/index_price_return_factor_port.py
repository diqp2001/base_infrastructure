from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.index.index_price_return_factor import IndexPriceReturnFactor


class IndexPriceReturnFactorPort(ABC):
    """Port interface for IndexPriceReturnFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[IndexPriceReturnFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[IndexPriceReturnFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[IndexPriceReturnFactor]: ...

    @abstractmethod
    def get_all(self) -> List[IndexPriceReturnFactor]: ...

    @abstractmethod
    def add(self, entity: IndexPriceReturnFactor) -> Optional[IndexPriceReturnFactor]: ...

    @abstractmethod
    def update(self, entity: IndexPriceReturnFactor) -> Optional[IndexPriceReturnFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[IndexPriceReturnFactor]: ...
