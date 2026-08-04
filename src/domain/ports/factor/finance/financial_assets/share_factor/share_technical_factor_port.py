from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.share_factor.share_technical_factor import ShareTechnicalFactor


class ShareTechnicalFactorPort(ABC):
    """Port interface for ShareTechnicalFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[ShareTechnicalFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[ShareTechnicalFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[ShareTechnicalFactor]: ...

    @abstractmethod
    def get_by_subgroup(self, subgroup: str) -> List[ShareTechnicalFactor]: ...

    @abstractmethod
    def get_all(self) -> List[ShareTechnicalFactor]: ...

    @abstractmethod
    def add(self, entity: ShareTechnicalFactor) -> Optional[ShareTechnicalFactor]: ...

    @abstractmethod
    def update(self, entity: ShareTechnicalFactor) -> Optional[ShareTechnicalFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ShareTechnicalFactor]: ...
