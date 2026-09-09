"""
src/domain/ports/universe/universe_port.py

Abstract port for Universe repository.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.universe.universe import Universe


class UniversePort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[Universe]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Universe]: ...

    @abstractmethod
    def get_all(self) -> List[Universe]: ...

    @abstractmethod
    def add(self, entity: Universe) -> Optional[Universe]: ...

    @abstractmethod
    def update(self, entity: Universe) -> Optional[Universe]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[Universe]: ...
