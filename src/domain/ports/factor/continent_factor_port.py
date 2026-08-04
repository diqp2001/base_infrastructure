from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.continent_factor import ContinentFactor


class ContinentFactorPort(ABC):
    """Port interface for ContinentFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[ContinentFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[ContinentFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[ContinentFactor]: ...

    @abstractmethod
    def get_all(self) -> List[ContinentFactor]: ...

    @abstractmethod
    def add(self, entity: ContinentFactor) -> Optional[ContinentFactor]: ...

    @abstractmethod
    def update(self, entity: ContinentFactor) -> Optional[ContinentFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ContinentFactor]: ...
