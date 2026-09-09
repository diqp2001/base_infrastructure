"""
src/domain/entities/ml/model_artifact.py

ModelArtifact domain entity — metadata for an artifact produced by a ModelTraining.
"""

from __future__ import annotations
import json
from datetime import datetime
from typing import Optional, Dict, Any
from src.domain.entities.entity import Entity


class ModelArtifact(Entity):
    """
    Stores the metadata for an artifact produced during a model training run.

    The artifact itself (file, S3 object, Azure Blob) is NOT stored in SQL —
    only the reference (location) and metadata are stored here.  This separates
    artifact metadata from storage mechanism.

    Supported artifact_type values:
        trained_model, feature_importance, predictions, shap_values,
        training_log, cross_validation_results, parameters
    """

    ARTIFACT_TYPES = {
        "trained_model", "feature_importance", "predictions",
        "shap_values", "training_log", "cross_validation_results", "parameters",
    }

    FORMAT_TYPES = {"pickle", "joblib", "json", "csv", "parquet", "h5", "txt", "onnx"}

    def __init__(
        self,
        model_training_id: int,
        artifact_type: str,
        name: str,
        location: str,
        id: Optional[int] = None,
        format: Optional[str] = None,
        artifact_metadata: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
    ):
        super().__init__(id)
        self.model_training_id = model_training_id
        self.artifact_type = artifact_type
        self.name = name
        self.location = location    # local path, S3 URI, Azure Blob URI, etc.
        self.format = format
        self.artifact_metadata = artifact_metadata or {}
        self.created_at = created_at

    def get_artifact_metadata_json(self) -> str:
        return json.dumps(self.artifact_metadata)

    def __repr__(self) -> str:
        return (
            f"ModelArtifact(id={self.id}, training_id={self.model_training_id}, "
            f"type='{self.artifact_type}', name='{self.name}')"
        )
