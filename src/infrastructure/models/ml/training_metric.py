"""
src/infrastructure/models/ml/training_metric.py

SQLAlchemy ORM model for TrainingMetric.
Table: training_metrics
"""

from sqlalchemy import Column, Integer, String, Text, Date, Numeric, ForeignKey
from src.infrastructure.models import ModelBase as Base


class TrainingMetricModel(Base):
    __tablename__ = "training_metrics"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    model_training_id = Column(Integer, ForeignKey("model_trainings.id"), nullable=False, index=True)
    metric_name       = Column(String(255), nullable=False)
    metric_value      = Column(Numeric(20, 10), nullable=False)
    dataset_type      = Column(String(50), nullable=False)   # training | validation | test
    calculation_date  = Column(Date, nullable=True)
    configuration     = Column(Text, nullable=True)          # JSON string

    def __repr__(self) -> str:
        return (
            f"<TrainingMetricModel(id={self.id}, training_id={self.model_training_id}, "
            f"name={self.metric_name}, value={self.metric_value}, "
            f"dataset={self.dataset_type})>"
        )
