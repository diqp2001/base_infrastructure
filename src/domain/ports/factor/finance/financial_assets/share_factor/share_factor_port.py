from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.share_factor import ShareFactor


class ShareFactorPort(ABC):
    """Port interface for ShareFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[ShareFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[ShareFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[ShareFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[ShareFactor]: ...

    @abstractmethod
    def get_all(self) -> List[ShareFactor]: ...

    @abstractmethod
    def add(self, entity: ShareFactor) -> Optional[ShareFactor]: ...

    @abstractmethod
    def update(self, entity: ShareFactor) -> Optional[ShareFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ShareFactor]: ...
