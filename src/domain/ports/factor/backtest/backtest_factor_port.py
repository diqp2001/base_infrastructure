from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.factor.backtest.backtest_factor import BacktestFactor


class BacktestFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[BacktestFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[BacktestFactor]: ...

    @abstractmethod
    def get_all(self) -> List[BacktestFactor]: ...

    @abstractmethod
    def add(self, entity: BacktestFactor) -> Optional[BacktestFactor]: ...

    @abstractmethod
    def update(self, entity: BacktestFactor) -> Optional[BacktestFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[BacktestFactor]: ...
