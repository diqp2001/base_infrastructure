"""
src/infrastructure/models/ml/ml_model.py

SQLAlchemy ORM model for MLModel.
Table: ml_models  (separate from backtests.models)
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from src.infrastructure.models import ModelBase as Base


class MLModelModel(Base):
    __tablename__ = "ml_models"

    id               = Column(Integer, primary_key=True, autoincrement=True)
    name             = Column(String(255), nullable=False)
    description      = Column(Text, nullable=True)
    model_type       = Column(String(100), nullable=False)
    target_factor_id = Column(Integer, ForeignKey("factors.id"), nullable=True)
    configuration    = Column(Text, nullable=True)     # JSON string
    created_at       = Column(DateTime, nullable=True)
    updated_at       = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<MLModelModel(id={self.id}, name={self.name}, model_type={self.model_type})>"
