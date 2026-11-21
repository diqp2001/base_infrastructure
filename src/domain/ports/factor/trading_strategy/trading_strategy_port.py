"""
src/domain/ports/factor/trading_strategy_port.py

Abstract port for the TradingStrategy factor repository.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.factor.trading_strategy.trading_strategy import TradingStrategy


class TradingStrategyPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[TradingStrategy]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[TradingStrategy]: ...

    @abstractmethod
    def get_all(self) -> List[TradingStrategy]: ...

    @abstractmethod
    def add(self, entity: TradingStrategy) -> Optional[TradingStrategy]: ...

    @abstractmethod
    def update(self, entity: TradingStrategy) -> Optional[TradingStrategy]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[TradingStrategy]: ...
