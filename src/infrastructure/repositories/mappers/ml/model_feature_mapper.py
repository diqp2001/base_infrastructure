"""
src/infrastructure/repositories/mappers/ml/model_feature_mapper.py

Mapper between ModelFeature domain entity and ModelFeatureModel ORM model.
"""

import json
from typing import Optional
from src.domain.entities.ml.model_feature import ModelFeature
from src.infrastructure.models.ml.model_feature import ModelFeatureModel


class ModelFeatureMapper:

    def to_domain(self, orm: Optional[ModelFeatureModel]) -> Optional[ModelFeature]:
        if not orm:
            return None
        config = {}
        if orm.feature_configuration:
            try:
                config = json.loads(orm.feature_configuration)
            except (json.JSONDecodeError, TypeError):
                config = {}
        return ModelFeature(
            id=orm.id,
            model_id=orm.model_id,
            factor_id=orm.factor_id,
            name=orm.name,
            lag=orm.lag,
            enabled=bool(orm.enabled),
            feature_configuration=config,
        )

    def to_orm(self, entity: ModelFeature) -> ModelFeatureModel:
        return ModelFeatureModel(
            id=entity.id,
            model_id=entity.model_id,
            factor_id=entity.factor_id,
            name=entity.name,
            lag=entity.lag,
            enabled=entity.enabled,
            feature_configuration=(
                json.dumps(entity.feature_configuration)
                if entity.feature_configuration else None
            ),
        )

    @property
    def model_class(self):
        return ModelFeatureModel
