"""
src/domain/ports/ml/ml_model_port.py

Abstract port for MLModel repository.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.ml.ml_model import MLModel


class MLModelPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[MLModel]: ...

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[MLModel]: ...

    @abstractmethod
    def get_all(self) -> List[MLModel]: ...

    @abstractmethod
    def add(self, entity: MLModel) -> Optional[MLModel]: ...

    @abstractmethod
    def update(self, entity: MLModel) -> Optional[MLModel]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[MLModel]: ...
