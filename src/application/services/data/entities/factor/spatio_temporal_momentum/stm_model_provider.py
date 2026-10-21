"""
SpatioTemporalMomentumModelProvider — inference provider injected into
CompanyShareSpatioTemporalMomentumFactor by its repository (same pattern as
LGBMMomentumModelProvider).

For a decision date D (a completed session):
  1. select the artifact eligible for D (validation ended before D)
  2. load closes for the artifact's assets, dates <= D only
  3. rebuild features with the artifact's feature configuration
  4. build X = [1, assets, lookback, features] with the artifact's scaler
  5. run the model once and cache {entity_id: score} for every constituent

The provider never trains implicitly: if no artifact covers D it returns
None, so a missing model can never silently fall back to a look-ahead fit.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import torch

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_time import (
    bar_key, bars_per_session,
)

from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_artifact_store import (
    LoadedArtifact,
    STMArtifactStore,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_configuration import (
    STMConfiguration,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_dataset import (
    align_close_panel,
    build_feature_panel,
    build_inference_input,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_feature_store import (
    STMFeatureStore,
)
from src.application.services.data.entities.factor.spatio_temporal_momentum.stm_price_history import (
    STMPriceHistoryReader,
)


class SpatioTemporalMomentumModelProvider:
    # (model_hash, session date) -> {entity_id: score}
    _score_cache: Dict[Tuple[str, pd.Timestamp], Dict[int, float]] = {}
    _model_cache: Dict[Any, LoadedArtifact] = {}
    # Set by the project manager so providers built by the repository use
    # the project configuration (model hash, artifact selection).
    default_config: Optional[STMConfiguration] = None

    def __init__(self, factory=None, config: Optional[STMConfiguration] = None,
                 price_reader: Optional[STMPriceHistoryReader] = None,
                 artifact_store: Optional[STMArtifactStore] = None):
        self.factory = factory
        self.config = config or type(self).default_config or STMConfiguration()
        self.price_reader = price_reader or (STMPriceHistoryReader(factory) if factory else None)
        self.artifact_store = artifact_store or (STMArtifactStore(factory, self.config) if factory else None)

    # ------------------------------------------------------------------
    # Factor interface
    # ------------------------------------------------------------------

    def predict(self, dependencies: dict, entity, target_date) -> Optional[float]:
        entity_id = getattr(entity, "id", None)
        if entity_id is None:
            return None
        scores = self.score_universe(target_date)
        return scores.get(int(entity_id)) if scores else None

    # ------------------------------------------------------------------
    # Universe scoring
    # ------------------------------------------------------------------

    def _load(self, artifact) -> LoadedArtifact:
        key = getattr(artifact, "id", None) or artifact.location
        if key not in self._model_cache:
            self._model_cache[key] = self.artifact_store.load(artifact)
        return self._model_cache[key]

    def score_universe(self, as_of, persist: bool = False) -> Dict[int, float]:
        d = bar_key(as_of, self.config.bar_minutes)
        cache_key = (self.config.model_hash(), d)
        if cache_key in self._score_cache:
            return self._score_cache[cache_key]
        if self.artifact_store is None or self.price_reader is None:
            return {}

        selected = self.artifact_store.select(d)
        if selected is None:
            return {}
        loaded = self._load(selected[0])
        scores = self.score_with_artifact(loaded, d)
        self._score_cache[cache_key] = scores
        if persist and scores and self.factory is not None:
            STMFeatureStore(self.factory, self.config).write_signals(d, scores)
        return scores

    def score_with_artifact(self, loaded: LoadedArtifact, as_of) -> Dict[int, float]:
        """Run one artifact for session ``as_of`` using only closes dated <= as_of."""
        return {row["entity_id"]: row["score"] for row in self.score_details_with_artifact(loaded, as_of)}

    def score_details(self, as_of) -> List[Dict[str, Any]]:
        """Per constituent: ticker, entity_id, score and daily vol at ``as_of`` (for portfolio construction)."""
        if self.artifact_store is None or self.price_reader is None:
            return []
        selected = self.artifact_store.select(bar_key(as_of, self.config.bar_minutes))
        if selected is None:
            return []
        return self.score_details_with_artifact(self._load(selected[0]), as_of)

    def score_details_with_artifact(self, loaded: LoadedArtifact, as_of) -> List[Dict[str, Any]]:
        cfg = loaded.config
        d = bar_key(as_of, cfg.bar_minutes)
        id_to_asset = {eid: a for a, eid in loaded.asset_entity_ids.items()}
        if loaded.metadata.get("history_start"):
            start = pd.Timestamp(loaded.metadata["history_start"])
        else:
            history_days = cfg.features.required_history_days(cfg.model.lookback)
            sessions = -(-history_days // bars_per_session(cfg.bar_minutes))        # rows -> sessions
            start = d.normalize() - pd.Timedelta(days=int(sessions * 7 / 5) + 30)  # weekend/holiday padding
        closes = self.price_reader.load_close_panel(id_to_asset, start=start, end=d)
        closes = closes[closes.index <= d]
        closes, _report = align_close_panel(closes.reindex(columns=loaded.assets))
        if list(closes.columns) != loaded.assets:
            return []
        try:
            panel = build_feature_panel(closes, cfg.features, cfg.prediction_horizon, assets=loaded.assets)
            X, row_date = build_inference_input(panel, d, cfg.model.lookback, loaded.scaler)
        except ValueError:
            return []
        if bar_key(row_date, cfg.bar_minutes) != d:
            # an asset of this model has no close for the session (inner join dropped it):
            # never score from a stale row — the trading cycle retrains without that asset
            return []
        with torch.no_grad():
            signal = loaded.model(torch.tensor(X, dtype=torch.float32))[0].numpy()
        i = panel.index_at_or_before(d)
        rows = []
        for k, a in enumerate(loaded.assets):
            if a not in loaded.asset_entity_ids or not np.isfinite(signal[k]):
                continue
            rows.append({"ticker": a, "entity_id": int(loaded.asset_entity_ids[a]), "score": float(signal[k]),
                         "daily_vol": float(panel.daily_vol[i, k]), "feature_date": row_date})
        return rows

    @classmethod
    def clear_cache(cls) -> None:
        cls._score_cache.clear()
        cls._model_cache.clear()
