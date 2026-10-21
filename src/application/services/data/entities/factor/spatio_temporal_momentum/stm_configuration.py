"""
STMConfiguration — every research parameter of the Spatio-Temporal Momentum
pipeline in one serialisable object.

Defaults reproduce the reference notebook `train_multivariate.ipynb` /
`src/features.py`, except where the project requested otherwise:
  * model_type defaults to 'tft' (notebook default is 'mlp')
  * lookback defaults to 84 trading days (4 x 21) with a 63-day encoder
    (notebook TFT uses 63 / 42)
  * n_epochs defaults to 100 with early stopping (notebook uses 2)
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Reference feature names (src/features.py → DeepMomentumFeatures / MACDFeatures)
_REFERENCE_RETURN_NAMES = {
    1: "norm_daily_return",
    21: "norm_monthly_return",
    63: "norm_quarterly_return",
    126: "norm_biannual_return",
    252: "norm_annual_return",
}


@dataclass
class STMFeatureConfig:
    """Feature construction (reference: DeepMomentumFeatures, MACDFeatures, DefaultFeatureCreator)."""

    return_horizons: Tuple[int, ...] = (1, 21, 63, 126, 252)
    vol_lookback: int = 60                 # EWM span for daily vol
    vol_target: float = 0.15               # annualised vol target for the scaled target
    macd_combinations: Tuple[Tuple[int, int], ...] = ((8, 24), (16, 48), (32, 96))
    macd_price_std_window: int = 63        # q = macd / rolling(63).std(price)
    macd_signal_std_window: int = 252      # signal = q / rolling(252).std(q)
    winsorise_halflife: int = 252          # DefaultFeatureCreator half_winsore
    winsorise_threshold: float = 5.0       # DefaultFeatureCreator vol_threshold
    min_warmup_rows: int = 253             # DefaultFeatureCreator cut_nan_samples
    annualisation: int = 252

    def return_feature_names(self) -> List[str]:
        return [_REFERENCE_RETURN_NAMES.get(h, f"norm_return_{h}d") for h in self.return_horizons]

    def macd_feature_names(self) -> List[str]:
        return [f"macd_{s}_{l}" for s, l in self.macd_combinations]

    def feature_names(self) -> List[str]:
        """Canonical feature order — identical in training and inference."""
        return self.return_feature_names() + self.macd_feature_names()

    def required_history_days(self, lookback: int) -> int:
        """Trading days of closes needed before the first usable sample."""
        # a normalised return needs both its h-day return and the vol (min_periods)
        longest_return = max(self.return_horizons) if self.return_horizons else 0
        return_warmup = max(longest_return, self.vol_lookback) + 1
        macd_warmup = self.macd_price_std_window + self.macd_signal_std_window
        return max(self.min_warmup_rows, return_warmup, macd_warmup + 1) + lookback


@dataclass
class STMModelConfig:
    """Architecture (reference MODEL_MAPPING: lstm, slp, mlp, conv, tft)."""

    model_type: str = "tft"
    lookback: int = 84                     # input window ("training_window" in project config)
    encoder_length: Optional[int] = 63     # TFT only: lookback - encoder_length = decoder steps
    params: Dict[str, Any] = field(default_factory=dict)  # constructor kwargs (e.g. hidden_dim)

    def target_timesteps(self) -> int:
        if self.model_type == "tft":
            return self.lookback - int(self.encoder_length)
        return self.lookback


@dataclass
class STMTrainingConfig:
    """Expanding-window training (reference train_multivariate.ipynb cell 17)."""

    first_split_start: str = "2019-01-01"  # train <= start, val (start, start+val], test after
    last_split_start: str = "2024-01-01"
    split_frequency_days: int = 365
    val_days: int = 365
    test_days: int = 365
    batch_size: int = 64
    lr: float = 1e-3
    weight_decay: float = 1e-5
    lr_decay_steps: int = 10
    lr_decay_gamma: float = 0.75
    min_lr: float = 1e-5                   # scheduler only steps while lr > min_lr
    n_epochs: int = 100
    early_stopping_rounds: int = 10
    seed: int = 42
    scaling: Optional[str] = None          # None | 'standard' | 'minmax' (fit on train only)
    apply_l1_reg: bool = False
    l1_alpha: float = 1e-4
    apply_turnover_reg: bool = False
    turnover_alpha: float = 1e-4
    target_vol: float = 0.15               # turnover evaluation
    basis_points: Tuple[int, ...] = (0, 1, 5, 10)
    purge_days: int = 1                    # drop last h train/val rows whose label leaks into next fold
    rolling_window_rows: Optional[int] = None  # train on the last N sessions only (None = expanding)
    device: str = "cpu"


@dataclass
class STMUniverseConfig:
    """Universe selection (reference: N_ASSETS_PER_SECTOR random stocks per sector, SEED)."""

    name: str = "stm_reference_sector_sample"
    entity_type: str = "CompanyShare"
    n_per_sector: int = 5
    seed: int = 42
    tickers: Optional[List[str]] = None    # explicit override of the sampled universe


@dataclass
class STMConfiguration:
    universe: STMUniverseConfig = field(default_factory=STMUniverseConfig)
    features: STMFeatureConfig = field(default_factory=STMFeatureConfig)
    model: STMModelConfig = field(default_factory=STMModelConfig)
    training: STMTrainingConfig = field(default_factory=STMTrainingConfig)
    prediction_horizon: int = 1            # rows: next session (daily) or next bar (intraday)
    # None = one row per session (the original daily projects); e.g. 10 = one row per 10-minute bar: every
    # window above (return horizons, vol / MACD spans, lookback, rolling rows) is then counted in bars, and
    # features.annualisation must be periods per year (stm_time.periods_per_year)
    bar_minutes: Optional[int] = None
    artifact_selection: str = "covering_test_window"  # or 'latest_before'
    artifact_dir: Optional[str] = None
    ml_model_name_prefix: str = "stm_"
    signal_factor_name: str = "spatio_temporal_momentum_signal"
    feature_factor_prefix: str = "stm_"
    persist_features: bool = True

    # ------------------------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "STMConfiguration":
        data = dict(data or {})

        def _tuple(v):
            return tuple(tuple(x) if isinstance(x, list) else x for x in v) if v is not None else v

        feat = dict(data.get("features", {}))
        for k in ("return_horizons", "macd_combinations"):
            if k in feat:
                feat[k] = _tuple(feat[k])
        train = dict(data.get("training", {}))
        if "basis_points" in train:
            train["basis_points"] = tuple(train["basis_points"])
        return cls(
            universe=STMUniverseConfig(**data.get("universe", {})),
            features=STMFeatureConfig(**feat),
            model=STMModelConfig(**data.get("model", {})),
            training=STMTrainingConfig(**train),
            **{k: v for k, v in data.items() if k not in ("universe", "features", "model", "training")},
        )

    def model_hash(self) -> str:
        """Hash of everything that changes the model's inputs/outputs (not training dates)."""
        payload = {
            "features": asdict(self.features),
            "model": asdict(self.model),
            "prediction_horizon": self.prediction_horizon,
            "scaling": self.training.scaling,
        }
        if self.bar_minutes:                      # absent for daily models: their existing hashes are unchanged
            payload["bar_minutes"] = self.bar_minutes
        return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()

    def hash(self) -> str:
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True, default=str).encode()).hexdigest()
