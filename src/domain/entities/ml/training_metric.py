"""
src/domain/entities/ml/training_metric.py

TrainingMetric domain entity — a single metric produced during a ModelTraining run.
"""

from __future__ import annotations
import json
from datetime import date
from decimal import Decimal
from typing import Optional, Dict, Any
from src.domain.entities.entity import Entity


class TrainingMetric(Entity):
    """
    Stores one named metric (e.g. roc_auc=0.64) produced by a ModelTraining run.

    Metrics are extensible by name — no new columns are required for new metric types.
    dataset_type distinguishes train / validation / test splits.
    """

    DATASET_TYPES = {"training", "validation", "test"}

    def __init__(
        self,
        model_training_id: int,
        metric_name: str,
        metric_value: Decimal,
        dataset_type: str,
        id: Optional[int] = None,
        calculation_date: Optional[date] = None,
        configuration: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(id)
        self.model_training_id = model_training_id
        self.metric_name = metric_name
        self.metric_value = metric_value
        self.dataset_type = dataset_type
        self.calculation_date = calculation_date
        self.configuration = configuration or {}

    def get_configuration_json(self) -> str:
        return json.dumps(self.configuration)

    def __repr__(self) -> str:
        return (
            f"TrainingMetric(id={self.id}, training_id={self.model_training_id}, "
            f"name='{self.metric_name}', value={self.metric_value}, "
            f"dataset='{self.dataset_type}')"
        )
