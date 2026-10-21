"""
ImpliedVolMlModelProvider — regime-aware ML model lifecycle manager.

Responsibilities
----------------
* Compute the regime key = SHA-256(universe_fp + feature_hash + config_hash).
* Serve a cached model when the regime matches; otherwise load from a valid
  DB artifact or trigger a full training run.
* Expose a `predict` method that accepts the same dependency dict that Branch-A
  `calculate()` receives.

Domain layer integration
------------------------
* Universe fingerprint: resolved via the InvestmentUniverse + UniverseConstituent
  domain repos (Universe / UniverseConstituent entities).  Falls back to a raw
  FactorValueModel scan only when no named universe exists yet.
* Artifact lookup: resolved via MLModel → ModelTraining → ModelArtifact domain
  chain (MLModel, ModelTraining, ModelArtifact entities).

Model cache
-----------
`_model_cache` is a *class-level* dict so the model survives across multiple
`calculate()` calls within the same Python process — batch efficiency without
threading risk (GIL-safe for dict reads).
"""

import hashlib
import json
import os
import logging
import pickle
from datetime import date
from typing import Any, Dict, Optional

from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_model_configuration import (
    ImpliedVolMlModelConfiguration,
)
from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_feature_definition import (
    ImpliedVolMlFeatureDefinition,
)



logger = logging.getLogger(__name__)


class ImpliedVolMlModelProvider:
    # Class-level cache: regime_key → fitted model object
    _model_cache: Dict[str, Any] = {}

    def __init__(
        self,
        factory=None,
        config: Optional[ImpliedVolMlModelConfiguration] = None,
        feature_def: Optional[ImpliedVolMlFeatureDefinition] = None,
        history_service=None,
    ):
        self.factory = factory
        self.config = config or ImpliedVolMlModelConfiguration()
        self.feature_def = feature_def or ImpliedVolMlFeatureDefinition()
        self.history_service = history_service

    # ------------------------------------------------------------------
    # Primary interface called from calculate()
    # ------------------------------------------------------------------

    def predict(
        self,
        dependencies: dict,
        entity,
        target_date,
    ) -> Optional[float]:
        """
        Return ML-predicted implied vol for (entity, target_date).

        Returns None if features cannot be extracted or no model is available.
        """
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
            # Clamp to reasonable IV range [0.001, 20]
            return max(0.001, min(result, 20.0))
        except Exception as e:
            logger.error(f"ImpliedVolMlModelProvider.predict failed for {entity} at {target_date}: {e}")
            return None

    # ------------------------------------------------------------------
    # Model lifecycle
    # ------------------------------------------------------------------

    def _get_or_train_model(self, target_date: date) -> Optional[Any]:
        regime_key = self._compute_regime_key(target_date)

        # 1. In-memory cache hit
        if regime_key in ImpliedVolMlModelProvider._model_cache:
            return ImpliedVolMlModelProvider._model_cache[regime_key]

        # 2. Try loading a valid persisted artifact via domain layer
        model = self._load_artifact(regime_key, target_date)
        if model is not None:
            ImpliedVolMlModelProvider._model_cache[regime_key] = model
            return model

        # 3. Train fresh model (auto-training)
        model = self._train_and_cache(regime_key, target_date)
        return model

    def _compute_regime_key(self, target_date: date) -> str:
        universe_fp = self._get_universe_fingerprint(target_date)
        combined = universe_fp + self.feature_def.hash() + self.config.hash()
        return hashlib.sha256(combined.encode()).hexdigest()

    # ------------------------------------------------------------------
    # Universe fingerprint — uses Universe / UniverseConstituent domain entities
    # ------------------------------------------------------------------

    def _get_universe_fingerprint(self, target_date: date) -> str:
        """
        SHA-256 of sorted entity IDs of active CompanyShareOption constituents.

        Resolution:
        1. Universe named _UNIVERSE_NAME — seeded by the trainer on the first training
           run; reliable from the second call onward.
        2. "no_universe_yet" sentinel — returned before the first training run.
           Guarantees training will be triggered and the named universe will be seeded.

        Note: a raw DB scan across all factor_values is intentionally avoided — the DB
        can contain IV factor values from other projects or backtests, which would
        produce a fingerprint that does not match the artifact actually trained on this
        project's universe.
        """
        if self.factory is None:
            return "no_factory"
        try:
            from src.domain.entities.universe.universe import Universe
            from src.domain.entities.universe.universe_constituent import UniverseConstituent

            universe_repo = self.factory.investment_universe_local_repo
            constituent_repo = self.factory.universe_constituent_local_repo

            universe: Optional[Universe] = universe_repo.get_by_name(self.config.UNIVERSE_NAME)
            if universe is not None and universe.id is not None:
                constituents = constituent_repo.get_active_by_universe(
                    universe.id, target_date
                )
                option_ids = sorted(
                    str(c.entity_id)
                    for c in constituents
                    if isinstance(c, UniverseConstituent)
                )
                if option_ids:
                    return hashlib.sha256(",".join(option_ids).encode()).hexdigest()

            # Named universe not seeded yet — first call before any training.
            return "no_universe_yet"

        except Exception:
            return "no_universe_yet"

    # ------------------------------------------------------------------
    # Artifact lookup — uses MLModel → ModelTraining → ModelArtifact domain chain
    # ------------------------------------------------------------------

    def _load_artifact(self, regime_key: str, target_date: date) -> Optional[Any]:
        """
        Walk the MLModel → ModelTraining → ModelArtifact domain chain to find a
        valid artifact for this regime, then deserialize it.
        """
        if self.factory is None:
            return None
        try:
            from src.domain.entities.ml.ml_model import MLModel
            from src.domain.entities.ml.model_training import ModelTraining
            from src.domain.entities.ml.model_artifact import ModelArtifact

            ml_model_repo = self.factory.ml_model_local_repo
            training_repo = self.factory.model_training_local_repo
            artifact_repo = self.factory.model_artifact_local_repo

            # Find all MLModel rows whose name starts with our prefix
            all_models = ml_model_repo.get_all()
            candidate_model_ids = [
                m.id for m in all_models
                if isinstance(m, MLModel) and m.name and m.name.startswith(self.config.ML_MODEL_NAME_PREFIX)
            ]
            if not candidate_model_ids:
                return None

            for model_id in candidate_model_ids:
                trainings = training_repo.get_by_model(model_id)
                for training in trainings:
                    if not isinstance(training, ModelTraining):
                        continue
                    artifacts = artifact_repo.get_by_training_and_type(
                        training.id, "trained_model"
                    )
                    for artifact in artifacts:
                        if not isinstance(artifact, ModelArtifact):
                            continue
                        if self._artifact_matches(artifact, regime_key, target_date):
                            model = self._deserialize(artifact.location)
                            if model is not None:
                                return model
        except Exception as e:
            logger.error(f"ImpliedVolMlModelProvider: artifact lookup failed ({e}) — training a new model")
        return None

    def _artifact_matches(self, artifact, regime_key: str, target_date: date) -> bool:
        """Check fingerprints + validity window against a ModelArtifact domain entity."""
        meta = artifact.artifact_metadata or {}
        if not isinstance(meta, dict):
            try:
                meta = json.loads(meta)
            except Exception:
                return False

        # Regime check: recompute combined fingerprint from stored hashes
        stored_universe = meta.get("universe_fingerprint", "")
        stored_feature = meta.get("feature_definition_hash", "")
        stored_config = meta.get("model_configuration_hash", "")
        stored_regime = hashlib.sha256(
            (stored_universe + stored_feature + stored_config).encode()
        ).hexdigest()
        if stored_regime != regime_key:
            return False

        # Validity window
        valid_from_str = meta.get("valid_from")
        valid_until_str = meta.get("valid_until")
        if valid_from_str is None or valid_until_str is None:
            return False
        try:
            valid_from = date.fromisoformat(valid_from_str)
            valid_until = date.fromisoformat(valid_until_str)
        except ValueError:
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
            logger.error(f"ImpliedVolMlModelProvider: artifact {location} is unreadable ({type(e).__name__}: {e}) — "
                         f"not used")
            return None

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def _train_and_cache(self, regime_key: str, target_date: date) -> Optional[Any]:
        from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_model_trainer import (
            ImpliedVolMlModelTrainer,
        )
        universe_fp = self._get_universe_fingerprint(target_date)
        trainer = ImpliedVolMlModelTrainer(
            factory=self.factory,
            config=self.config,
            feature_def=self.feature_def,
            history_service=self.history_service,
        )
        try:
            model = trainer.train_and_persist(
                target_date=target_date,
                universe_fingerprint=universe_fp,
            )
        except Exception as e:
            logger.error(f"ImpliedVolMlModelProvider: training failed for {target_date} ({type(e).__name__}: {e})")
            return None
        if model is None:
            logger.error(f"ImpliedVolMlModelProvider: training produced no model for {target_date} — no IV")
            return None
        ImpliedVolMlModelProvider._model_cache[regime_key] = model
        return model

    # ------------------------------------------------------------------
    # Cache management (for testing)
    # ------------------------------------------------------------------

    @classmethod
    def clear_cache(cls) -> None:
        cls._model_cache.clear()
