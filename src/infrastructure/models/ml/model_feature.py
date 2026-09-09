"""
src/infrastructure/models/ml/model_feature.py

SQLAlchemy ORM model for ModelFeature.
Table: model_features
"""

from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from src.infrastructure.models import ModelBase as Base


class ModelFeatureModel(Base):
    __tablename__ = "model_features"

    id                    = Column(Integer, primary_key=True, autoincrement=True)
    model_id              = Column(Integer, ForeignKey("ml_models.id"), nullable=False, index=True)
    factor_id             = Column(Integer, ForeignKey("factors.id"), nullable=False, index=True)
    name                  = Column(String(255), nullable=True)
    lag                   = Column(Integer, nullable=True)     # lag in calendar days
    enabled               = Column(Boolean, nullable=False, default=True)
    feature_configuration = Column(Text, nullable=True)        # JSON string

    def __repr__(self) -> str:
        return (
            f"<ModelFeatureModel(id={self.id}, model_id={self.model_id}, "
            f"factor_id={self.factor_id}, lag={self.lag})>"
        )
