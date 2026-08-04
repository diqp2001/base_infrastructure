from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.backtest.backtest import Backtest


class BacktestPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[Backtest]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Backtest]: ...

    @abstractmethod
    def get_by_model_id(self, model_id: int) -> List[Backtest]: ...

    @abstractmethod
    def get_all(self) -> List[Backtest]: ...

    @abstractmethod
    def add(self, entity: Backtest) -> Optional[Backtest]: ...

    @abstractmethod
    def update(self, entity: Backtest) -> Optional[Backtest]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, name: str, model_id: int, **kwargs) -> Optional[Backtest]: ...
