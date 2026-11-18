"""
Which constituents' calls the model-filtered dispersion buys. It only chooses the LONG basket: the number of short
ETF calls is fixed before (DispersionPortfolioConstructionService), from the full basket.

The model's native output is the STM score (position in [-1, 1], higher = more likely to rise over the horizon) and
its rank (1 = highest). Every criterion set is applied (AND):
    minimum_model_score   keep score >= x               (0.0 = only names the model would hold long)
    top_n                 keep the n best ranks
    bottom_n_excluded     drop the n worst ranks
    percentile_threshold  keep score >= that percentile of the day's scores (0..100)
    minimum_probability_up  refused: the STM model gives no probability
Constituents without a score: ``unscored`` = 'keep' (the model has no view: bought as in the full basket) or
'reject'.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping, Optional, Sequence

import numpy as np


@dataclass(frozen=True)
class ModelFilterConfig:
    minimum_model_score: Optional[float] = 0.0
    top_n: Optional[int] = None
    bottom_n_excluded: Optional[int] = None
    percentile_threshold: Optional[float] = None
    minimum_probability_up: Optional[float] = None
    unscored: str = "keep"

    def __post_init__(self):
        if self.minimum_probability_up is not None:
            raise ValueError("minimum_probability_up: the spatio-temporal model outputs a position score in [-1, 1], "
                             "not a probability; use minimum_model_score / top_n / percentile_threshold")
        if self.unscored not in ("keep", "reject"):
            raise ValueError("unscored must be 'keep' or 'reject'")
        if self.percentile_threshold is not None and not 0 <= self.percentile_threshold <= 100:
            raise ValueError("percentile_threshold is a percentile (0..100)")


@dataclass
class Selection:
    selected: List[str]
    rejected: Dict[str, str] = field(default_factory=dict)      # constituent -> reason
    scores: Dict[str, float] = field(default_factory=dict)
    ranks: Dict[str, int] = field(default_factory=dict)


def select_constituents(members: Sequence[str], scores: Mapping[str, float], config: ModelFilterConfig,
                        unscored_reasons: Optional[Mapping[str, str]] = None) -> Selection:
    ordered = sorted(scores, key=lambda s: (-scores[s], s))
    ranks = {s: i + 1 for i, s in enumerate(ordered)}
    n = len(ordered)
    cut = (float(np.percentile([scores[s] for s in ordered], config.percentile_threshold))
           if config.percentile_threshold is not None and n else None)
    selected, rejected = [], {}
    for s in members:
        if s not in scores:
            if config.unscored == "keep":
                selected.append(s)
            else:
                rejected[s] = f"no score ({(unscored_reasons or {}).get(s, 'not scored')})"
            continue
        v, r = scores[s], ranks[s]
        reasons = []
        if config.minimum_model_score is not None and v < config.minimum_model_score:
            reasons.append(f"score {v:.3f} < {config.minimum_model_score}")
        if config.top_n is not None and r > config.top_n:
            reasons.append(f"rank {r} outside the top {config.top_n}")
        if config.bottom_n_excluded is not None and r > n - config.bottom_n_excluded:
            reasons.append(f"rank {r} in the bottom {config.bottom_n_excluded}")
        if cut is not None and v < cut:
            reasons.append(f"score {v:.3f} below the {config.percentile_threshold:g}th percentile ({cut:.3f})")
        if reasons:
            rejected[s] = "; ".join(reasons)
        else:
            selected.append(s)
    return Selection(selected, rejected, dict(scores), ranks)
