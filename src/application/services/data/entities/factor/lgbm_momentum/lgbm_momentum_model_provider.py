"""
LGBMMomentumModelProvider — model lifecycle manager for the cross-sectional
quintile rank momentum factor.

Handles: regime fingerprinting, artifact lookup, auto-training, prediction.
Injected into CompanyShareLGBMCSQuintileRankMomentumFactor by the repository.
"""

import hashlib
import json
import os
import pickle
from datetime import date
from typing import Any, Dict, Optional

from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_configuration import (
    LGBMMomentumModelConfiguration,
)
from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_feature_definition import (
    LGBMMomentumFeatureDefinition,
)


class LGBMMomentumModelProvider:
    # Class-level cache: regime_key → fitted model
    _model_cache: Dict[str, Any] = {}

    def __init__(
        self,
        factory=None,
        config: Optional[LGBMMomentumModelConfiguration] = None,
        feature_def: Optional[LGBMMomentumFeatureDefinition] = None,
        history_service=None,
    ):
        self.factory = factory
        self.config = config or LGBMMomentumModelConfiguration()
        self.feature_def = feature_def or LGBMMomentumFeatureDefinition()
        self.history_service = history_service

    # ------------------------------------------------------------------
    # Primary interface called from calculate()
    # ------------------------------------------------------------------

    def predict(self, dependencies: dict, entity, target_date) -> Optional[float]:
        """Return predicted quintile rank (1.0–5.0) or None."""
        features = self.feature_def.extract(dependencies, entity, target_date)
        if features is None:
            return None

        ref_date = target_date.date() if hasattr(target_date, "date") else target_date
        model = self._get_or_train_model(ref_date)
        if model is None:
            return None

        try:
            import numpy as np
            X = np.array([features])
            result = float(model.predict(X)[0])
            # Clamp to valid quintile range
            return max(1.0, min(result, float(self.config.n_quintiles)))
        except Exception as e:
            print(f"LGBMMomentumModelProvider.predict error: {e}")
            return None

    # ------------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------------

    def _get_or_train_model(self, target_date: date) -> Optional[Any]:
        regime_key = self._compute_regime_key(target_date)

        if regime_key in LGBMMomentumModelProvider._model_cache:
            return LGBMMomentumModelProvider._model_cache[regime_key]

        model = self._load_artifact(regime_key, target_date)
        if model is not None:
            LGBMMomentumModelProvider._model_cache[regime_key] = model
            return model

        model = self._train_and_cache(regime_key, target_date)
        return model

    def _compute_regime_key(self, target_date: date) -> str:
        universe_fp = self._get_universe_fingerprint(target_date)
        combined = universe_fp + self.feature_def.hash() + self.config.hash()
        return hashlib.sha256(combined.encode()).hexdigest()

    def _get_universe_fingerprint(self, target_date: date) -> str:
        if self.factory is None:
            return "no_factory"
        try:
            from src.domain.entities.universe.universe import Universe
            from src.domain.entities.universe.universe_constituent import UniverseConstituent

            universe_repo = self.factory.investment_universe_local_repo
            constituent_repo = self.factory.universe_constituent_local_repo

            universe = universe_repo.get_by_name(self.config.UNIVERSE_NAME)
            if universe is not None and universe.id is not None:
                constituents = constituent_repo.get_active_by_universe(universe.id, target_date)
                share_ids = sorted(
                    str(c.entity_id)
                    for c in constituents
                    if isinstance(c, UniverseConstituent)
                )
                if share_ids:
                    return hashlib.sha256(",".join(share_ids).encode()).hexdigest()

            return "no_universe_yet"
        except Exception:
            return "no_universe_yet"

    # ------------------------------------------------------------------
    # Artifact lookup
    # ------------------------------------------------------------------

    def _load_artifact(self, regime_key: str, target_date: date) -> Optional[Any]:
        if self.factory is None:
            return None
        try:
            from src.domain.entities.ml.ml_model import MLModel
            from src.domain.entities.ml.model_training import ModelTraining
            from src.domain.entities.ml.model_artifact import ModelArtifact

            ml_model_repo = self.factory.ml_model_local_repo
            training_repo = self.factory.model_training_local_repo
            artifact_repo = self.factory.model_artifact_local_repo

            all_models = ml_model_repo.get_all()
            candidate_ids = [
                m.id for m in all_models
                if isinstance(m, MLModel) and m.name and m.name.startswith(self.config.ML_MODEL_NAME_PREFIX)
            ]
            if not candidate_ids:
                return None

            for model_id in candidate_ids:
                for training in training_repo.get_by_model(model_id):
                    if not isinstance(training, ModelTraining):
                        continue
                    for artifact in artifact_repo.get_by_training_and_type(training.id, "trained_model"):
                        if not isinstance(artifact, ModelArtifact):
                            continue
                        if self._artifact_matches(artifact, regime_key, target_date):
                            model = self._deserialize(artifact.location)
                            if model is not None:
                                return model
        except Exception as e:
            print(f"LGBMMomentumModelProvider._load_artifact error: {e}")
        return None

    def _artifact_matches(self, artifact, regime_key: str, target_date: date) -> bool:
        meta = artifact.artifact_metadata or {}
        if not isinstance(meta, dict):
            try:
                meta = json.loads(meta)
            except Exception:
                return False

        stored_regime = hashlib.sha256(
            (meta.get("universe_fingerprint", "") +
             meta.get("feature_definition_hash", "") +
             meta.get("model_configuration_hash", "")).encode()
        ).hexdigest()
        if stored_regime != regime_key:
            return False

        try:
            valid_from = date.fromisoformat(meta["valid_from"])
            valid_until = date.fromisoformat(meta["valid_until"])
        except (KeyError, ValueError):
            return False
        return valid_from <= target_date <= valid_until

    @staticmethod
    def _deserialize(location: str) -> Optional[Any]:
        if not location or not os.path.exists(location):
            return None
        try:
            with open(location, "rb") as f:
                return pickle.load(f)
        except Exception as e:
            print(f"LGBMMomentumModelProvider: failed to deserialize {location}: {e}")
            return None

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def _train_and_cache(self, regime_key: str, target_date: date) -> Optional[Any]:
        from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_model_trainer import (
            LGBMMomentumModelTrainer,
        )
        universe_fp = self._get_universe_fingerprint(target_date)
        trainer = LGBMMomentumModelTrainer(
            factory=self.factory,
            config=self.config,
            feature_def=self.feature_def,
            history_service=self.history_service,
        )
        model = trainer.train_and_persist(
            target_date=target_date,
            universe_fingerprint=universe_fp,
        )
        if model is not None:
            LGBMMomentumModelProvider._model_cache[regime_key] = model
        return model

    @classmethod
    def clear_cache(cls) -> None:
        cls._model_cache.clear()
