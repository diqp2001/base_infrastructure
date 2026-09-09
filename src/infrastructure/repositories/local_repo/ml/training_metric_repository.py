"""
src/infrastructure/repositories/local_repo/ml/training_metric_repository.py

Local SQLAlchemy repository for TrainingMetric.
"""

from decimal import Decimal
from typing import Optional, List
from sqlalchemy.orm import Session

from src.domain.entities.ml.training_metric import TrainingMetric
from src.domain.ports.ml.training_metric_port import TrainingMetricPort
from src.infrastructure.repositories.mappers.ml.training_metric_mapper import TrainingMetricMapper
from src.infrastructure.models.ml.training_metric import TrainingMetricModel


class TrainingMetricRepository(TrainingMetricPort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = TrainingMetricMapper()

    @property
    def model_class(self):
        return TrainingMetricModel

    def _to_entity(self, orm) -> Optional[TrainingMetric]:
        return self.mapper.to_domain(orm)

    def _to_model(self, entity: TrainingMetric) -> TrainingMetricModel:
        return self.mapper.to_orm(entity)

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[TrainingMetric]:
        """
        Uniqueness: (model_training_id, metric_name, dataset_type).
        primary_key is unused.
        """
        try:
            model_training_id = kwargs.get("model_training_id")
            metric_name       = kwargs.get("metric_name", primary_key)
            dataset_type      = kwargs.get("dataset_type", "validation")

            existing = (
                self.session.query(TrainingMetricModel)
                .filter(
                    TrainingMetricModel.model_training_id == model_training_id,
                    TrainingMetricModel.metric_name       == metric_name,
                    TrainingMetricModel.dataset_type      == dataset_type,
                )
                .one_or_none()
            )
            if existing:
                return self._to_entity(existing)

            metric_value = kwargs.get("metric_value", Decimal("0"))
            orm = TrainingMetricModel(
                model_training_id=model_training_id,
                metric_name=metric_name,
                metric_value=metric_value,
                dataset_type=dataset_type,
                calculation_date=kwargs.get("calculation_date"),
                configuration=kwargs.get("configuration"),
            )
            self.session.add(orm)
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error in TrainingMetric._create_or_get: {e}")
            self.session.rollback()
            return None

    def get_by_id(self, id: int) -> Optional[TrainingMetric]:
        orm = (
            self.session.query(TrainingMetricModel)
            .filter(TrainingMetricModel.id == id)
            .one_or_none()
        )
        return self._to_entity(orm)

    def get_by_training(self, model_training_id: int) -> List[TrainingMetric]:
        rows = (
            self.session.query(TrainingMetricModel)
            .filter(TrainingMetricModel.model_training_id == model_training_id)
            .all()
        )
        return [self._to_entity(r) for r in rows]

    def get_by_training_and_dataset(
        self, model_training_id: int, dataset_type: str
    ) -> List[TrainingMetric]:
        rows = (
            self.session.query(TrainingMetricModel)
            .filter(
                TrainingMetricModel.model_training_id == model_training_id,
                TrainingMetricModel.dataset_type      == dataset_type,
            )
            .all()
        )
        return [self._to_entity(r) for r in rows]

    def get_all(self) -> List[TrainingMetric]:
        return [self._to_entity(o) for o in self.session.query(TrainingMetricModel).all()]

    def add(self, entity: TrainingMetric) -> Optional[TrainingMetric]:
        try:
            orm = self._to_model(entity)
            self.session.add(orm)
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error adding TrainingMetric: {e}")
            self.session.rollback()
            return None

    def update(self, entity: TrainingMetric) -> Optional[TrainingMetric]:
        try:
            orm = (
                self.session.query(TrainingMetricModel)
                .filter(TrainingMetricModel.id == entity.id)
                .one_or_none()
            )
            if not orm:
                return None
            orm.metric_value     = entity.metric_value
            orm.calculation_date = entity.calculation_date
            orm.configuration    = entity.get_configuration_json()
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error updating TrainingMetric {entity.id}: {e}")
            self.session.rollback()
            return None

    def delete(self, id: int) -> bool:
        try:
            orm = (
                self.session.query(TrainingMetricModel)
                .filter(TrainingMetricModel.id == id)
                .one_or_none()
            )
            if not orm:
                return False
            self.session.delete(orm)
            self.session.commit()
            return True
        except Exception as e:
            print(f"Error deleting TrainingMetric {id}: {e}")
            self.session.rollback()
            return False
