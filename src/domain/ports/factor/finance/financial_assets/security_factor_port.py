from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.security_factor import SecurityFactor


class SecurityFactorPort(ABC):
    """Port interface for SecurityFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[SecurityFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[SecurityFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[SecurityFactor]: ...

    @abstractmethod
    def get_all(self) -> List[SecurityFactor]: ...

    @abstractmethod
    def add(self, entity: SecurityFactor) -> Optional[SecurityFactor]: ...

    @abstractmethod
    def update(self, entity: SecurityFactor) -> Optional[SecurityFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[SecurityFactor]: ...
