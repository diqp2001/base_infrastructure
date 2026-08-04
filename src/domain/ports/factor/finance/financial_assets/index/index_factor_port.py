from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.index.index_factor import IndexFactor


class IndexFactorPort(ABC):
    """Port interface for IndexFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[IndexFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[IndexFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[IndexFactor]: ...

    @abstractmethod
    def get_all(self) -> List[IndexFactor]: ...

    @abstractmethod
    def add(self, entity: IndexFactor) -> Optional[IndexFactor]: ...

    @abstractmethod
    def update(self, entity: IndexFactor) -> Optional[IndexFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[IndexFactor]: ...
