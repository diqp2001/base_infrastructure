"""
src/infrastructure/repositories/mappers/ml/model_artifact_mapper.py

Mapper between ModelArtifact domain entity and ModelArtifactModel ORM model.
"""

import json
from typing import Optional
from src.domain.entities.ml.model_artifact import ModelArtifact
from src.infrastructure.models.ml.model_artifact import ModelArtifactModel


class ModelArtifactMapper:

    def to_domain(self, orm: Optional[ModelArtifactModel]) -> Optional[ModelArtifact]:
        if not orm:
            return None
        meta = {}
        if orm.artifact_metadata:
            try:
                meta = json.loads(orm.artifact_metadata)
            except (json.JSONDecodeError, TypeError):
                meta = {}
        return ModelArtifact(
            id=orm.id,
            model_training_id=orm.model_training_id,
            artifact_type=orm.artifact_type,
            name=orm.name,
            location=orm.location,
            format=orm.format,
            artifact_metadata=meta,
            created_at=orm.created_at,
        )

    def to_orm(self, entity: ModelArtifact) -> ModelArtifactModel:
        return ModelArtifactModel(
            id=entity.id,
            model_training_id=entity.model_training_id,
            artifact_type=entity.artifact_type,
            name=entity.name,
            location=entity.location,
            format=entity.format,
            artifact_metadata=(
                json.dumps(entity.artifact_metadata) if entity.artifact_metadata else None
            ),
            created_at=entity.created_at,
        )

    @property
    def model_class(self):
        return ModelArtifactModel
