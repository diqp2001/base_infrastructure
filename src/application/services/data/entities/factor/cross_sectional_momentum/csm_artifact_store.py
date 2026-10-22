"""
CSMArtifactStore — LightGBM model persistence through the existing ML domain (same records as STM):

    MLModel        one per (configuration prefix, universe)        ml_models
    ModelTraining  one per retraining                              model_trainings
    TrainingMetric the Optuna cross-validation result              training_metrics
    ModelArtifact  the trained booster (text file on disk)         model_artifacts

The ModelArtifact metadata holds everything needed to score and to report: selected features, LightGBM
parameters, training window, the Optuna study summary (trial values, feature selection frequency,
hyper-parameter importances) and the gain importance of the final model.

Selection never looks ahead: an artifact trained as of session S (labels known at S only) is usable from S on.
"""

from __future__ import annotations

import json
import logging
import os
import platform
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.cross_sectional_momentum.csm_configuration import (
    CSMConfiguration,
)
from src.application.services.data.entities.factor.cross_sectional_momentum.csm_model import FittedModel

logger = logging.getLogger(__name__)

_DEFAULT_ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "artifacts")


@dataclass
class LoadedCSMModel:
    booster: Any
    metadata: Dict[str, Any]
    artifact_id: Optional[int] = None

    @property
    def features(self) -> List[str]:
        return list(self.metadata["features"])

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        return self.booster.predict(X[self.features].to_numpy(dtype=float))

    def contributions(self, X: pd.DataFrame) -> np.ndarray:
        return self.booster.predict(X[self.features].to_numpy(dtype=float), pred_contrib=True)[:, :-1]


def _d(ts) -> Optional[str]:
    return None if ts is None else pd.Timestamp(ts).date().isoformat()


def build_metadata(config: CSMConfiguration, model: FittedModel, trained_as_of, universe_id: Optional[int],
                   assets: List[str]) -> Dict[str, Any]:
    import lightgbm
    import optuna
    s = model.study
    return {
        "framework": "lightgbm",
        "lightgbm_version": lightgbm.__version__,
        "optuna_version": optuna.__version__,
        "python_version": platform.python_version(),
        "universe_name": config.universe.name,
        "universe_id": universe_id,
        "assets": list(assets),
        "features": list(model.features),
        "candidate_features": config.features.feature_names(),
        "params": dict(model.params),
        "trained_as_of": _d(trained_as_of),
        "train_start": _d(model.train_start),
        "train_end": _d(model.train_end),
        "n_train_rows": int(model.n_train_rows),
        "label_horizon": config.label.horizon,
        "metric": config.optimization.metric,
        "cv_best_value": s.best_value,
        "cv_fold_values": list(s.fold_values),
        "trial_values": list(s.trial_values),
        "n_trials": s.n_trials,
        "n_pruned": s.n_pruned,
        "selection_frequency": dict(s.selection_frequency),
        "param_importance": dict(s.param_importance),
        "gain_importance": model.gain_importance(),
        "model_hash": config.model_hash(),
        "configuration": config.to_dict(),
    }


class CSMArtifactStore:

    def __init__(self, factory, config: CSMConfiguration):
        self.factory = factory
        self.config = config
        self.artifact_dir = config.artifact_dir or _DEFAULT_ARTIFACT_DIR

    def ml_model_name(self) -> str:
        return f"{self.config.ml_model_name_prefix}lightgbm_{self.config.universe.name}"

    def ensure_ml_model(self):
        from src.domain.entities.ml.ml_model import MLModel
        ml_model = self.factory.ml_model_local_repo._create_or_get(
            MLModel,
            self.ml_model_name(),
            model_type="lightgbm",
            configuration=json.dumps(self.config.to_dict(), default=str),
            description="Cross-sectional momentum classifier (LightGBM, features + hyper-parameters by Optuna TPE)",
        )
        if ml_model is None:
            raise RuntimeError("MLModel creation failed")
        return ml_model

    def save(self, model: FittedModel, trained_as_of, universe_id: Optional[int], assets: List[str]):
        """Register the training (+ CV metrics) and the artifact; returns (artifact, metadata)."""
        from src.domain.entities.ml.model_artifact import ModelArtifact
        from src.domain.entities.ml.model_training import ModelTraining
        from src.domain.entities.ml.training_metric import TrainingMetric
        ml_model = self.ensure_ml_model()
        as_of = pd.Timestamp(trained_as_of)
        training = self.factory.model_training_local_repo.add(ModelTraining(
            model_id=ml_model.id,
            universe_id=universe_id,
            training_start_date=model.train_start.date(),
            training_end_date=model.train_end.date(),
            validation_start_date=model.train_start.date(),     # walk-forward folds inside the window
            validation_end_date=model.train_end.date(),
            test_start_date=as_of.date(),
            test_end_date=as_of.date(),
            status="pending",
            training_configuration=self.config.to_dict(),
        ))
        if training is None:
            raise RuntimeError("ModelTraining creation failed")
        training.mark_running()
        self.factory.model_training_local_repo.update(training)

        metadata = build_metadata(self.config, model, as_of, universe_id, assets)
        os.makedirs(self.artifact_dir, exist_ok=True)
        filename = f"{self.ml_model_name()}_{metadata['trained_as_of']}_{metadata['model_hash'][:12]}_t{training.id}.txt"
        path = os.path.join(self.artifact_dir, filename)
        model.booster.save_model(path)
        with open(path + ".json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, default=str)
        metrics = {f"cv_{self.config.optimization.metric}": model.study.best_value}
        metrics.update({f"cv_{self.config.optimization.metric}_fold{i}": v
                        for i, v in enumerate(model.study.fold_values)})
        for name, value in metrics.items():
            if value is None or not np.isfinite(float(value)):
                continue
            self.factory.training_metric_local_repo._create_or_get(
                TrainingMetric, name, model_training_id=training.id, metric_name=name,
                metric_value=Decimal(str(round(float(value), 8))), dataset_type="validation",
                calculation_date=as_of.date())
        artifact = self.factory.model_artifact_local_repo._create_or_get(
            ModelArtifact, filename, model_training_id=training.id, artifact_type="trained_model",
            location=path, format="txt", artifact_metadata=json.dumps(metadata, default=str))
        if artifact is None:
            training.mark_failed()
            self.factory.model_training_local_repo.update(training)
            raise RuntimeError("ModelArtifact creation failed")
        training.mark_completed()
        self.factory.model_training_local_repo.update(training)
        return artifact, metadata

    def list_artifacts(self) -> List[Tuple[Any, Dict[str, Any]]]:
        """Completed artifacts of THIS configuration (model hash) whose model file still exists."""
        from src.domain.entities.ml.ml_model import MLModel
        ml_model = self.factory.ml_model_local_repo.get_by_name(self.ml_model_name())
        if not isinstance(ml_model, MLModel):
            return []
        out = []
        for training in self.factory.model_training_local_repo.get_by_model(ml_model.id):
            if getattr(training, "status", None) != "completed":
                continue
            for artifact in self.factory.model_artifact_local_repo.get_by_training_and_type(training.id, "trained_model"):
                meta = artifact.artifact_metadata
                if isinstance(meta, str):
                    try:
                        meta = json.loads(meta)
                    except ValueError:
                        continue
                if not (isinstance(meta, dict) and meta.get("model_hash") == self.config.model_hash()):
                    continue
                if not artifact.location or not os.path.exists(artifact.location):
                    logger.warning(f"Artifact {artifact.id} ignored: model file missing ({artifact.location})")
                    continue
                out.append((artifact, meta))
        return out

    def select(self, session) -> Optional[Tuple[Any, Dict[str, Any]]]:
        """Most recent artifact trained as of a session <= ``session``."""
        d = pd.Timestamp(session).normalize()
        usable = [(a, m) for a, m in self.list_artifacts() if pd.Timestamp(m["trained_as_of"]) <= d]
        return max(usable, key=lambda am: (pd.Timestamp(am[1]["trained_as_of"]), am[0].id)) if usable else None

    def load(self, artifact) -> LoadedCSMModel:
        import lightgbm as lgb
        meta = artifact.artifact_metadata
        meta = json.loads(meta) if isinstance(meta, str) else meta
        return LoadedCSMModel(booster=lgb.Booster(model_file=artifact.location), metadata=meta,
                              artifact_id=artifact.id)
