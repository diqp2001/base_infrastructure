from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.share_target_factor import ShareTargetFactor


class ShareTargetFactorPort(ABC):
    """Port interface for ShareTargetFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[ShareTargetFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[ShareTargetFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[ShareTargetFactor]: ...

    @abstractmethod
    def get_all(self) -> List[ShareTargetFactor]: ...

    @abstractmethod
    def add(self, entity: ShareTargetFactor) -> Optional[ShareTargetFactor]: ...

    @abstractmethod
    def update(self, entity: ShareTargetFactor) -> Optional[ShareTargetFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ShareTargetFactor]: ...
