"""
STMArtifactStore — PyTorch model persistence through the existing ML domain:

    MLModel        one per (model_type, universe)          ml_models
    ModelTraining  one per walk-forward window             model_trainings
    TrainingMetric validation / test metrics per window    training_metrics
    ModelFeature   one per input feature (ordered)         model_features
    ModelArtifact  the trained network                     model_artifacts

The weights file itself (``torch.save``) lives on disk; the ModelArtifact row
stores its location plus every piece of metadata needed to rebuild the exact
inference environment (asset order, feature order, lookback, scaler, model
hyper-parameters, training/validation/test periods, library versions).

Artifact selection never looks ahead: an artifact is eligible for date D only
if its validation period ended before D.
"""

from __future__ import annotations

import json
import logging
import os
import platform
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import bar_key
import torch

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMConfiguration,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_models import (
    SpatioTemporalMomentumNet,
)

logger = logging.getLogger(__name__)

_DEFAULT_ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "artifacts")

# MLModel.MODEL_TYPES vocabulary
_ML_MODEL_TYPE = {"tft": "transformer", "lstm": "lstm", "mlp": "neural_network",
                  "slp": "neural_network", "conv": "neural_network"}


@dataclass
class LoadedArtifact:
    model: SpatioTemporalMomentumNet
    metadata: Dict[str, Any]
    artifact_id: Optional[int] = None

    @property
    def assets(self) -> List[str]:
        return list(self.metadata["assets"])

    @property
    def asset_entity_ids(self) -> Dict[str, int]:
        return {k: int(v) for k, v in self.metadata.get("asset_entity_ids", {}).items()}

    @property
    def feature_names(self) -> List[str]:
        return list(self.metadata["feature_names"])

    @property
    def scaler(self) -> Optional[Dict[str, list]]:
        return self.metadata.get("scaler")

    @property
    def config(self) -> STMConfiguration:
        return STMConfiguration.from_dict(self.metadata["configuration"])


def _safe_date(d) -> Optional[str]:
    return None if d is None else pd.Timestamp(d).date().isoformat()


def build_artifact_metadata(config: STMConfiguration, assets: List[str], asset_entity_ids: Dict[str, int],
                            feature_names: List[str], split, scaler, universe_id: Optional[int],
                            train_result, history_start=None, valid_until=None) -> Dict[str, Any]:
    return {
        "model_type": config.model.model_type,
        "framework": "pytorch",
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "pandas_version": pd.__version__,
        "python_version": platform.python_version(),
        "universe_name": config.universe.name,
        "universe_id": universe_id,
        "assets": list(assets),
        "asset_entity_ids": {a: int(asset_entity_ids[a]) for a in assets if a in asset_entity_ids},
        "feature_names": list(feature_names),
        "lookback": config.model.lookback,
        "encoder_length": config.model.encoder_length if config.model.model_type == "tft" else None,
        "model_params": dict(config.model.params),
        "prediction_horizon": config.prediction_horizon,
        "scaler": scaler,
        # first close date of the panel used in training; inference recomputes
        # features from the same start so EWM statistics are identical
        "history_start": _safe_date(history_start),
        "training_end": _safe_date(split.train_end),
        "validation_start": _safe_date(split.start + pd.Timedelta(days=1)),
        "validation_end": _safe_date(split.val_end),
        "valid_from": _safe_date(split.val_end + pd.Timedelta(days=1)),
        "valid_until": _safe_date(valid_until if valid_until is not None else split.test_end),
        "best_epoch": train_result.best_epoch,
        "epochs_run": train_result.epochs_run,
        "best_val_sharpe": None if not np.isfinite(train_result.best_val_sharpe) else train_result.best_val_sharpe,
        "model_hash": config.model_hash(),
        "configuration": config.to_dict(),
    }


def rebuild_model(metadata: Dict[str, Any], state_dict) -> SpatioTemporalMomentumNet:
    model = SpatioTemporalMomentumNet(
        n_assets=len(metadata["assets"]),
        n_features=len(metadata["feature_names"]),
        lookback=int(metadata["lookback"]),
        model_type=metadata["model_type"],
        encoder_length=metadata.get("encoder_length"),
        model_params=metadata.get("model_params") or {},
    )
    model.load_state_dict(state_dict)
    model.eval()
    return model


def save_model_file(path: str, model: torch.nn.Module, metadata: Dict[str, Any]) -> str:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    torch.save({"state_dict": model.state_dict(), "metadata": metadata}, path)
    return path


def load_model_file(path: str) -> LoadedArtifact:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    return LoadedArtifact(model=rebuild_model(payload["metadata"], payload["state_dict"]),
                          metadata=payload["metadata"])


class STMArtifactStore:

    def __init__(self, factory, config: STMConfiguration):
        self.factory = factory
        self.config = config
        self.artifact_dir = config.artifact_dir or _DEFAULT_ARTIFACT_DIR

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def ml_model_name(self) -> str:
        return f"{self.config.ml_model_name_prefix}{self.config.model.model_type}_{self.config.universe.name}"

    def ensure_ml_model(self, target_factor_id: Optional[int] = None):
        from src.domain.entities.ml.ml_model import MLModel
        ml_model = self.factory.ml_model_local_repo._create_or_get(
            MLModel,
            self.ml_model_name(),
            model_type=_ML_MODEL_TYPE.get(self.config.model.model_type, "neural_network"),
            configuration=json.dumps(self.config.to_dict(), default=str),
            target_factor_id=target_factor_id,
            description="Spatio-Temporal Momentum (joint universe) — "
                        "port of KurochkinAlexey/SpatioTemporalMomentum",
        )
        if ml_model is None:
            raise RuntimeError("MLModel creation failed")
        return ml_model

    def ensure_model_features(self, ml_model, feature_factor_ids: Dict[str, int]) -> None:
        from src.domain.entities.ml.model_feature import ModelFeature
        repo = self.factory.model_feature_local_repo
        for idx, name in enumerate(self.config.features.feature_names()):
            if feature_factor_ids.get(name) is None:
                raise ValueError(f"No factor id for model feature '{name}'")
            repo._create_or_get(
                ModelFeature,
                name,
                model_id=ml_model.id,
                factor_id=feature_factor_ids.get(name),
                name=name,
                lag=0,
                enabled=True,
                feature_configuration=json.dumps({"index": idx, "factor_name": f"{self.config.feature_factor_prefix}{name}"}),
            )

    def start_training(self, ml_model, universe_id: Optional[int], split, first_train_date=None):
        from src.domain.entities.ml.model_training import ModelTraining
        training = self.factory.model_training_local_repo.add(ModelTraining(
            model_id=ml_model.id,
            universe_id=universe_id,
            training_start_date=pd.Timestamp(first_train_date).date() if first_train_date is not None else None,
            training_end_date=pd.Timestamp(split.train_end).date(),
            validation_start_date=(split.start + pd.Timedelta(days=1)).date(),
            validation_end_date=pd.Timestamp(split.val_end).date(),
            test_start_date=(split.val_end + pd.Timedelta(days=1)).date(),
            test_end_date=pd.Timestamp(split.test_end).date(),
            status="pending",
            training_configuration=self.config.to_dict(),
        ))
        if training is None:
            raise RuntimeError("ModelTraining creation failed")
        training.mark_running()
        self.factory.model_training_local_repo.update(training)
        return training

    def finish_training(self, training, ok: bool) -> None:
        training.mark_completed() if ok else training.mark_failed()
        self.factory.model_training_local_repo.update(training)

    def record_metrics(self, training, metrics: Dict[str, Dict[str, float]], calculation_date=None) -> int:
        """metrics = {dataset_type: {metric_name: value}}; non-finite values are skipped."""
        from src.domain.entities.ml.training_metric import TrainingMetric
        repo = self.factory.training_metric_local_repo
        n = 0
        for dataset_type, values in metrics.items():
            for name, value in values.items():
                if value is None or not np.isfinite(float(value)):
                    continue
                repo._create_or_get(
                    TrainingMetric, name,
                    model_training_id=training.id,
                    metric_name=name,
                    metric_value=Decimal(str(round(float(value), 8))),
                    dataset_type=dataset_type,
                    calculation_date=pd.Timestamp(calculation_date).date() if calculation_date is not None else None,
                )
                n += 1
        return n

    def save_artifact(self, training, model: torch.nn.Module, metadata: Dict[str, Any]):
        from src.domain.entities.ml.model_artifact import ModelArtifact
        filename = (f"{self.ml_model_name()}_{metadata['valid_from']}_{metadata['model_hash'][:12]}"
                    f"_t{training.id}.pt")
        path = save_model_file(os.path.join(self.artifact_dir, filename), model, metadata)
        artifact = self.factory.model_artifact_local_repo._create_or_get(
            ModelArtifact,
            filename,
            model_training_id=training.id,
            artifact_type="trained_model",
            location=path,
            format="pt",
            artifact_metadata=json.dumps(metadata, default=str),
        )
        if artifact is None:
            raise RuntimeError("ModelArtifact creation failed")
        return artifact

    # ------------------------------------------------------------------
    # Selection / loading
    # ------------------------------------------------------------------

    def list_artifacts(self) -> List[Tuple[Any, Dict[str, Any]]]:
        """
        Usable trained-model artifacts of this configuration.

        An artifact counts only if its training completed, its model hash
        matches AND its weights file still exists on disk: a DB row whose file
        was deleted is ignored, so the trading cycle retrains instead of
        selecting a model it cannot load.
        """
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
                    except Exception:
                        continue
                if not (isinstance(meta, dict) and meta.get("model_hash") == self.config.model_hash()):
                    continue
                if not artifact.location or not os.path.exists(artifact.location):
                    logger.warning(f"Artifact {artifact.id} ignored: weights file missing ({artifact.location})")
                    continue
                out.append((artifact, meta))
        return out

    def select(self, as_of) -> Optional[Tuple[Any, Dict[str, Any]]]:
        """
        'covering_test_window': artifact whose test window contains as_of
                                (the walk-forward out-of-sample model).
        'latest_before'       : most recent artifact whose validation ended before as_of.
        Both require validation_end < as_of, so no model is used on dates it saw.
        """
        d = bar_key(as_of, self.config.bar_minutes)
        candidates = [(a, m) for a, m in self.list_artifacts()
                      if m.get("validation_end") and pd.Timestamp(m["validation_end"]) < d]
        if not candidates:
            return None
        if self.config.artifact_selection == "covering_test_window":
            covering = [(a, m) for a, m in candidates
                        if pd.Timestamp(m["valid_from"]) <= d <= pd.Timestamp(m["valid_until"])]
            if covering:
                return max(covering, key=lambda am: pd.Timestamp(am[1]["validation_end"]))
            return None
        return max(candidates, key=lambda am: pd.Timestamp(am[1]["validation_end"]))

    def load(self, artifact) -> LoadedArtifact:
        loaded = load_model_file(artifact.location)
        loaded.artifact_id = artifact.id
        return loaded
