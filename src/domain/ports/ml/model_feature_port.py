"""
src/domain/ports/ml/model_feature_port.py

Abstract port for ModelFeature repository.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.ml.model_feature import ModelFeature


class ModelFeaturePort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[ModelFeature]: ...

    @abstractmethod
    def get_by_model(self, model_id: int) -> List[ModelFeature]: ...

    @abstractmethod
    def get_enabled_by_model(self, model_id: int) -> List[ModelFeature]: ...

    @abstractmethod
    def get_all(self) -> List[ModelFeature]: ...

    @abstractmethod
    def add(self, entity: ModelFeature) -> Optional[ModelFeature]: ...

    @abstractmethod
    def update(self, entity: ModelFeature) -> Optional[ModelFeature]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ModelFeature]: ...
