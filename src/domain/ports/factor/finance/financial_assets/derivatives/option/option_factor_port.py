from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.option_factor import OptionFactor


class OptionFactorPort(ABC):
    """Port interface for OptionFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[OptionFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[OptionFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[OptionFactor]: ...

    @abstractmethod
    def get_all(self) -> List[OptionFactor]: ...

    @abstractmethod
    def add(self, entity: OptionFactor) -> Optional[OptionFactor]: ...

    @abstractmethod
    def update(self, entity: OptionFactor) -> Optional[OptionFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[OptionFactor]: ...
