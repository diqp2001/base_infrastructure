"""
src/domain/ports/factor/constituent_score_factor_port.py

Abstract port for ConstituentScoreFactor repository.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.factor.constituent_score_factor import ConstituentScoreFactor


class ConstituentScoreFactorPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[ConstituentScoreFactor]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[ConstituentScoreFactor]: ...

    @abstractmethod
    def get_all(self) -> List[ConstituentScoreFactor]: ...

    @abstractmethod
    def add(self, entity: ConstituentScoreFactor) -> Optional[ConstituentScoreFactor]: ...

    @abstractmethod
    def update(self, entity: ConstituentScoreFactor) -> Optional[ConstituentScoreFactor]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ConstituentScoreFactor]: ...
