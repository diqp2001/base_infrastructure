from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.share_momentum_factor import ShareMomentumFactor


class ShareMomentumFactorPort(ABC):
    """Port interface for ShareMomentumFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[ShareMomentumFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[ShareMomentumFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[ShareMomentumFactor]: ...

    @abstractmethod
    def get_all(self) -> List[ShareMomentumFactor]: ...

    @abstractmethod
    def add(self, entity: ShareMomentumFactor) -> Optional[ShareMomentumFactor]: ...

    @abstractmethod
    def update(self, entity: ShareMomentumFactor) -> Optional[ShareMomentumFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ShareMomentumFactor]: ...
