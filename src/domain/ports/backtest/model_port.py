from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.backtest.model import Model


class ModelPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[Model]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Model]: ...

    @abstractmethod
    def get_all(self) -> List[Model]: ...

    @abstractmethod
    def add(self, entity: Model) -> Optional[Model]: ...

    @abstractmethod
    def update(self, entity: Model) -> Optional[Model]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, name: str) -> Optional[Model]: ...
