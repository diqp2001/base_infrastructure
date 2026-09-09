"""
src/domain/entities/ml/model_feature.py

ModelFeature domain entity — an input feature referencing an existing Factor.
"""

from __future__ import annotations
import json
from typing import Optional, Dict, Any
from src.domain.entities.entity import Entity


class ModelFeature(Entity):
    """
    Links a Factor to an MLModel as an input feature.

    Feature-specific transformations (lag, normalization, winsorisation) live here,
    NOT on the Factor itself.  The same Factor can appear multiple times in the same
    model with different lags or configurations.
    """

    def __init__(
        self,
        model_id: int,
        factor_id: int,
        id: Optional[int] = None,
        name: Optional[str] = None,
        lag: Optional[int] = None,
        enabled: bool = True,
        feature_configuration: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(id)
        self.model_id = model_id
        self.factor_id = factor_id
        self.name = name
        self.lag = lag                                      # lag in days, avoids look-ahead bias
        self.enabled = enabled
        self.feature_configuration = feature_configuration or {}

    def get_feature_configuration_json(self) -> str:
        return json.dumps(self.feature_configuration)

    def __repr__(self) -> str:
        return (
            f"ModelFeature(id={self.id}, model_id={self.model_id}, "
            f"factor_id={self.factor_id}, lag={self.lag})"
        )
