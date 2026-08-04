from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.country_factor import CountryFactor


class CountryFactorPort(ABC):
    """Port interface for CountryFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[CountryFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[CountryFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[CountryFactor]: ...

    @abstractmethod
    def get_all(self) -> List[CountryFactor]: ...

    @abstractmethod
    def add(self, entity: CountryFactor) -> Optional[CountryFactor]: ...

    @abstractmethod
    def update(self, entity: CountryFactor) -> Optional[CountryFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[CountryFactor]: ...
