from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.factor_dependency import FactorDependency


class FactorDependencyPort(ABC):
    """Port interface for FactorDependency repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[FactorDependency]: ...

    @abstractmethod
    def get_by_dependent_factor_id(self, dependent_factor_id: int) -> List[FactorDependency]: ...

    @abstractmethod
    def get_by_independent_factor_id(self, independent_factor_id: int) -> List[FactorDependency]: ...

    @abstractmethod
    def get_all(self) -> List[FactorDependency]: ...

    @abstractmethod
    def add(self, entity: FactorDependency) -> Optional[FactorDependency]: ...

    @abstractmethod
    def update(self, entity: FactorDependency) -> Optional[FactorDependency]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def exists(self, dependent_factor_id: int, independent_factor_id: int) -> bool: ...
