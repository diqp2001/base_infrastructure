from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.index_future_option_factor import IndexFutureOptionFactor


class IndexFutureOptionFactorPort(ABC):
    """Port interface for IndexFutureOptionFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[IndexFutureOptionFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[IndexFutureOptionFactor]: ...

    @abstractmethod
    def get_all(self) -> List[IndexFutureOptionFactor]: ...

    @abstractmethod
    def add(self, entity: IndexFutureOptionFactor) -> Optional[IndexFutureOptionFactor]: ...

    @abstractmethod
    def update(self, entity: IndexFutureOptionFactor) -> Optional[IndexFutureOptionFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[IndexFutureOptionFactor]: ...
