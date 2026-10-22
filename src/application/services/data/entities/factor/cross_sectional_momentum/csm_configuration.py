"""
CSMConfiguration — every parameter of the cross-sectional momentum classifier in one serialisable object.

    features      the candidate features (Optuna chooses the subset used by each model)
    label         what the classifier predicts: next ``horizon`` sessions' return above the cross-sectional median
    optimization  the Optuna TPE study run at each retraining (feature subset + LightGBM hyper-parameters)
    training      rolling training window, retraining schedule, portfolio construction
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class CSMUniverseConfig:
    name: str = "csm_universe"
    entity_type: str = "CompanyShare"
    tickers: Optional[List[str]] = None


@dataclass
class CSMFeatureConfig:
    """
    Candidate features = the 24 momentum factors of LGBMMomentumFeatureDefinition (return_1d ... momentum_zscore_20d),
    each computed by its own domain factor's calculate() on the closes up to the date, so the trading cycle and the
    factor-resolution path read identical values. ``cross_sectional_ranks`` adds the per-date percentile rank of
    each (cs_rank_<name>); those need the whole cross-section, so a model using them can only be scored by the
    trading cycle, not by a single-entity factor resolution.
    """

    cross_sectional_ranks: bool = False
    vol_span: int = 20                    # EWM span of the daily volatility used for position sizing (not a feature)
    exclude: Tuple[str, ...] = ()         # candidates left out of the study

    def base_feature_names(self) -> List[str]:
        from src.application.services.data.entities.factor.lgbm_momentum.lgbm_momentum_feature_definition import (
            LGBMMomentumFeatureDefinition,
        )
        return [n for n in LGBMMomentumFeatureDefinition.FEATURE_NAMES if n not in self.exclude]

    def feature_names(self) -> List[str]:
        base = self.base_feature_names()
        return base + ([f"cs_rank_{n}" for n in base] if self.cross_sectional_ranks else [])

    def warmup_rows(self) -> int:
        """Sessions of closes before the first row where every candidate exists (longest lookback: 106)."""
        return 107


@dataclass
class CSMLabelConfig:
    horizon: int = 1                     # sessions ahead


@dataclass
class CSMOptimizationConfig:
    """Optuna study run at every retraining: TPE over the feature subset and the LightGBM hyper-parameters."""

    n_trials: int = 40
    n_startup_trials: int = 10           # random trials before TPE models the search space
    multivariate: bool = True            # TPE models the parameters jointly
    n_folds: int = 3                     # purged walk-forward folds inside the training window
    metric: str = "auc"                  # 'auc' | 'long_short_sharpe' (validation, averaged over folds)
    min_features: int = 3
    seed: int = 42
    timeout_seconds: Optional[float] = None
    top_trial_fraction: float = 0.2      # trials used for the feature selection frequency
    # search space
    num_leaves: Tuple[int, int] = (7, 63)
    max_depth: Tuple[int, int] = (2, 8)
    learning_rate: Tuple[float, float] = (0.01, 0.2)
    n_estimators: Tuple[int, int] = (50, 400)
    min_child_samples: Tuple[int, int] = (10, 200)
    subsample: Tuple[float, float] = (0.5, 1.0)
    colsample_bytree: Tuple[float, float] = (0.5, 1.0)
    reg_lambda: Tuple[float, float] = (1e-3, 10.0)
    n_jobs: int = 1


@dataclass
class CSMTrainingConfig:
    training_window_rows: int = 252      # sessions of history the model is trained on (rolling)
    long_short_quantile: float = 0.2     # long the top, short the bottom quantile of probabilities
    gross_exposure: float = 1.0          # sum of |weights| (half long, half short)


@dataclass
class CSMConfiguration:
    universe: CSMUniverseConfig = field(default_factory=CSMUniverseConfig)
    features: CSMFeatureConfig = field(default_factory=CSMFeatureConfig)
    label: CSMLabelConfig = field(default_factory=CSMLabelConfig)
    optimization: CSMOptimizationConfig = field(default_factory=CSMOptimizationConfig)
    training: CSMTrainingConfig = field(default_factory=CSMTrainingConfig)
    artifact_dir: Optional[str] = None
    ml_model_name_prefix: str = "csm_"
    signal_factor_name: str = "cross_sectional_momentum_signal"
    persist_signals: bool = True

    def required_history_rows(self) -> int:
        return self.training.training_window_rows + self.features.warmup_rows() + self.label.horizon

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CSMConfiguration":
        def tup(x):
            return tuple(x) if isinstance(x, list) else x
        f = {k: tup(v) for k, v in d.get("features", {}).items()}
        o = {k: tup(v) for k, v in d.get("optimization", {}).items()}
        return cls(
            universe=CSMUniverseConfig(**d.get("universe", {})),
            features=CSMFeatureConfig(**f),
            label=CSMLabelConfig(**d.get("label", {})),
            optimization=CSMOptimizationConfig(**o),
            training=CSMTrainingConfig(**d.get("training", {})),
            artifact_dir=d.get("artifact_dir"),
            ml_model_name_prefix=d.get("ml_model_name_prefix", "csm_"),
            signal_factor_name=d.get("signal_factor_name", "cross_sectional_momentum_signal"),
            persist_signals=d.get("persist_signals", True),
        )

    def model_hash(self) -> str:
        """Identity of everything that changes a trained model (not paths or persistence switches)."""
        d = self.to_dict()
        for k in ("artifact_dir", "persist_signals"):
            d.pop(k, None)
        return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()
