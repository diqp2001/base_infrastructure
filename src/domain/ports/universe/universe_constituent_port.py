"""
src/domain/ports/universe/universe_constituent_port.py

Abstract port for UniverseConstituent repository.
"""

from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, List
from src.domain.entities.universe.universe_constituent import UniverseConstituent


class UniverseConstituentPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[UniverseConstituent]: ...

    @abstractmethod
    def get_by_universe(self, universe_id: int) -> List[UniverseConstituent]: ...

    @abstractmethod
    def get_active_by_universe(self, universe_id: int, as_of: date) -> List[UniverseConstituent]: ...

    @abstractmethod
    def get_by_entity(self, entity_id: int, entity_type: str) -> List[UniverseConstituent]: ...

    @abstractmethod
    def get_all(self) -> List[UniverseConstituent]: ...

    @abstractmethod
    def add(self, entity: UniverseConstituent) -> Optional[UniverseConstituent]: ...

    @abstractmethod
    def update(self, entity: UniverseConstituent) -> Optional[UniverseConstituent]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[UniverseConstituent]: ...
