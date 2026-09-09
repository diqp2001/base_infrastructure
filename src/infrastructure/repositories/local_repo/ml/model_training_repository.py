"""
src/infrastructure/repositories/local_repo/ml/model_training_repository.py

Local SQLAlchemy repository for ModelTraining.
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session

from src.domain.entities.ml.model_training import ModelTraining
from src.domain.ports.ml.model_training_port import ModelTrainingPort
from src.infrastructure.repositories.mappers.ml.model_training_mapper import ModelTrainingMapper
from src.infrastructure.models.ml.model_training import ModelTrainingModel


class ModelTrainingRepository(ModelTrainingPort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = ModelTrainingMapper()

    @property
    def model_class(self):
        return ModelTrainingModel

    def _to_entity(self, orm) -> Optional[ModelTraining]:
        return self.mapper.to_domain(orm)

    def _to_model(self, entity: ModelTraining) -> ModelTrainingModel:
        return self.mapper.to_orm(entity)

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ModelTraining]:
        """
        primary_key is unused. Uniqueness is on (model_id, training_start_date, training_end_date).
        A new training run is always created unless an identical one already exists.
        """
        try:
            model_id            = kwargs.get("model_id")
            training_start_date = kwargs.get("training_start_date")
            training_end_date   = kwargs.get("training_end_date")

            if model_id and training_start_date and training_end_date:
                existing = (
                    self.session.query(ModelTrainingModel)
                    .filter(
                        ModelTrainingModel.model_id            == model_id,
                        ModelTrainingModel.training_start_date == training_start_date,
                        ModelTrainingModel.training_end_date   == training_end_date,
                    )
                    .first()
                )
                if existing:
                    return self._to_entity(existing)

            now = datetime.utcnow()
            orm = ModelTrainingModel(
                model_id=model_id,
                universe_id=kwargs.get("universe_id"),
                training_start_date=training_start_date,
                training_end_date=training_end_date,
                validation_start_date=kwargs.get("validation_start_date"),
                validation_end_date=kwargs.get("validation_end_date"),
                test_start_date=kwargs.get("test_start_date"),
                test_end_date=kwargs.get("test_end_date"),
                status=kwargs.get("status", "pending"),
                started_at=kwargs.get("started_at"),
                completed_at=kwargs.get("completed_at"),
                training_configuration=kwargs.get("training_configuration"),
                created_at=now,
                updated_at=now,
            )
            self.session.add(orm)
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error in ModelTraining._create_or_get: {e}")
            self.session.rollback()
            return None

    def get_by_id(self, id: int) -> Optional[ModelTraining]:
        orm = self.session.query(ModelTrainingModel).filter(ModelTrainingModel.id == id).one_or_none()
        return self._to_entity(orm)

    def get_by_model(self, model_id: int) -> List[ModelTraining]:
        rows = (
            self.session.query(ModelTrainingModel)
            .filter(ModelTrainingModel.model_id == model_id)
            .order_by(ModelTrainingModel.created_at.desc())
            .all()
        )
        return [self._to_entity(r) for r in rows]

    def get_by_status(self, status: str) -> List[ModelTraining]:
        rows = (
            self.session.query(ModelTrainingModel)
            .filter(ModelTrainingModel.status == status)
            .all()
        )
        return [self._to_entity(r) for r in rows]

    def get_all(self) -> List[ModelTraining]:
        return [self._to_entity(o) for o in self.session.query(ModelTrainingModel).all()]

    def add(self, entity: ModelTraining) -> Optional[ModelTraining]:
        try:
            orm = self._to_model(entity)
            self.session.add(orm)
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error adding ModelTraining: {e}")
            self.session.rollback()
            return None

    def update(self, entity: ModelTraining) -> Optional[ModelTraining]:
        try:
            orm = (
                self.session.query(ModelTrainingModel)
                .filter(ModelTrainingModel.id == entity.id)
                .one_or_none()
            )
            if not orm:
                return None
            orm.status                 = entity.status
            orm.started_at             = entity.started_at
            orm.completed_at           = entity.completed_at
            orm.training_configuration = entity.get_training_configuration_json()
            orm.updated_at             = datetime.utcnow()
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error updating ModelTraining {entity.id}: {e}")
            self.session.rollback()
            return None

    def delete(self, id: int) -> bool:
        try:
            orm = (
                self.session.query(ModelTrainingModel)
                .filter(ModelTrainingModel.id == id)
                .one_or_none()
            )
            if not orm:
                return False
            self.session.delete(orm)
            self.session.commit()
            return True
        except Exception as e:
            print(f"Error deleting ModelTraining {id}: {e}")
            self.session.rollback()
            return False
