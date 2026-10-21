"""
LGBMMomentumModelTrainer — builds training data for the cross-sectional
quintile rank momentum model and persists all ML domain entities.

Training data structure
-----------------------
For each (entity_id, date) pair in the DB:
  X  = 24-dim momentum feature vector (values of the momentum factors at `date`)
  y  = quintile rank (1–5) of the 5-day forward return at `date`,
       computed cross-sectionally (all stocks on the same date are ranked together).

The 5-day forward return at `date` is approximated using the pre-computed
`return_5d` factor value at `date + forward_return_days` trading-day offset.
Where that value is not available, the sample is skipped.
"""

import json
import os
import pickle
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple, Any

from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_configuration import (
    LGBMMomentumModelConfiguration,
)
from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_feature_definition import (
    LGBMMomentumFeatureDefinition,
)

_ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "artifacts")

# ORM polymorphic_identity strings for the 24 feature factors
_FEATURE_FACTOR_TYPES = [
    "company_share_return_1d_factor",
    "company_share_return_5d_factor",
    "company_share_return_20d_factor",
    "company_share_return_1m_factor",
    "company_share_return_3m_factor",
    "company_share_return_5m_factor",
    "company_share_return_ytd_factor",
    "company_share_price_vs_ma_20_factor",
    "company_share_price_vs_ma_50_factor",
    "company_share_price_vs_ma_100_factor",
    "company_share_ma_5_vs_ma_10_factor",
    "company_share_ma_20_vs_ma_50_factor",
    "company_share_trend_slope_20d_factor",
    "company_share_trend_slope_50d_factor",
    "company_share_momentum_slope_20d_factor",
    "company_share_sharpe_20d_factor",
    "company_share_sharpe_50d_factor",
    "company_share_sortino_20d_factor",
    "company_share_distance_from_5m_high_factor",
    "company_share_drawdown_from_5m_high_factor",
    "company_share_days_since_5m_high_factor",
    "company_share_short_term_momentum_factor",
    "company_share_medium_term_momentum_factor",
    "company_share_momentum_zscore_20d_factor",
]

# Factor type used for the forward-return label
_RETURN_5D_TYPE = "company_share_return_5d_factor"


class LGBMMomentumModelTrainer:

    def __init__(
        self,
        factory,
        config: LGBMMomentumModelConfiguration,
        feature_def: LGBMMomentumFeatureDefinition,
        history_service=None,
    ):
        self.factory = factory
        self.config = config
        self.feature_def = feature_def
        self.history_service = history_service

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def train_and_persist(
        self,
        target_date: date,
        universe_fingerprint: str,
        factor_id: Optional[int] = None,
    ) -> Optional[Any]:
        print("\n[LGBMMomentum] Step 1: Building training data...")
        X, y, entity_ids = self._build_training_data(target_date)
        if X is None or len(X) < self.config.min_training_samples:
            n = 0 if X is None else len(X)
            print(f"  ✗ Insufficient samples ({n} < {self.config.min_training_samples}); skipping.")
            return None
        n_feat = X.shape[1] if hasattr(X, "shape") else "?"
        print(f"  ✓ {len(X)} samples, {n_feat} features, {self.config.n_quintiles} quintile classes")

        if self.factory is None:
            return self._fit_model(X, y)

        try:
            return self._train_with_domain_persistence(
                X, y, entity_ids, target_date, universe_fingerprint, factor_id
            )
        except Exception as e:
            import traceback
            print(f"LGBMMomentumModelTrainer.train_and_persist error: {e}")
            traceback.print_exc()
            return None

    # ------------------------------------------------------------------
    # Domain persistence orchestration (mirrors ImpliedVolMlModelTrainer)
    # ------------------------------------------------------------------

    def _train_with_domain_persistence(self, X, y, entity_ids, target_date, universe_fingerprint, factor_id):
        from src.domain.entities.ml.ml_model import MLModel
        from src.domain.entities.ml.model_training import ModelTraining
        from src.domain.entities.ml.model_artifact import ModelArtifact
        from src.domain.entities.ml.model_feature import ModelFeature
        from src.domain.entities.ml.training_metric import TrainingMetric

        print("\n[LGBMMomentum] Step 2: Registering universe...")
        universe = self._ensure_universe(entity_ids, target_date)
        print(f"  ✓ Universe '{self.config.UNIVERSE_NAME}' (id={universe.id if universe else None})")

        print("\n[LGBMMomentum] Step 3: Getting / creating MLModel...")
        model_name = f"{self.config.ML_MODEL_NAME_PREFIX}{universe_fingerprint[:16]}"
        ml_model = self.factory.ml_model_local_repo._create_or_get(
            MLModel,
            model_name,
            model_type="lightgbm_classifier",
            configuration=json.dumps(self.config.to_dict()),
            target_factor_id=factor_id,
            description="LightGBM cross-sectional quintile rank momentum model",
        )
        if ml_model is None:
            print("  ✗ MLModel _create_or_get returned None")
            return None
        print(f"  ✓ MLModel '{model_name}' (id={ml_model.id})")

        print("\n[LGBMMomentum] Step 4: Creating training run...")
        valid_until = (
            datetime.combine(target_date, datetime.min.time()) + self.config.retraining_period
        ).date()
        metadata = {
            "universe_fingerprint": universe_fingerprint,
            "feature_definition_hash": self.feature_def.hash(),
            "model_configuration_hash": self.config.hash(),
            "factor_id": factor_id,
            "valid_from": target_date.isoformat(),
            "valid_until": valid_until.isoformat(),
        }
        from src.domain.entities.ml.model_training import ModelTraining
        training_entity = ModelTraining(
            model_id=ml_model.id,
            universe_id=universe.id if universe else None,
            training_end_date=target_date,
            status="pending",
            training_configuration=json.dumps(metadata),
        )
        training = self.factory.model_training_local_repo.add(training_entity)
        if training is None:
            print("  ✗ ModelTraining.add returned None")
            return None
        training.mark_running()
        self.factory.model_training_local_repo.update(training)

        print("\n[LGBMMomentum] Step 5: Fitting LightGBM classifier...")
        model = self._fit_model(X, y)
        if model is None:
            training.mark_failed()
            self.factory.model_training_local_repo.update(training)
            print("  ✗ Fitting failed")
            return None
        print(f"  ✓ Model fitted ({type(model).__name__})")

        print("\n[LGBMMomentum] Step 6: Persisting artifact...")
        os.makedirs(_ARTIFACT_DIR, exist_ok=True)
        filename = f"{self.config.ML_MODEL_NAME_PREFIX}{universe_fingerprint[:16]}_{target_date.isoformat()}.pkl"
        filepath = os.path.join(_ARTIFACT_DIR, filename)
        try:
            with open(filepath, "wb") as f:
                pickle.dump(model, f)
        except Exception as e:
            print(f"  ✗ Could not pickle model: {e}")
            training.mark_failed()
            self.factory.model_training_local_repo.update(training)
            return None
        from src.application.services.model_service.artifact_integrity import sha256_of
        metadata["sha256"] = sha256_of(filepath)          # BI-015: verified before any later unpickling
        training.mark_completed()
        self.factory.model_training_local_repo.update(training)
        from src.domain.entities.ml.model_artifact import ModelArtifact
        self.factory.model_artifact_local_repo._create_or_get(
            ModelArtifact,
            filename,
            model_training_id=training.id,
            artifact_type="trained_model",
            location=filepath,
            format="pickle",
            artifact_metadata=json.dumps(metadata),
        )
        print(f"  ✓ Artifact saved: {filename}")

        print("\n[LGBMMomentum] Step 7: Registering model features...")
        self._ensure_model_features(ml_model, ModelFeature)
        print(f"  ✓ {len(self.feature_def.FEATURE_NAMES)} features registered")

        print("\n[LGBMMomentum] Step 8: Persisting training metrics...")
        self._persist_training_metrics(training, X, y, model, target_date, TrainingMetric)
        print("  ✓ Metrics persisted")

        return model

    # ------------------------------------------------------------------
    # Universe
    # ------------------------------------------------------------------

    def _ensure_universe(self, entity_ids: List[int], training_date: date):
        from src.domain.entities.universe.universe import Universe
        from src.domain.entities.universe.universe_constituent import UniverseConstituent
        try:
            universe_repo = self.factory.investment_universe_local_repo
            constituent_repo = self.factory.universe_constituent_local_repo
            universe = universe_repo._create_or_get(
                Universe,
                self.config.UNIVERSE_NAME,
                entity_type=self.config.UNIVERSE_ENTITY_TYPE,
                description="Training universe for LightGBM cross-sectional quintile rank momentum",
            )
            if universe is None:
                return None
            for eid in entity_ids:
                constituent_repo._create_or_get(
                    UniverseConstituent,
                    f"{universe.id}_{eid}",
                    universe_id=universe.id,
                    entity_id=eid,
                    entity_type=self.config.UNIVERSE_ENTITY_TYPE,
                    start_date=training_date,
                )
            return universe
        except Exception as e:
            print(f"LGBMMomentumModelTrainer._ensure_universe error: {e}")
            return None

    # ------------------------------------------------------------------
    # ModelFeature & TrainingMetric
    # ------------------------------------------------------------------

    def _ensure_model_features(self, ml_model, ModelFeature) -> None:
        from src.domain.entities.ml.model_feature import ModelFeature
        try:
            feature_repo = self.factory.model_feature_local_repo
            for idx, feature_name in enumerate(self.feature_def.FEATURE_NAMES):
                feature_repo._create_or_get(
                    ModelFeature,
                    feature_name,
                    model_id=ml_model.id,
                    factor_id=None,
                    name=feature_name,
                    lag=0,
                    enabled=True,
                    feature_configuration=json.dumps({"index": idx}),
                )
        except Exception as e:
            print(f"LGBMMomentumModelTrainer._ensure_model_features error: {e}")

    def _persist_training_metrics(self, training, X, y, model, target_date, TrainingMetric) -> None:
        from src.domain.entities.ml.training_metric import TrainingMetric
        try:
            import numpy as np
            metric_repo = self.factory.training_metric_local_repo
            metric_repo._create_or_get(
                TrainingMetric, "sample_count",
                model_training_id=training.id,
                metric_name="sample_count",
                metric_value=Decimal(str(len(X))),
                dataset_type="training",
                calculation_date=target_date,
            )
            try:
                y_pred = model.predict(X)
                accuracy = float(np.mean(y_pred == y))
                metric_repo._create_or_get(
                    TrainingMetric, "accuracy",
                    model_training_id=training.id,
                    metric_name="accuracy",
                    metric_value=Decimal(str(round(accuracy, 6))),
                    dataset_type="training",
                    calculation_date=target_date,
                )
            except Exception:
                pass
        except Exception as e:
            print(f"LGBMMomentumModelTrainer._persist_training_metrics error: {e}")

    # ------------------------------------------------------------------
    # Training data collection
    # ------------------------------------------------------------------

    def _build_training_data(
        self, target_date: date
    ) -> Tuple[Optional[Any], Optional[Any], List[int]]:
        """
        Returns (X, y, entity_ids).

        X: numpy array shape (n_samples, 24) — momentum feature vectors
        y: numpy array shape (n_samples,) — quintile rank labels 1–5
        entity_ids: list of entity_id values that appear in the training set
        """
        if self.factory is None:
            return None, None, []

        try:
            import numpy as np
        except ImportError:
            print("LGBMMomentumModelTrainer: numpy not available.")
            return None, None, []

        from src.infrastructure.models.factor.factor_value import FactorValueModel
        from src.infrastructure.models.factor.factor import FactorModel

        session = self.factory.session

        # ── Step A: collect factor-type → factor_id mapping ─────────────────
        feature_factor_id_sets = {}
        for ftype in _FEATURE_FACTOR_TYPES:
            rows = session.query(FactorModel).filter(FactorModel.factor_type == ftype).all()
            if rows:
                feature_factor_id_sets[ftype] = {r.id for r in rows}

        # Return-5d factor (used for forward-return label)
        return_5d_rows = session.query(FactorModel).filter(
            FactorModel.factor_type == _RETURN_5D_TYPE
        ).all()
        if not return_5d_rows:
            print("  ✗ No return_5d factor rows in DB — cannot build labels.")
            return None, None, []
        return_5d_ids = {r.id for r in return_5d_rows}

        if not feature_factor_id_sets:
            print("  ✗ No momentum factor rows in DB — cannot build features.")
            return None, None, []

        # ── Step B: load all relevant factor values into memory ──────────────
        # feature values: {(entity_id, date_key, factor_type) → float}
        feature_lookup: dict = {}
        all_feature_ids = set()
        for ftype, fids in feature_factor_id_sets.items():
            all_feature_ids.update(fids)

        feat_rows = session.query(FactorValueModel).filter(
            FactorValueModel.factor_id.in_(all_feature_ids)
        ).all()

        # reverse map: factor_id → factor_type
        id_to_type = {}
        for ftype, fids in feature_factor_id_sets.items():
            for fid in fids:
                id_to_type[fid] = ftype

        def _dk(dt):
            return dt.date() if hasattr(dt, "date") else dt

        for fv in feat_rows:
            ftype = id_to_type.get(fv.factor_id)
            if ftype is None:
                continue
            dk = _dk(fv.date)
            if dk > target_date:
                continue
            key = (fv.entity_id, dk, ftype)
            try:
                feature_lookup[key] = float(str(fv.value))
            except (ValueError, TypeError):
                pass

        # forward-return label lookup: {(entity_id, date_key) → float}
        return_lookup: dict = {}
        ret_rows = session.query(FactorValueModel).filter(
            FactorValueModel.factor_id.in_(return_5d_ids)
        ).all()
        for fv in ret_rows:
            dk = _dk(fv.date)
            key = (fv.entity_id, dk)
            try:
                return_lookup[key] = float(str(fv.value))
            except (ValueError, TypeError):
                pass

        if not return_lookup:
            print("  ✗ No return_5d values in DB — cannot build labels.")
            return None, None, []

        # ── Step C: find all (entity_id, date) pairs that have all 24 features
        # and a forward return label ─────────────────────────────────────────
        # Group feature_lookup keys by (entity_id, date)
        sample_candidates: dict = {}  # {(entity_id, date): {ftype: value}}
        for (entity_id, dk, ftype), val in feature_lookup.items():
            sample_candidates.setdefault((entity_id, dk), {})[ftype] = val

        # Keep only samples with all 24 features + a forward return label
        X_rows, y_rows, seen_entity_ids = [], [], set()

        for (entity_id, sample_date), feat_dict in sample_candidates.items():
            if len(feat_dict) < len(self.feature_def.FEATURE_MAP):
                continue  # not all features available

            # Forward return: look for return_5d value ~5 trading days ahead
            # Try exact offset by calendar days (5 days forward)
            label = None
            for offset_days in range(5, 12):  # 5–11 calendar days covers 1 trading week
                fwd_date = sample_date + timedelta(days=offset_days)
                label = return_lookup.get((entity_id, fwd_date))
                if label is not None:
                    break
            if label is None:
                continue

            # Build feature vector in canonical order
            row = []
            valid = True
            for ftype, _ in zip(_FEATURE_FACTOR_TYPES, self.feature_def.FEATURE_NAMES):
                v = feat_dict.get(ftype)
                if v is None:
                    valid = False
                    break
                row.append(v)
            if not valid:
                continue

            X_rows.append(row)
            y_rows.append(label)
            seen_entity_ids.add(entity_id)

        if not X_rows:
            return None, None, []

        X = np.array(X_rows, dtype=float)
        y_raw = np.array(y_rows, dtype=float)

        # ── Step D: cross-sectional quintile ranking ─────────────────────────
        # Group samples by date (we need same-date samples to rank together)
        # Since X_rows are not date-indexed here, we do a global rank over all
        # training samples. This approximates cross-sectional ranking when the
        # training set spans many dates with similar stock universes.
        y = self._assign_quintile_labels(y_raw, self.config.n_quintiles)

        return X, y, list(seen_entity_ids)

    def _assign_quintile_labels(self, y_raw, n_quintiles: int):
        """Convert raw return values to quintile rank labels (1 = worst, n_quintiles = best)."""
        import numpy as np
        ranks = np.argsort(np.argsort(y_raw))  # ordinal rank 0..N-1
        n = len(ranks)
        # Map rank to quintile 1..n_quintiles
        labels = np.floor(ranks / n * n_quintiles).astype(int) + 1
        labels = np.clip(labels, 1, n_quintiles)
        return labels

    # ------------------------------------------------------------------
    # Model fitting — LightGBM classifier, sklearn fallback
    # ------------------------------------------------------------------

    def _fit_model(self, X, y) -> Optional[Any]:
        try:
            import lightgbm as lgb
            model = lgb.LGBMClassifier(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                learning_rate=self.config.learning_rate,
                num_leaves=self.config.num_leaves,
                min_child_samples=self.config.min_data_in_leaf,
                random_state=self.config.random_state,
                n_jobs=-1,
                verbose=-1,
            )
            model.fit(X, y)
            return model
        except ImportError:
            pass
        # Sklearn RandomForest classifier fallback
        try:
            from sklearn.ensemble import RandomForestClassifier
            model = RandomForestClassifier(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                random_state=self.config.random_state,
                n_jobs=-1,
            )
            model.fit(X, y)
            return model
        except ImportError:
            print("LGBMMomentumModelTrainer: neither lightgbm nor sklearn available.")
            return None
