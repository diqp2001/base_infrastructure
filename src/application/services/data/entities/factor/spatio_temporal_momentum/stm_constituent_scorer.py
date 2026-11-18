"""
Spatio-temporal momentum scores of an index's constituents at a decision date, with the EXISTING STM pipeline
(no second model): STMConfiguration -> align_close_panel -> build_feature_panel -> STMWalkForwardTrainer.train_as_of
-> SpatioTemporalMomentumModelProvider.score_details_with_artifact. Same eligibility rules as STMTradingCycle:
an asset is scored when it has a close on the decision date and at least the rolling window (else the feature
warm-up) of closes; the training panel is the eligible assets' closes up to the decision date, inner-joined on dates,
cut to the rolling window.

Everything stays in memory (factory=None: no artifact, feature or signal row in the database). The model is retrained
when ``retrain_every`` decisions have passed or when the eligible set changes (an index change), never with data after
the decision date.

The score is the STM network's position in [-1, 1] (Sharpe-ratio loss, horizon = config.prediction_horizon rows):
> 0 = the model would be long the share over the horizon. It is not a probability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_artifact_store import LoadedArtifact
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMConfiguration,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_dataset import (
    align_close_panel,
    build_feature_panel,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_model_provider import (
    SpatioTemporalMomentumModelProvider,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_walk_forward import (
    STMWalkForwardTrainer,
)


class InMemoryClosePanelReader:
    """The STM price reader interface over a close panel (dates x symbols)."""

    def __init__(self, closes: pd.DataFrame):
        self.closes = closes

    def load_close_panel(self, assets: Dict[int, str], start=None, end=None) -> pd.DataFrame:
        cols = [a for a in assets.values() if a in self.closes.columns]
        out = self.closes[cols]
        if start is not None:
            out = out[out.index >= pd.Timestamp(start)]
        if end is not None:
            out = out[out.index <= pd.Timestamp(end)]
        return out


@dataclass
class ConstituentScores:
    as_of: pd.Timestamp
    scores: Dict[str, float]                        # scored constituents -> STM position in [-1, 1]
    unscored: Dict[str, str]                        # constituent -> why it has no score
    model_assets: List[str] = field(default_factory=list)
    trained_at: Optional[pd.Timestamp] = None       # decision date of the model used
    retrained: bool = False

    def ranks(self) -> Dict[str, int]:
        """1 = highest score."""
        ordered = sorted(self.scores, key=lambda s: (-self.scores[s], s))
        return {s: i + 1 for i, s in enumerate(ordered)}


class STMConstituentScorer:

    def __init__(self, config: STMConfiguration, retrain_every: int = 1,
                 log: Optional[Callable[[str], None]] = None,
                 extra_features: Optional[Callable[[pd.DatetimeIndex, List[str]], Dict[str, pd.DataFrame]]] = None,
                 extra_feature_groups: Optional[Mapping[str, str]] = None):
        """``extra_features(dates, assets)``: point-in-time feature panels added to the price features (e.g.
        fundamentals known at each date) - in training AND in scoring. ``extra_feature_groups`` ({asset: group},
        e.g. the sector): those features are scaled group-neutrally (stm_dataset.cross_sectional_zscore)."""
        self.config = config
        self.extra_features = extra_features
        self.extra_feature_groups = dict(extra_feature_groups) if extra_feature_groups else None
        self.retrain_every = max(1, int(retrain_every))
        self.log = log or (lambda m: None)
        self._loaded: Optional[LoadedArtifact] = None
        self._trained_at: Optional[pd.Timestamp] = None
        self._decisions_since = 0

    def required_rows(self) -> int:
        rows = self.config.training.rolling_window_rows
        return int(rows) if rows else self.config.features.required_history_days(self.config.model.lookback)

    def eligible(self, closes: pd.DataFrame, members: Sequence[str], as_of: pd.Timestamp) -> Dict[str, Optional[str]]:
        """{member: None if eligible else the reason}."""
        required = self.required_rows()
        out: Dict[str, Optional[str]] = {}
        for s in members:
            col = closes.get(s)
            if col is None:
                out[s] = "no price history"
            elif pd.isna(col.get(as_of, np.nan)):
                out[s] = "no close on the decision date"
            elif int(col.loc[:as_of].notna().sum()) < required:
                out[s] = f"fewer than {required} closes"
            else:
                out[s] = None
        return out

    def _extra(self, aligned: pd.DataFrame) -> Optional[Dict[str, pd.DataFrame]]:
        """The extra (e.g. fundamental) feature panels on the aligned rows and assets; None without a source."""
        if self.extra_features is None:
            return None
        return self.extra_features(pd.DatetimeIndex(aligned.index), list(aligned.columns)) or None

    def _train(self, closes: pd.DataFrame, eligible: List[str], as_of: pd.Timestamp) -> Optional[LoadedArtifact]:
        aligned, _ = align_close_panel(closes[eligible].loc[:as_of])
        rows = self.config.training.rolling_window_rows
        if rows:
            aligned = aligned.iloc[-int(rows):]
        if aligned.shape[1] < 2 or len(aligned) == 0:
            return None
        panel = build_feature_panel(aligned, self.config.features, self.config.prediction_horizon,
                                    extra_features=self._extra(aligned),
                                    extra_feature_groups=self.extra_feature_groups)
        ids = {s: i + 1 for i, s in enumerate(panel.assets)}
        result = STMWalkForwardTrainer(self.config, factory=None, log=self.log).train_as_of(
            panel, as_of, ids, valid_days=366)
        if result is None or result.model is None:
            return None
        return LoadedArtifact(model=result.model, metadata=result.metadata)

    def score(self, closes: pd.DataFrame, members: Sequence[str], as_of) -> ConstituentScores:
        """Scores of ``members`` at the close of ``as_of`` from closes dated <= as_of only."""
        as_of = pd.Timestamp(as_of)
        closes = closes.loc[:as_of]
        reasons = self.eligible(closes, members, as_of)
        eligible = [s for s in members if reasons[s] is None]
        unscored = {s: r for s, r in reasons.items() if r is not None}

        model_assets = self._loaded.assets if self._loaded is not None else None
        due = (self._loaded is None or self._decisions_since >= self.retrain_every
               or sorted(model_assets) != sorted(eligible))
        retrained = False
        if due:
            loaded = self._train(closes, eligible, as_of) if len(eligible) >= 2 else None
            if loaded is None:
                for s in eligible:
                    unscored[s] = "no model (not enough training data)"
                self._loaded = None
                return ConstituentScores(as_of, {}, unscored)
            self._loaded, self._trained_at, self._decisions_since, retrained = loaded, as_of, 0, True
        self._decisions_since += 1

        if self.extra_features is None:
            provider = SpatioTemporalMomentumModelProvider(config=self.config,
                                                           price_reader=InMemoryClosePanelReader(closes))
            rows = provider.score_details_with_artifact(self._loaded, as_of)
            scores = {r["ticker"]: r["score"] for r in rows}
        else:
            scores = self._score_with_extra(closes, as_of)
        for s in eligible:
            if s not in scores:
                unscored[s] = ("not in the model (no common history)" if s not in self._loaded.assets
                               else "the model gave no score")
        return ConstituentScores(as_of, scores, unscored, model_assets=list(self._loaded.assets),
                                 trained_at=self._trained_at, retrained=retrained)

    def _score_with_extra(self, closes: pd.DataFrame, as_of: pd.Timestamp) -> Dict[str, float]:
        """Inference with the extra features: the panel rebuilt exactly as in training (the artifact's assets, from
        its history start), the window ending at ``as_of``."""
        import torch
        from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_dataset import (
            build_inference_input,
        )
        loaded = self._loaded
        start = loaded.metadata.get("history_start")
        frame = closes[closes.index >= pd.Timestamp(start)] if start else closes
        aligned, _ = align_close_panel(frame.reindex(columns=loaded.assets))
        if list(aligned.columns) != loaded.assets or not len(aligned) or aligned.index[-1] != as_of:
            return {}
        panel = build_feature_panel(aligned, self.config.features, self.config.prediction_horizon,
                                    assets=loaded.assets, extra_features=self._extra(aligned),
                                    extra_feature_groups=self.extra_feature_groups)
        try:
            X, _ = build_inference_input(panel, as_of, self.config.model.lookback, loaded.metadata.get("scaler"))
        except ValueError:
            return {}
        with torch.no_grad():
            signal = loaded.model(torch.tensor(X, dtype=torch.float32))[0].numpy()
        return {a: float(signal[k]) for k, a in enumerate(loaded.assets) if np.isfinite(signal[k])}
