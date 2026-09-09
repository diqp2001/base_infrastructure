"""
src/infrastructure/repositories/local_repo/ml/ml_model_repository.py

Local SQLAlchemy repository for MLModel.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from src.domain.entities.ml.ml_model import MLModel
from src.domain.ports.ml.ml_model_port import MLModelPort
from src.infrastructure.repositories.mappers.ml.ml_model_mapper import MLModelMapper
from src.infrastructure.models.ml.ml_model import MLModelModel


class MLModelRepository(MLModelPort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = MLModelMapper()

    @property
    def model_class(self):
        return MLModelModel

    def _to_entity(self, orm) -> Optional[MLModel]:
        return self.mapper.to_domain(orm)

    def _to_model(self, entity: MLModel) -> MLModelModel:
        return self.mapper.to_orm(entity)

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[MLModel]:
        try:
            existing = self.get_by_name(primary_key)
            if existing:
                return existing

            now = datetime.utcnow()
            orm = MLModelModel(
                name=primary_key,
                description=kwargs.get("description"),
                model_type=kwargs.get("model_type", "lightgbm"),
                target_factor_id=kwargs.get("target_factor_id"),
                configuration=kwargs.get("configuration"),
                created_at=now,
                updated_at=now,
            )
            self.session.add(orm)
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error in MLModel._create_or_get for '{primary_key}': {e}")
            self.session.rollback()
            return None

    def get_by_id(self, id: int) -> Optional[MLModel]:
        orm = self.session.query(MLModelModel).filter(MLModelModel.id == id).one_or_none()
        return self._to_entity(orm)

    def get_by_name(self, name: str) -> Optional[MLModel]:
        orm = self.session.query(MLModelModel).filter(MLModelModel.name == name).one_or_none()
        return self._to_entity(orm)

    def get_all(self) -> List[MLModel]:
        return [self._to_entity(o) for o in self.session.query(MLModelModel).all()]

    def add(self, entity: MLModel) -> Optional[MLModel]:
        try:
            orm = self._to_model(entity)
            self.session.add(orm)
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error adding MLModel: {e}")
            self.session.rollback()
            return None

    def update(self, entity: MLModel) -> Optional[MLModel]:
        try:
            orm = self.session.query(MLModelModel).filter(MLModelModel.id == entity.id).one_or_none()
            if not orm:
                return None
            orm.name             = entity.name
            orm.description      = entity.description
            orm.model_type       = entity.model_type
            orm.target_factor_id = entity.target_factor_id
            orm.configuration    = entity.get_configuration_json()
            orm.updated_at       = datetime.utcnow()
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error updating MLModel {entity.id}: {e}")
            self.session.rollback()
            return None

    def delete(self, id: int) -> bool:
        try:
            orm = self.session.query(MLModelModel).filter(MLModelModel.id == id).one_or_none()
            if not orm:
                return False
            self.session.delete(orm)
            self.session.commit()
            return True
        except Exception as e:
            print(f"Error deleting MLModel {id}: {e}")
            self.session.rollback()
            return False
