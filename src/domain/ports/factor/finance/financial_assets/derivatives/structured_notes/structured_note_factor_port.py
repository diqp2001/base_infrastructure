from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.finance.financial_assets.derivatives.structured_notes.structured_note_factor import StructuredNoteFactor


class StructuredNoteFactorPort(ABC):
    """Port interface for StructuredNoteFactor repositories."""

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[StructuredNoteFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[StructuredNoteFactor]: ...

    @abstractmethod
    def get_by_group(self, group: str) -> List[StructuredNoteFactor]: ...

    @abstractmethod
    def get_all(self) -> List[StructuredNoteFactor]: ...

    @abstractmethod
    def add(self, entity: StructuredNoteFactor) -> Optional[StructuredNoteFactor]: ...

    @abstractmethod
    def update(self, entity: StructuredNoteFactor) -> Optional[StructuredNoteFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[StructuredNoteFactor]: ...
