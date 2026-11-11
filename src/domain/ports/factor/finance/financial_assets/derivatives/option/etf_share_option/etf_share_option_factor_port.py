from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.option.etf_share_option.etf_share_option_factor import ETFShareOptionFactor


class ETFShareOptionFactorPort(ABC):
    """Port interface for ETFShareOptionFactor repositories (and its subclasses' repositories)."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[ETFShareOptionFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[ETFShareOptionFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[ETFShareOptionFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[ETFShareOptionFactor]: ...

    @abstractmethod
    def get_all(self) -> List[ETFShareOptionFactor]: ...

    @abstractmethod
    def add(self, entity: ETFShareOptionFactor) -> Optional[ETFShareOptionFactor]: ...

    @abstractmethod
    def update(self, entity: ETFShareOptionFactor) -> Optional[ETFShareOptionFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ETFShareOptionFactor]: ...
