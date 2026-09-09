"""
src/infrastructure/repositories/mappers/ml/ml_model_mapper.py

Mapper between MLModel domain entity and MLModelModel ORM model.
"""

import json
from typing import Optional
from src.domain.entities.ml.ml_model import MLModel
from src.infrastructure.models.ml.ml_model import MLModelModel


class MLModelMapper:

    def to_domain(self, orm: Optional[MLModelModel]) -> Optional[MLModel]:
        if not orm:
            return None
        config = {}
        if orm.configuration:
            try:
                config = json.loads(orm.configuration)
            except (json.JSONDecodeError, TypeError):
                config = {}
        return MLModel(
            id=orm.id,
            name=orm.name,
            description=orm.description,
            model_type=orm.model_type,
            target_factor_id=orm.target_factor_id,
            configuration=config,
            created_at=orm.created_at,
            updated_at=orm.updated_at,
        )

    def to_orm(self, entity: MLModel) -> MLModelModel:
        return MLModelModel(
            id=entity.id,
            name=entity.name,
            description=entity.description,
            model_type=entity.model_type,
            target_factor_id=entity.target_factor_id,
            configuration=json.dumps(entity.configuration) if entity.configuration else None,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    @property
    def model_class(self):
        return MLModelModel
