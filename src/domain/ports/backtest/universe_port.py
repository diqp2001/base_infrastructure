from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.backtest.universe import Universe


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
    def _create_or_get(self, name: str, **kwargs) -> Optional[Universe]: ...
