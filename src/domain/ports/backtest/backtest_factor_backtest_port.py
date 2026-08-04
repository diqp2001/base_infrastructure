from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities.backtest.backtest_factor_backtest import BacktestFactorBacktest


class BacktestFactorBacktestPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[BacktestFactorBacktest]: ...

    @abstractmethod
    def get_by_backtest_id(self, backtest_id: int) -> List[BacktestFactorBacktest]: ...

    @abstractmethod
    def get_by_backtest_factor_id(self, backtest_factor_id: int) -> List[BacktestFactorBacktest]: ...

    @abstractmethod
    def get_all(self) -> List[BacktestFactorBacktest]: ...

    @abstractmethod
    def add(self, entity: BacktestFactorBacktest) -> Optional[BacktestFactorBacktest]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, backtest_id: int, backtest_factor_id: int) -> Optional[BacktestFactorBacktest]: ...
