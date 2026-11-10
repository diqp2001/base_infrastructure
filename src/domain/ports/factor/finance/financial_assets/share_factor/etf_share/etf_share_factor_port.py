from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.etf_share.etf_share_factor import ETFShareFactor


class ETFShareFactorPort(ABC):
    """Port interface for ETFShareFactor repositories (and its subclasses' repositories)."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[ETFShareFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[ETFShareFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[ETFShareFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[ETFShareFactor]: ...

    @abstractmethod
    def get_all(self) -> List[ETFShareFactor]: ...

    @abstractmethod
    def add(self, entity: ETFShareFactor) -> Optional[ETFShareFactor]: ...

    @abstractmethod
    def update(self, entity: ETFShareFactor) -> Optional[ETFShareFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ETFShareFactor]: ...
