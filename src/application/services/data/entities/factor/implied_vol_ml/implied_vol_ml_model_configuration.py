import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, Any


@dataclass
class ImpliedVolMlModelConfiguration:
    """Hyperparameters + retraining schedule for the implied-vol ML model."""

    # Single source of truth for the ML training universe name — shared by
    # ImpliedVolMlModelProvider and ImpliedVolMlModelTrainer.
    UNIVERSE_NAME: str = "CompanyShareOptionImpliedVol"
    UNIVERSE_ENTITY_TYPE: str = "CompanyShareOption"
    ML_MODEL_NAME_PREFIX: str = "iv_ml_"

    model_type: str = "random_forest"
    n_estimators: int = 100
    max_depth: int = 5
    min_samples_split: int = 10
    random_state: int = 42
    retraining_period_days: int = 30
    min_training_samples: int = 2
    training_window_bars: int = 10

    @property
    def retraining_period(self) -> timedelta:
        return timedelta(days=self.retraining_period_days)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_type": self.model_type,
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "min_samples_split": self.min_samples_split,
            "random_state": self.random_state,
            "retraining_period_days": self.retraining_period_days,
            "min_training_samples": self.min_training_samples,
        }

    def hash(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True).encode()
        ).hexdigest()
