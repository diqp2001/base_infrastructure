"""
ImpliedVolMlModelTrainer — builds training data, fits the model, and persists
every domain entity required by the ML lifecycle.

Domain entities used
--------------------
* Universe              — named pool of CompanyShareOptions used as training universe
* UniverseConstituent   — one row per option entity_id in the training set
* MLModel               — definition of this model type (one per model name)
* ModelTraining         — one training run; lifecycle: pending → running → completed/failed
* ModelArtifact         — pickled model file linked to the training run
* ModelFeature          — one row per feature dimension of the input vector
* TrainingMetric        — r_squared, rmse, sample_count linked to the training run
"""

import json
import os
import pickle
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Tuple, Any

from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_model_configuration import (
    ImpliedVolMlModelConfiguration,
)
from src.application.services.data.entities.factor.implied_vol_ml.implied_vol_ml_feature_definition import (
    ImpliedVolMlFeatureDefinition,
)

_ARTIFACT_DIR = os.path.join(os.path.dirname(__file__), "artifacts")


class ImpliedVolMlModelTrainer:

    def __init__(
        self,
        factory,
        config: ImpliedVolMlModelConfiguration,
        feature_def: ImpliedVolMlFeatureDefinition,
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
        """
        Build training data, fit model, persist all domain entities, return fitted model.
        Returns None when insufficient data or fitting fails.
        """
        print("\nStep 1: Building training data...")
        X, y, entity_ids = self._build_training_data(target_date)
        if X is None or len(X) < self.config.min_training_samples:
            print(
                f"  ✗ Insufficient training samples "
                f"({0 if X is None else len(X)} < {self.config.min_training_samples}); skipping."
            )
            return None
        print(f"  ✓ {len(X)} samples, {X.shape[1] if hasattr(X, 'shape') else '?'} features")

        if self.factory is None:
            print("\nStep 2: Fitting model (no DB — factory=None)...")
            return self._fit_model(X, y)

        try:
            return self._train_with_domain_persistence(
                X, y, entity_ids, target_date, universe_fingerprint, factor_id
            )
        except Exception as e:
            import traceback
            print(f"ImpliedVolMlModelTrainer.train_and_persist error: {e}")
            traceback.print_exc()
            return None

    # ------------------------------------------------------------------
    # Domain-layer orchestration
    # ------------------------------------------------------------------

    def _train_with_domain_persistence(
        self,
        X,
        y,
        entity_ids: List[int],
        target_date: date,
        universe_fingerprint: str,
        factor_id: Optional[int],
    ) -> Optional[Any]:
        from src.domain.entities.ml.ml_model import MLModel
        from src.domain.entities.ml.model_training import ModelTraining
        from src.domain.entities.ml.model_artifact import ModelArtifact
        from src.domain.entities.ml.model_feature import ModelFeature
        from src.domain.entities.ml.training_metric import TrainingMetric
        from src.domain.entities.universe.universe import Universe
        from src.domain.entities.universe.universe_constituent import UniverseConstituent

        print("\nStep 2: Registering universe...")
        universe = self._ensure_universe(entity_ids, target_date)
        print(f"  ✓ Universe '{self.config.UNIVERSE_NAME}' (id={universe.id if universe else None})")

        print("\nStep 3: Getting / creating MLModel...")
        model_name = f"{self.config.ML_MODEL_NAME_PREFIX}{universe_fingerprint[:16]}"
        ml_model = self.factory.ml_model_local_repo._create_or_get(
            MLModel,
            model_name,
            model_type="random_forest",
            configuration=json.dumps(self.config.to_dict()),
            target_factor_id=factor_id,
            description="ML-predicted implied volatility (RandomForest)",
        )
        if ml_model is None:
            print("  ✗ MLModel _create_or_get returned None — check ml_model_local_repo")
            return None
        print(f"  ✓ MLModel '{model_name}' (id={ml_model.id})")

        print("\nStep 4: Creating training run (pending → running)...")
        valid_until = (
            datetime.combine(target_date, datetime.min.time())
            + self.config.retraining_period
        ).date()
        metadata = {
            "universe_fingerprint": universe_fingerprint,
            "feature_definition_hash": self.feature_def.hash(),
            "model_configuration_hash": self.config.hash(),
            "factor_id": factor_id,
            "valid_from": target_date.isoformat(),
            "valid_until": valid_until.isoformat(),
        }
        training_entity = ModelTraining(
            model_id=ml_model.id,
            universe_id=universe.id if universe else None,
            training_end_date=target_date,
            status="pending",
            training_configuration=json.dumps(metadata),
        )
        training = self.factory.model_training_local_repo.add(training_entity)
        if training is None:
            print("  ✗ ModelTraining.add returned None — check model_training_local_repo")
            return None
        training.mark_running()
        self.factory.model_training_local_repo.update(training)

        print("\nStep 5: Fitting model...")
        model = self._fit_model(X, y)
        if model is None:
            training.mark_failed()
            self.factory.model_training_local_repo.update(training)
            print("  ✗ Fitting failed — training marked failed")
            return None
        print(f"  ✓ Model fitted ({type(model).__name__})")

        print("\nStep 6: Persisting artifact to disk...")
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

        print("\nStep 7: Registering model features...")
        self._ensure_model_features(ml_model, ModelFeature)
        print(f"  ✓ {len(self.feature_def.FEATURE_NAMES)} features registered")

        print("\nStep 8: Persisting training metrics...")
        self._persist_training_metrics(training, X, y, model, target_date, TrainingMetric)
        print("  ✓ Metrics persisted")

        return model

    # ------------------------------------------------------------------
    # Universe registration
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
                description="Training universe for ML-predicted implied volatility",
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
            print(f"ImpliedVolMlModelTrainer._ensure_universe error: {e}")
            return None

    # ------------------------------------------------------------------
    # ModelFeature registration
    # ------------------------------------------------------------------

    def _ensure_model_features(self, ml_model, ModelFeature) -> None:
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
            print(f"ImpliedVolMlModelTrainer._ensure_model_features error: {e}")

    # ------------------------------------------------------------------
    # TrainingMetric persistence
    # ------------------------------------------------------------------

    def _persist_training_metrics(
        self, training, X, y, model, target_date: date, TrainingMetric
    ) -> None:
        try:
            import numpy as np

            metric_repo = self.factory.training_metric_local_repo
            sample_count = len(X)
            metric_repo._create_or_get(
                TrainingMetric,
                "sample_count",
                model_training_id=training.id,
                metric_name="sample_count",
                metric_value=Decimal(str(sample_count)),
                dataset_type="training",
                calculation_date=target_date,
            )

            try:
                y_pred = model.predict(X)
                ss_res = float(np.sum((y - y_pred) ** 2))
                ss_tot = float(np.sum((y - np.mean(y)) ** 2))
                r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
                rmse = float(np.sqrt(np.mean((y - y_pred) ** 2)))

                metric_repo._create_or_get(
                    TrainingMetric,
                    "r_squared",
                    model_training_id=training.id,
                    metric_name="r_squared",
                    metric_value=Decimal(str(round(r_squared, 6))),
                    dataset_type="training",
                    calculation_date=target_date,
                )
                metric_repo._create_or_get(
                    TrainingMetric,
                    "rmse",
                    model_training_id=training.id,
                    metric_name="rmse",
                    metric_value=Decimal(str(round(rmse, 8))),
                    dataset_type="training",
                    calculation_date=target_date,
                )
            except Exception:
                pass  # metrics are best-effort
        except Exception as e:
            print(f"ImpliedVolMlModelTrainer._persist_training_metrics error: {e}")

    # ------------------------------------------------------------------
    # Training data collection
    # ------------------------------------------------------------------

    def _prefetch_training_data(self, target_date: date) -> None:
        """
        Ensure factor values for the last training_window_bars dates exist by
        calling _create_or_get_factor_value_batch for option and share entities.
        Failures are logged but never block training.
        """
        from src.domain.entities.universe.universe_constituent import UniverseConstituent

        try:
            entity_ids: list = []

            # --- Primary: entities from the training universe (available after first run) ---
            try:
                universe_repo = self.factory.investment_universe_local_repo
                constituent_repo = self.factory.universe_constituent_local_repo
                universe = universe_repo.get_by_name(self.config.UNIVERSE_NAME)
                if universe is not None and universe.id is not None:
                    constituents = constituent_repo.get_active_by_universe(universe.id, target_date)
                    entity_ids = [
                        c.entity_id for c in constituents
                        if isinstance(c, UniverseConstituent) and c.entity_id is not None
                    ]
            except Exception:
                pass

            # --- Fallback: universe not seeded yet — use entities from existing IV values ---
            if not entity_ids:
                from src.infrastructure.models.factor.factor_value import FactorValueModel
                from src.infrastructure.models.factor.factor import FactorModel as _FactorModel
                session = self.factory.session
                iv_orm = session.query(_FactorModel).filter(
                    _FactorModel.factor_type == "company_share_option_implied_vol_factor"
                ).all()
                if iv_orm:
                    iv_ids = [r.id for r in iv_orm]
                    rows = (
                        session.query(FactorValueModel.entity_id)
                        .filter(FactorValueModel.factor_id.in_(iv_ids))
                        .distinct()
                        .all()
                    )
                    entity_ids = [r.entity_id for r in rows]

            if not entity_ids:
                print("    ⚠ No option entities found — skipping data pre-fetch")
                return

            option_repo = self.factory.company_share_option_local_repo
            option_entities = [
                e for e in (option_repo.get_by_id(eid) for eid in entity_ids)
                if e is not None
            ]
            if not option_entities:
                return

            # --- Option factor domain entities ---
            factor_groups: list = []
            for repo_key in (
                'CompanyShareOptionImpliedVolFactor',
                'CompanyShareOptionRFYieldFactor',
            ):
                try:
                    repo = self.factory.get_local_repository(repo_key)
                    for f in (repo.get_all() or []):
                        factor_groups.append({'factor_entity': f})
                except Exception:
                    pass
            try:
                for f in (self.factory.company_share_option_value_factor_local_repo.get_all() or []):
                    factor_groups.append({'factor_entity': f})
            except Exception:
                pass

            # --- Underlying share entities + share value factors ---
            share_factor_groups: list = []
            share_entities: list = []
            try:
                share_ids = {
                    getattr(e, 'underlying_asset_id', None)
                    for e in option_entities
                    if getattr(e, 'underlying_asset_id', None) is not None
                }
                if share_ids:
                    share_repo = self.factory.get_local_repository('CompanyShare')
                    share_entities = [
                        s for s in (share_repo.get_by_id(sid) for sid in share_ids)
                        if s is not None
                    ]
                    for f in (self.factory.company_share_value_factor_local_repo.get_all() or []):
                        share_factor_groups.append({'factor_entity': f})
            except Exception:
                pass

            # --- Fetch window (single request covers all bars via duration_str) ---
            duration_str = f"{self.config.training_window_bars} D"
            if factor_groups:
                try:
                    self.history_service._create_or_get_factor_value_batch(
                        factor_groups=factor_groups,
                        entities=option_entities,
                        date=target_date,
                        duration_str=duration_str,
                    )
                except Exception as e:
                    print(f"    ⚠ Option pre-fetch failed: {e}")
            if share_entities and share_factor_groups:
                try:
                    self.history_service._create_or_get_factor_value_batch(
                        factor_groups=share_factor_groups,
                        entities=share_entities,
                        date=target_date,
                        duration_str=duration_str,
                    )
                except Exception as e:
                    print(f"    ⚠ Share pre-fetch failed: {e}")

            print(
                f"    ✓ Pre-fetch window: {self.config.training_window_bars} bars"
                f" × {len(option_entities)} options"
                + (f" + {len(share_entities)} underlyings" if share_entities else "")
            )

        except Exception as e:
            print(f"    ⚠ Training data pre-fetch failed: {e}")

    def _build_training_data(
        self, target_date: date
    ) -> Tuple[Optional[Any], Optional[Any], List[int]]:
        """Returns (X, y, entity_ids)."""
        if self.factory is None:
            return None, None, []

        try:
            import numpy as np
        except ImportError:
            print("ImpliedVolMlModelTrainer: numpy not available.")
            return None, None, []

        from src.infrastructure.models.factor.factor_value import FactorValueModel
        from src.infrastructure.models.factor.factor import FactorModel
        from src.infrastructure.models.finance.financial_assets.derivative.option.company_share_option import (
            CompanyShareOptionModel,
        )

        session = self.factory.session

        # Phase 0: Fetch missing factor values for training window via IBKR
        if self.history_service is not None:
            self._prefetch_training_data(target_date)

        # Analytical IV factor rows
        iv_factor_rows = session.query(FactorModel).filter(
            FactorModel.factor_type == "company_share_option_implied_vol_factor"
        ).all()
        if not iv_factor_rows:
            return None, None, []
        iv_factor_ids = [r.id for r in iv_factor_rows]

        # Option-value factor rows
        opt_val_rows = session.query(FactorModel).filter(
            FactorModel.factor_type == "company_share_option_value_factor"
        ).all()
        opt_val_ids = {r.id for r in opt_val_rows}

        # RF-yield factor rows
        rf_rows = session.query(FactorModel).filter(
            FactorModel.factor_type == "company_share_option_rf_yield_factor"
        ).all()
        rf_ids = {r.id for r in rf_rows}

        # Share-value factor rows
        share_val_rows = session.query(FactorModel).filter(
            FactorModel.factor_type == "company_share_value_factor"
        ).all()
        share_val_ids = {r.id for r in share_val_rows}

        # All IV values up to target_date
        iv_values = session.query(FactorValueModel).filter(
            FactorValueModel.factor_id.in_(iv_factor_ids),
        ).all()
        if not iv_values:
            return None, None, []

        def _date_key(dt):
            return dt.date() if hasattr(dt, "date") else dt

        opt_lookup: dict = {}
        for fv in session.query(FactorValueModel).filter(
            FactorValueModel.factor_id.in_(opt_val_ids)
        ).all():
            opt_lookup.setdefault((_date_key(fv.date), fv.entity_id), []).append(fv.value)

        rf_lookup: dict = {}
        for fv in session.query(FactorValueModel).filter(
            FactorValueModel.factor_id.in_(rf_ids)
        ).all():
            rf_lookup.setdefault((_date_key(fv.date), fv.entity_id), []).append(fv.value)

        share_lookup: dict = {}
        for fv in session.query(FactorValueModel).filter(
            FactorValueModel.factor_id.in_(share_val_ids)
        ).all():
            share_lookup.setdefault((_date_key(fv.date), fv.entity_id), []).append(fv.value)

        import math
        X_rows, y_rows, seen_entity_ids = [], [], set()

        for iv_fv in iv_values:
            iv_date = _date_key(iv_fv.date)
            if iv_date > target_date or iv_fv.value is None:
                continue
            try:
                target_iv = float(str(iv_fv.value))
            except (ValueError, TypeError):
                continue

            entity_id = iv_fv.entity_id
            opt_orm = session.query(CompanyShareOptionModel).filter(
                CompanyShareOptionModel.id == entity_id
            ).first()
            if opt_orm is None:
                continue

            strike = getattr(opt_orm, "strike_price", None)
            if strike is None:
                continue
            try:
                strike = float(strike)
            except (ValueError, TypeError):
                continue
            if strike <= 0:
                continue

            expiry_date = getattr(opt_orm, "end_date", None)
            if expiry_date is None:
                expiry_str = getattr(opt_orm, "expiry", None)
                if expiry_str:
                    try:
                        from datetime import datetime as _dt
                        expiry_date = _dt.strptime(str(expiry_str), "%Y%m%d").date()
                    except ValueError:
                        continue
            if expiry_date is None:
                continue
            if hasattr(expiry_date, "date"):
                expiry_date = expiry_date.date()
            days = (expiry_date - iv_date).days
            if days <= 0:
                continue
            tte = days / 365.0

            option_type = getattr(opt_orm, "option_type", "call") or "call"
            is_call = 1.0 if option_type.lower() == "call" else 0.0

            opt_vals = opt_lookup.get((iv_date, entity_id))
            if not opt_vals:
                continue
            try:
                option_price = sum(float(str(v)) for v in opt_vals) / len(opt_vals)
            except (ValueError, TypeError):
                continue
            if option_price <= 0:
                continue

            rf_vals = rf_lookup.get((iv_date, entity_id))
            if not rf_vals:
                continue
            try:
                rf_rate = sum(float(str(v)) for v in rf_vals) / len(rf_vals)
            except (ValueError, TypeError):
                continue

            underlying_id = getattr(opt_orm, "underlying_asset_id", None)
            if underlying_id is None:
                continue
            share_vals = share_lookup.get((iv_date, underlying_id))
            if not share_vals:
                continue
            try:
                stock_price = sum(float(str(v)) for v in share_vals) / len(share_vals)
            except (ValueError, TypeError):
                continue
            if stock_price <= 0:
                continue

            moneyness = stock_price / strike
            try:
                log_moneyness = math.log(moneyness)
            except (ValueError, ZeroDivisionError):
                continue
            norm_option_price = option_price / stock_price

            X_rows.append([moneyness, log_moneyness, tte, rf_rate, norm_option_price, is_call])
            y_rows.append(target_iv)
            seen_entity_ids.add(entity_id)

        if not X_rows:
            return None, None, []
        return np.array(X_rows), np.array(y_rows), list(seen_entity_ids)

    # ------------------------------------------------------------------
    # Model fitting
    # ------------------------------------------------------------------

    def _fit_model(self, X, y) -> Optional[Any]:
        try:
            from sklearn.ensemble import RandomForestRegressor
            model = RandomForestRegressor(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                min_samples_split=self.config.min_samples_split,
                random_state=self.config.random_state,
                n_jobs=-1,
            )
            model.fit(X, y)
            return model
        except ImportError:
            pass
        try:
            import lightgbm as lgb
            model = lgb.LGBMRegressor(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                random_state=self.config.random_state,
            )
            model.fit(X, y)
            return model
        except ImportError:
            print("ImpliedVolMlModelTrainer: neither sklearn nor lightgbm available.")
            return None
