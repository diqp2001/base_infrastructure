"""
Ports of the strategy configuration domain: where configurations and experiments are kept.
"""

from abc import ABC, abstractmethod
from typing import List, Optional

from src.domain.entities.strategy.strategy_configuration import StrategyConfiguration
from src.domain.entities.strategy.strategy_experiment import StrategyExperiment


class StrategyConfigurationPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[StrategyConfiguration]: ...

    @abstractmethod
    def get_version(self, name: str, version: int) -> Optional[StrategyConfiguration]: ...

    @abstractmethod
    def get_versions(self, name: str) -> List[StrategyConfiguration]: ...

    @abstractmethod
    def latest_version_number(self, name: str) -> int: ...

    @abstractmethod
    def get_all(self) -> List[StrategyConfiguration]: ...

    @abstractmethod
    def add(self, entity: StrategyConfiguration) -> StrategyConfiguration: ...

    @abstractmethod
    def update(self, entity: StrategyConfiguration) -> StrategyConfiguration: ...


class StrategyExperimentPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[StrategyExperiment]: ...

    @abstractmethod
    def get_by_configuration(self, configuration_id: int) -> List[StrategyExperiment]: ...

    @abstractmethod
    def get_by_status(self, status: str) -> List[StrategyExperiment]: ...

    @abstractmethod
    def get_all(self) -> List[StrategyExperiment]: ...

    @abstractmethod
    def add(self, entity: StrategyExperiment) -> StrategyExperiment: ...

    @abstractmethod
    def update(self, entity: StrategyExperiment) -> StrategyExperiment: ...
