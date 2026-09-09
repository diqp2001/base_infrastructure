"""
src/infrastructure/repositories/local_repo/ml/model_artifact_repository.py

Local SQLAlchemy repository for ModelArtifact.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from src.domain.entities.ml.model_artifact import ModelArtifact
from src.domain.ports.ml.model_artifact_port import ModelArtifactPort
from src.infrastructure.repositories.mappers.ml.model_artifact_mapper import ModelArtifactMapper
from src.infrastructure.models.ml.model_artifact import ModelArtifactModel


class ModelArtifactRepository(ModelArtifactPort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = ModelArtifactMapper()

    @property
    def model_class(self):
        return ModelArtifactModel

    def _to_entity(self, orm) -> Optional[ModelArtifact]:
        return self.mapper.to_domain(orm)

    def _to_model(self, entity: ModelArtifact) -> ModelArtifactModel:
        return self.mapper.to_orm(entity)

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ModelArtifact]:
        """
        Uniqueness: (model_training_id, artifact_type, name).
        primary_key is the artifact name.
        """
        try:
            model_training_id = kwargs.get("model_training_id")
            artifact_type     = kwargs.get("artifact_type", "trained_model")

            existing = (
                self.session.query(ModelArtifactModel)
                .filter(
                    ModelArtifactModel.model_training_id == model_training_id,
                    ModelArtifactModel.artifact_type     == artifact_type,
                    ModelArtifactModel.name              == primary_key,
                )
                .one_or_none()
            )
            if existing:
                return self._to_entity(existing)

            orm = ModelArtifactModel(
                model_training_id=model_training_id,
                artifact_type=artifact_type,
                name=primary_key,
                location=kwargs.get("location", ""),
                format=kwargs.get("format"),
                artifact_metadata=kwargs.get("artifact_metadata"),
                created_at=datetime.utcnow(),
            )
            self.session.add(orm)
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error in ModelArtifact._create_or_get: {e}")
            self.session.rollback()
            return None

    def get_by_id(self, id: int) -> Optional[ModelArtifact]:
        orm = (
            self.session.query(ModelArtifactModel)
            .filter(ModelArtifactModel.id == id)
            .one_or_none()
        )
        return self._to_entity(orm)

    def get_by_training(self, model_training_id: int) -> List[ModelArtifact]:
        rows = (
            self.session.query(ModelArtifactModel)
            .filter(ModelArtifactModel.model_training_id == model_training_id)
            .all()
        )
        return [self._to_entity(r) for r in rows]

    def get_by_training_and_type(
        self, model_training_id: int, artifact_type: str
    ) -> List[ModelArtifact]:
        rows = (
            self.session.query(ModelArtifactModel)
            .filter(
                ModelArtifactModel.model_training_id == model_training_id,
                ModelArtifactModel.artifact_type     == artifact_type,
            )
            .all()
        )
        return [self._to_entity(r) for r in rows]

    def get_all(self) -> List[ModelArtifact]:
        return [self._to_entity(o) for o in self.session.query(ModelArtifactModel).all()]

    def add(self, entity: ModelArtifact) -> Optional[ModelArtifact]:
        try:
            orm = self._to_model(entity)
            self.session.add(orm)
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error adding ModelArtifact: {e}")
            self.session.rollback()
            return None

    def update(self, entity: ModelArtifact) -> Optional[ModelArtifact]:
        try:
            orm = (
                self.session.query(ModelArtifactModel)
                .filter(ModelArtifactModel.id == entity.id)
                .one_or_none()
            )
            if not orm:
                return None
            orm.location          = entity.location
            orm.format            = entity.format
            orm.artifact_metadata = entity.get_artifact_metadata_json()
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error updating ModelArtifact {entity.id}: {e}")
            self.session.rollback()
            return None

    def delete(self, id: int) -> bool:
        try:
            orm = (
                self.session.query(ModelArtifactModel)
                .filter(ModelArtifactModel.id == id)
                .one_or_none()
            )
            if not orm:
                return False
            self.session.delete(orm)
            self.session.commit()
            return True
        except Exception as e:
            print(f"Error deleting ModelArtifact {id}: {e}")
            self.session.rollback()
            return False
