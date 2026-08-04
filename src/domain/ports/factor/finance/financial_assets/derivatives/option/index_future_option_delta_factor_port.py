from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.index_future_option_delta_factor import IndexFutureOptionDeltaFactor


class IndexFutureOptionDeltaFactorPort(ABC):
    """Port interface for IndexFutureOptionDeltaFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[IndexFutureOptionDeltaFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[IndexFutureOptionDeltaFactor]: ...

    @abstractmethod
    def get_all(self) -> List[IndexFutureOptionDeltaFactor]: ...

    @abstractmethod
    def add(self, entity: IndexFutureOptionDeltaFactor) -> Optional[IndexFutureOptionDeltaFactor]: ...

    @abstractmethod
    def update(self, entity: IndexFutureOptionDeltaFactor) -> Optional[IndexFutureOptionDeltaFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[IndexFutureOptionDeltaFactor]: ...
