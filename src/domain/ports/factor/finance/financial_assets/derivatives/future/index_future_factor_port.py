from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.future.index_future_factor import IndexFutureFactor


class IndexFutureFactorPort(ABC):
    """Port interface for IndexFutureFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[IndexFutureFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[IndexFutureFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[IndexFutureFactor]: ...

    @abstractmethod
    def get_all(self) -> List[IndexFutureFactor]: ...

    @abstractmethod
    def add(self, entity: IndexFutureFactor) -> Optional[IndexFutureFactor]: ...

    @abstractmethod
    def update(self, entity: IndexFutureFactor) -> Optional[IndexFutureFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[IndexFutureFactor]: ...
