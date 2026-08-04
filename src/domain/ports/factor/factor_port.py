from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.factor import Factor


class FactorPort(ABC):
    """Port interface for Factor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[Factor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Factor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[Factor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[Factor]: ...

    @abstractmethod
    def get_all(self) -> List[Factor]: ...

    @abstractmethod
    def add(self, entity: Factor) -> Optional[Factor]: ...

    @abstractmethod
    def update(self, entity: Factor) -> Optional[Factor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[Factor]: ...
