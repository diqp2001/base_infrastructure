"""
src/infrastructure/repositories/local_repo/ml/model_feature_repository.py

Local SQLAlchemy repository for ModelFeature.
"""

from typing import Optional, List
from sqlalchemy.orm import Session

from src.domain.entities.ml.model_feature import ModelFeature
from src.domain.ports.ml.model_feature_port import ModelFeaturePort
from src.infrastructure.repositories.mappers.ml.model_feature_mapper import ModelFeatureMapper
from src.infrastructure.models.ml.model_feature import ModelFeatureModel


class ModelFeatureRepository(ModelFeaturePort):

    def __init__(self, session: Session, factory=None):
        self.session = session
        self.factory = factory
        self.mapper = ModelFeatureMapper()

    @property
    def model_class(self):
        return ModelFeatureModel

    def _to_entity(self, orm) -> Optional[ModelFeature]:
        return self.mapper.to_domain(orm)

    def _to_model(self, entity: ModelFeature) -> ModelFeatureModel:
        return self.mapper.to_orm(entity)

    def _create_or_get(self, entity_cls, primary_key: str, **kwargs) -> Optional[ModelFeature]:
        """
        Uniqueness: (model_id, factor_id, lag).
        primary_key is unused; all keys come from kwargs.
        """
        try:
            model_id  = kwargs.get("model_id")
            factor_id = kwargs.get("factor_id")
            lag       = kwargs.get("lag")

            query = (
                self.session.query(ModelFeatureModel)
                .filter(
                    ModelFeatureModel.model_id  == model_id,
                    ModelFeatureModel.factor_id == factor_id,
                )
            )
            if lag is not None:
                query = query.filter(ModelFeatureModel.lag == lag)
            existing = query.first()
            if existing:
                return self._to_entity(existing)

            orm = ModelFeatureModel(
                model_id=model_id,
                factor_id=factor_id,
                name=kwargs.get("name"),
                lag=lag,
                enabled=kwargs.get("enabled", True),
                feature_configuration=kwargs.get("feature_configuration"),
            )
            self.session.add(orm)
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error in ModelFeature._create_or_get: {e}")
            self.session.rollback()
            return None

    def get_by_id(self, id: int) -> Optional[ModelFeature]:
        orm = self.session.query(ModelFeatureModel).filter(ModelFeatureModel.id == id).one_or_none()
        return self._to_entity(orm)

    def get_by_model(self, model_id: int) -> List[ModelFeature]:
        rows = (
            self.session.query(ModelFeatureModel)
            .filter(ModelFeatureModel.model_id == model_id)
            .all()
        )
        return [self._to_entity(r) for r in rows]

    def get_enabled_by_model(self, model_id: int) -> List[ModelFeature]:
        rows = (
            self.session.query(ModelFeatureModel)
            .filter(
                ModelFeatureModel.model_id == model_id,
                ModelFeatureModel.enabled == True,
            )
            .all()
        )
        return [self._to_entity(r) for r in rows]

    def get_all(self) -> List[ModelFeature]:
        return [self._to_entity(o) for o in self.session.query(ModelFeatureModel).all()]

    def add(self, entity: ModelFeature) -> Optional[ModelFeature]:
        try:
            orm = self._to_model(entity)
            self.session.add(orm)
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error adding ModelFeature: {e}")
            self.session.rollback()
            return None

    def update(self, entity: ModelFeature) -> Optional[ModelFeature]:
        try:
            orm = (
                self.session.query(ModelFeatureModel)
                .filter(ModelFeatureModel.id == entity.id)
                .one_or_none()
            )
            if not orm:
                return None
            orm.name                  = entity.name
            orm.lag                   = entity.lag
            orm.enabled               = entity.enabled
            orm.feature_configuration = entity.get_feature_configuration_json()
            self.session.commit()
            return self._to_entity(orm)
        except Exception as e:
            print(f"Error updating ModelFeature {entity.id}: {e}")
            self.session.rollback()
            return None

    def delete(self, id: int) -> bool:
        try:
            orm = self.session.query(ModelFeatureModel).filter(ModelFeatureModel.id == id).one_or_none()
            if not orm:
                return False
            self.session.delete(orm)
            self.session.commit()
            return True
        except Exception as e:
            print(f"Error deleting ModelFeature {id}: {e}")
            self.session.rollback()
            return False
