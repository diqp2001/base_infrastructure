"""
src/domain/entities/ml/ml_model.py

MLModel domain entity — reusable machine learning model definition.
"""

from __future__ import annotations
import json
from datetime import datetime
from typing import Optional, Dict, Any
from src.domain.entities.entity import Entity


class MLModel(Entity):
    """
    Logical definition of a machine learning model: its type, hyperparameter
    configuration, and target factor.  Does NOT represent a single trained binary —
    use ModelTraining for individual training runs.

    Examples: LightGBM Stock Return Classifier, Random Forest Value Model.
    """

    MODEL_TYPES = {
        "lightgbm", "random_forest", "neural_network",
        "logistic_regression", "xgboost", "linear_regression",
        "gradient_boosting", "svm", "lstm", "transformer",
    }

    def __init__(
        self,
        name: str,
        model_type: str,
        id: Optional[int] = None,
        description: Optional[str] = None,
        target_factor_id: Optional[int] = None,
        configuration: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        super().__init__(id)
        self.name = name
        self.model_type = model_type
        self.description = description
        self.target_factor_id = target_factor_id
        self.configuration = configuration or {}
        self.created_at = created_at
        self.updated_at = updated_at

    def get_configuration_json(self) -> str:
        return json.dumps(self.configuration)

    def __repr__(self) -> str:
        return f"MLModel(id={self.id}, name='{self.name}', model_type='{self.model_type}')"
