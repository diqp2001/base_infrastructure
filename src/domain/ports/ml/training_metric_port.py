"""
src/domain/ports/ml/training_metric_port.py

Abstract port for TrainingMetric repository.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from src.domain.entities.ml.training_metric import TrainingMetric


class TrainingMetricPort(ABC):

    @abstractmethod
    def get_by_id(self, id: int) -> Optional[TrainingMetric]: ...

    @abstractmethod
    def get_by_training(self, model_training_id: int) -> List[TrainingMetric]: ...

    @abstractmethod
    def get_by_training_and_dataset(
        self, model_training_id: int, dataset_type: str
    ) -> List[TrainingMetric]: ...

    @abstractmethod
    def get_all(self) -> List[TrainingMetric]: ...

    @abstractmethod
    def add(self, entity: TrainingMetric) -> Optional[TrainingMetric]: ...

    @abstractmethod
    def update(self, entity: TrainingMetric) -> Optional[TrainingMetric]: ...

    @abstractmethod
    def delete(self, id: int) -> bool: ...

    @abstractmethod
    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[TrainingMetric]: ...
