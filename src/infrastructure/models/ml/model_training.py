"""
src/infrastructure/models/ml/model_training.py

SQLAlchemy ORM model for ModelTraining.
Table: model_trainings
"""

from sqlalchemy import Column, Integer, String, Text, Date, DateTime, ForeignKey
from src.infrastructure.models import ModelBase as Base


class ModelTrainingModel(Base):
    __tablename__ = "model_trainings"

    id                     = Column(Integer, primary_key=True, autoincrement=True)
    model_id               = Column(Integer, ForeignKey("ml_models.id"), nullable=False, index=True)
    universe_id            = Column(Integer, ForeignKey("investment_universes.id"), nullable=True, index=True)
    training_start_date    = Column(Date, nullable=True)
    training_end_date      = Column(Date, nullable=True)
    validation_start_date  = Column(Date, nullable=True)
    validation_end_date    = Column(Date, nullable=True)
    test_start_date        = Column(Date, nullable=True)
    test_end_date          = Column(Date, nullable=True)
    status                 = Column(String(50), nullable=False, default="pending")
    started_at             = Column(DateTime, nullable=True)
    completed_at           = Column(DateTime, nullable=True)
    training_configuration = Column(Text, nullable=True)       # JSON snapshot at training time
    created_at             = Column(DateTime, nullable=True)
    updated_at             = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ModelTrainingModel(id={self.id}, model_id={self.model_id}, "
            f"status={self.status})>"
        )
