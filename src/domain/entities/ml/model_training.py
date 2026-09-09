"""
src/domain/entities/ml/model_training.py

ModelTraining domain entity — one execution run of an MLModel.
"""

from __future__ import annotations
import json
from datetime import date, datetime
from typing import Optional, Dict, Any
from src.domain.entities.entity import Entity


class ModelTraining(Entity):
    """
    Represents a single training execution of an MLModel on a specific universe
    and date range.  Stores a configuration snapshot so historical runs can be
    reproduced even when the Model or its features later change.

    Status lifecycle: pending → running → completed | failed
    """

    STATUSES = {"pending", "running", "completed", "failed"}

    def __init__(
        self,
        model_id: int,
        id: Optional[int] = None,
        universe_id: Optional[int] = None,
        training_start_date: Optional[date] = None,
        training_end_date: Optional[date] = None,
        validation_start_date: Optional[date] = None,
        validation_end_date: Optional[date] = None,
        test_start_date: Optional[date] = None,
        test_end_date: Optional[date] = None,
        status: str = "pending",
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        training_configuration: Optional[Dict[str, Any]] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        super().__init__(id)
        self.model_id = model_id
        self.universe_id = universe_id
        self.training_start_date = training_start_date
        self.training_end_date = training_end_date
        self.validation_start_date = validation_start_date
        self.validation_end_date = validation_end_date
        self.test_start_date = test_start_date
        self.test_end_date = test_end_date
        self.status = status
        self.started_at = started_at
        self.completed_at = completed_at
        # Snapshot of model + feature config captured at training time for reproducibility
        self.training_configuration = training_configuration or {}
        self.created_at = created_at
        self.updated_at = updated_at

    def get_training_configuration_json(self) -> str:
        return json.dumps(self.training_configuration, default=str)

    def mark_running(self) -> None:
        self.status = "running"
        self.started_at = datetime.utcnow()

    def mark_completed(self) -> None:
        self.status = "completed"
        self.completed_at = datetime.utcnow()

    def mark_failed(self) -> None:
        self.status = "failed"
        self.completed_at = datetime.utcnow()

    def __repr__(self) -> str:
        return (
            f"ModelTraining(id={self.id}, model_id={self.model_id}, "
            f"status='{self.status}', train={self.training_start_date}..{self.training_end_date})"
        )
