import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, Any


@dataclass
class LGBMMomentumModelConfiguration:
    """Hyperparameters + retraining schedule for the LightGBM cross-sectional quintile rank model."""

    UNIVERSE_NAME: str = "CompanyShareMomentum"
    UNIVERSE_ENTITY_TYPE: str = "CompanyShare"
    ML_MODEL_NAME_PREFIX: str = "lgbm_mom_"

    # LightGBM params
    n_estimators: int = 200
    max_depth: int = 6
    learning_rate: float = 0.05
    num_leaves: int = 31
    min_data_in_leaf: int = 20
    random_state: int = 42

    # Training schedule
    retraining_period_days: int = 30
    min_training_samples: int = 50
    training_window_bars: int = 252  # ~1 year of daily bars for training

    # Model semantics
    n_quintiles: int = 5          # output classes 1-5
    forward_return_days: int = 5  # 1 trading week ahead

    @property
    def retraining_period(self) -> timedelta:
        return timedelta(days=self.retraining_period_days)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "n_estimators": self.n_estimators,
            "max_depth": self.max_depth,
            "learning_rate": self.learning_rate,
            "num_leaves": self.num_leaves,
            "min_data_in_leaf": self.min_data_in_leaf,
            "random_state": self.random_state,
            "retraining_period_days": self.retraining_period_days,
            "n_quintiles": self.n_quintiles,
            "forward_return_days": self.forward_return_days,
        }

    def hash(self) -> str:
        return hashlib.sha256(
            json.dumps(self.to_dict(), sort_keys=True).encode()
        ).hexdigest()
