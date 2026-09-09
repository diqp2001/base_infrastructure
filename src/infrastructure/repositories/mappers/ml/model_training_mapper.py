"""
src/infrastructure/repositories/mappers/ml/model_training_mapper.py

Mapper between ModelTraining domain entity and ModelTrainingModel ORM model.
"""

import json
from typing import Optional
from src.domain.entities.ml.model_training import ModelTraining
from src.infrastructure.models.ml.model_training import ModelTrainingModel


class ModelTrainingMapper:

    def to_domain(self, orm: Optional[ModelTrainingModel]) -> Optional[ModelTraining]:
        if not orm:
            return None
        config = {}
        if orm.training_configuration:
            try:
                config = json.loads(orm.training_configuration)
            except (json.JSONDecodeError, TypeError):
                config = {}
        return ModelTraining(
            id=orm.id,
            model_id=orm.model_id,
            universe_id=orm.universe_id,
            training_start_date=orm.training_start_date,
            training_end_date=orm.training_end_date,
            validation_start_date=orm.validation_start_date,
            validation_end_date=orm.validation_end_date,
            test_start_date=orm.test_start_date,
            test_end_date=orm.test_end_date,
            status=orm.status or "pending",
            started_at=orm.started_at,
            completed_at=orm.completed_at,
            training_configuration=config,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def to_orm(self, entity: ModelTraining) -> ModelTrainingModel:
        return ModelTrainingModel(
            id=entity.id,
            model_id=entity.model_id,
            universe_id=entity.universe_id,
            training_start_date=entity.training_start_date,
            training_end_date=entity.training_end_date,
            validation_start_date=entity.validation_start_date,
            validation_end_date=entity.validation_end_date,
            test_start_date=entity.test_start_date,
            test_end_date=entity.test_end_date,
            status=entity.status,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            training_configuration=(
                json.dumps(entity.training_configuration, default=str)
                if entity.training_configuration else None
            ),
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @property
    def model_class(self):
        return ModelTrainingModel
