"""
CSMConfiguration — every parameter of the cross-sectional momentum classifier in one serialisable object.

    features      the candidate features (Optuna chooses the subset used by each model)
    label         what the classifier predicts: next ``horizon`` sessions' return above the cross-sectional median
    optimization  the Optuna TPE study run at each retraining (feature subset + LightGBM hyper-parameters)
    training      rolling training window, retraining schedule, portfolio construction
    bar_minutes   None = daily bars (one row per session); e.g. 10 = 10-minute bars: every window, the label horizon,
                  the training window and the annualisation are then counted in 10-minute bars
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


def liquidity_volume_names(enabled: bool) -> List[str]:
    """The opt-in liquidity / volume candidates (feature name = the factor's default name), or none."""
    if not enabled:
        return []
    from src.domain.entities.factor.finance.financial_assets.share_factor.company_share.company_share_liquidity_volume_factors import (  # noqa: E501
        LIQUIDITY_VOLUME_FACTOR_CLASSES,
    )
    return [cls.DEFAULT_NAME for cls in LIQUIDITY_VOLUME_FACTOR_CLASSES]


@dataclass
class CSMFeatureConfig:
    """
    Candidate features = CSMFeatureDefinition: the 24 momentum factors of LGBMMomentumFeatureDefinition plus 11
    liquidity / volume-trend / price-range / return-extreme factors, each computed by its own domain factor's
    calculate() on the bars up to the date, so the trading cycle and the factor-resolution path read identical values. ``cross_sectional_ranks`` adds the per-date percentile rank of
    each (cs_rank_<name>); those need the whole cross-section, so a model using them can only be scored by the
    trading cycle, not by a single-entity factor resolution.
    """

    cross_sectional_ranks: bool = False
    vol_span: int = 20                    # EWM span of the daily volatility used for position sizing (not a feature)
    exclude: Tuple[str, ...] = ()         # candidates left out of the study
    # point-in-time fundamental candidates (csm_fundamentals: 'fund_<factor>_<1q|1y>'), read from the statement
    # provider(s) the cycle is given; empty = none (the default: no statements are fetched)
    fundamentals: Tuple[str, ...] = ()
    # opt-in (2026-11-23): the 27 liquidity / volume candidates over 5d..12m (company_share_liquidity_volume_factors).
    # Off by default, so existing configurations keep their 48 candidates, warm-up and model hash. Computed by the
    # trading cycle / feature engine only: not dependencies of CompanyShareCrossSectionalMomentumFactor, so a model
    # selecting them cannot be scored by a single-entity factor resolution (like cross_sectional_ranks)
    liquidity_volume: bool = False

    def base_feature_names(self) -> List[str]:
        from src.application.services.data.entities.factor.cross_sectional_momentum.csm_feature_definition import (
            CSMFeatureDefinition,
        )
        names = list(CSMFeatureDefinition.FEATURE_NAMES) + liquidity_volume_names(self.liquidity_volume) \
            + list(self.fundamentals)
        return [n for n in names if n not in self.exclude]

    def fundamental_names(self) -> List[str]:
        return [n for n in self.fundamentals if n not in self.exclude]

    def feature_names(self) -> List[str]:
        base = self.base_feature_names()
        return base + ([f"cs_rank_{n}" for n in base] if self.cross_sectional_ranks else [])

    def warmup_rows(self) -> int:
        """Sessions of bars before the first row where every candidate exists: the longest window plus one - 127
        closes of max_daily_return_6m, 253 with the liquidity / volume group (12-month factors). Constants, checked
        against csm_features.max_lookback by the tests (no import of csm_features here: it imports this module)."""
        return 254 if self.liquidity_volume else 128


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
    min_feature_coverage: float = 0.8    # candidates present on fewer labelled rows of the window are left out
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
    bar_minutes: Optional[int] = None
    optimization: CSMOptimizationConfig = field(default_factory=CSMOptimizationConfig)
    training: CSMTrainingConfig = field(default_factory=CSMTrainingConfig)
    artifact_dir: Optional[str] = None
    ml_model_name_prefix: str = "csm_"
    signal_factor_name: str = "cross_sectional_momentum_signal"
    persist_signals: bool = True
    # store the candidate feature values of every decision as factor values (CSMFeatureStore): the decision can
    # then be audited from the database (option C, 2026-10-26)
    persist_features: bool = False

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
            bar_minutes=d.get("bar_minutes"),
            optimization=CSMOptimizationConfig(**o),
            training=CSMTrainingConfig(**d.get("training", {})),
            artifact_dir=d.get("artifact_dir"),
            ml_model_name_prefix=d.get("ml_model_name_prefix", "csm_"),
            signal_factor_name=d.get("signal_factor_name", "cross_sectional_momentum_signal"),
            persist_signals=d.get("persist_signals", True),
            persist_features=d.get("persist_features", False),
        )

    def model_hash(self) -> str:
        """Identity of everything that changes a trained model (not paths or persistence switches)."""
        d = self.to_dict()
        for k in ("artifact_dir", "persist_signals", "persist_features"):
            d.pop(k, None)
        if d.get("bar_minutes") is None:
            d.pop("bar_minutes", None)            # daily: the hash of the models trained before the field existed
        if not d.get("features", {}).get("fundamentals"):
            d.get("features", {}).pop("fundamentals", None)    # idem: models trained before fundamentals existed
        if not d.get("features", {}).get("liquidity_volume"):
            d.get("features", {}).pop("liquidity_volume", None)   # idem: before the liquidity / volume candidates
        return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()
