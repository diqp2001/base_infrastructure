from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.share_volatility_factor import ShareVolatilityFactor


class ShareVolatilityFactorPort(ABC):
    """Port interface for ShareVolatilityFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[ShareVolatilityFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[ShareVolatilityFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[ShareVolatilityFactor]: ...

    @abstractmethod
    def get_all(self) -> List[ShareVolatilityFactor]: ...

    @abstractmethod
    def add(self, entity: ShareVolatilityFactor) -> Optional[ShareVolatilityFactor]: ...

    @abstractmethod
    def update(self, entity: ShareVolatilityFactor) -> Optional[ShareVolatilityFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ShareVolatilityFactor]: ...
