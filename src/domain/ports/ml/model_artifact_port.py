"""
src/domain/ports/ml/model_artifact_port.py

Abstract port for ModelArtifact repository.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.ml.model_artifact import ModelArtifact


class ModelArtifactPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[ModelArtifact]: ...

    @abstractmethod
    def get_by_training(self, model_training_id: int) -> List[ModelArtifact]: ...

    @abstractmethod
    def get_by_training_and_type(
        self, model_training_id: int, artifact_type: str
    ) -> List[ModelArtifact]: ...

    @abstractmethod
    def get_all(self) -> List[ModelArtifact]: ...

    @abstractmethod
    def add(self, entity: ModelArtifact) -> Optional[ModelArtifact]: ...

    @abstractmethod
    def update(self, entity: ModelArtifact) -> Optional[ModelArtifact]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ModelArtifact]: ...
