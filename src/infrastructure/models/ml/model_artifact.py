"""
src/infrastructure/models/ml/model_artifact.py

SQLAlchemy ORM model for ModelArtifact.
Table: model_artifacts
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from src.infrastructure.models import ModelBase as Base


class ModelArtifactModel(Base):
    __tablename__ = "model_artifacts"

    id                = Column(Integer, primary_key=True, autoincrement=True)
    model_training_id = Column(Integer, ForeignKey("model_trainings.id"), nullable=False, index=True)
    artifact_type     = Column(String(100), nullable=False)
    name              = Column(String(255), nullable=False)
    location          = Column(Text, nullable=False)     # file path / S3 URI / Azure Blob URI
    format            = Column(String(50), nullable=True)
    artifact_metadata = Column(Text, nullable=True)      # JSON string
    created_at        = Column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<ModelArtifactModel(id={self.id}, training_id={self.model_training_id}, "
            f"type={self.artifact_type}, name={self.name})>"
        )
