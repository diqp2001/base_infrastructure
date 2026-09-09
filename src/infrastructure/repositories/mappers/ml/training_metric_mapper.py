"""
src/infrastructure/repositories/mappers/ml/training_metric_mapper.py

Mapper between TrainingMetric domain entity and TrainingMetricModel ORM model.
"""

import json
from decimal import Decimal
from typing import Optional
from src.domain.entities.ml.training_metric import TrainingMetric
from src.infrastructure.models.ml.training_metric import TrainingMetricModel


class TrainingMetricMapper:

    def to_domain(self, orm: Optional[TrainingMetricModel]) -> Optional[TrainingMetric]:
        if not orm:
            return None
        config = {}
        if orm.configuration:
            try:
                config = json.loads(orm.configuration)
            except (json.JSONDecodeError, TypeError):
                config = {}
        return TrainingMetric(
            id=orm.id,
            model_training_id=orm.model_training_id,
            metric_name=orm.metric_name,
            metric_value=Decimal(str(orm.metric_value)) if orm.metric_value is not None else Decimal("0"),
            dataset_type=orm.dataset_type,
            calculation_date=orm.calculation_date,
            configuration=config,
        )

    def to_orm(self, entity: TrainingMetric) -> TrainingMetricModel:
        return TrainingMetricModel(
            id=entity.id,
            model_training_id=entity.model_training_id,
            metric_name=entity.metric_name,
            metric_value=entity.metric_value,
            dataset_type=entity.dataset_type,
            calculation_date=entity.calculation_date,
            configuration=json.dumps(entity.configuration) if entity.configuration else None,
        )

    @property
    def model_class(self):
        return TrainingMetricModel
