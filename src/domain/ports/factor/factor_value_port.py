from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.factor_value import FactorValue


class FactorValuePort(ABC):
    """Port interface for FactorValue repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[FactorValue]: ...

    @abstractmethod
    def get_by_factor_entity_date(self, factor_id: int, entity_id: int, date_str: str) -> Optional[FactorValue]: ...

    @abstractmethod
    def get_all_dates_by_id_entity_id(self, factor_id: int, entity_id: int) -> List[str]: ...

    @abstractmethod
    def get_all(self) -> List[FactorValue]: ...

    @abstractmethod
    def add(self, entity: FactorValue) -> Optional[FactorValue]: ...

    @abstractmethod
    def update(self, entity: FactorValue) -> Optional[FactorValue]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...
