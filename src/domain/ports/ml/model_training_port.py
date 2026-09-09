"""
src/domain/ports/ml/model_training_port.py

Abstract port for ModelTraining repository.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.ml.model_training import ModelTraining


class ModelTrainingPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[ModelTraining]: ...

    @abstractmethod
    def get_by_model(self, model_id: int) -> List[ModelTraining]: ...

    @abstractmethod
    def get_by_status(self, status: str) -> List[ModelTraining]: ...

    @abstractmethod
    def get_all(self) -> List[ModelTraining]: ...

    @abstractmethod
    def add(self, entity: ModelTraining) -> Optional[ModelTraining]: ...

    @abstractmethod
    def update(self, entity: ModelTraining) -> Optional[ModelTraining]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ModelTraining]: ...
