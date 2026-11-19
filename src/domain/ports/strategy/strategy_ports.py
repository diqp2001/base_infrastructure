"""
Ports of the strategy domain: where strategies (one row per version) and their experiments are kept.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.strategy.strategy import Strategy
from src.domain.entities.strategy.strategy_experiment import StrategyExperiment


class StrategyPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[Strategy]: ...

    @abstractmethod
    def get_version(self, name: str, version: int) -> Optional[Strategy]: ...

    @abstractmethod
    def get_versions(self, name: str) -> List[Strategy]: ...

    @abstractmethod
    def latest_version_number(self, name: str) -> int: ...

    @abstractmethod
    def get_by_universe(self, universe_id: int) -> List[Strategy]: ...

    @abstractmethod
    def get_all(self) -> List[Strategy]: ...

    @abstractmethod
    def add(self, entity: Strategy) -> Strategy: ...

    @abstractmethod
    def update(self, entity: Strategy) -> Strategy: ...


StrategyConfigurationPort = StrategyPort          # former name


class StrategyExperimentPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[StrategyExperiment]: ...

    @abstractmethod
    def get_by_strategy(self, strategy_id: int) -> List[StrategyExperiment]: ...

    @abstractmethod
    def get_by_status(self, status: str) -> List[StrategyExperiment]: ...

    @abstractmethod
    def get_all(self) -> List[StrategyExperiment]: ...

    @abstractmethod
    def add(self, entity: StrategyExperiment) -> StrategyExperiment: ...

    @abstractmethod
    def update(self, entity: StrategyExperiment) -> StrategyExperiment: ...
